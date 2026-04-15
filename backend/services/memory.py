"""
Memory service – dual-store architecture.

• **PostgreSQL** stores relational data: sessions, messages, tool executions.
• **Qdrant** stores vector embeddings for semantic search over past conversations.

Together they give the agent both exact recall and fuzzy/semantic memory.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

from backend.config import settings
from backend.database.models import Message, MessageRole, Session
from backend.database.qdrant import client as qdrant_client


class MemoryService:
    """Unified memory layer over Postgres + Qdrant."""

    def __init__(self):
        self._embedder = None

    # ── Embedding helpers ────────────────────────────────────────

    def _get_embedder(self):
        if self._embedder is None:
            from fastembed import TextEmbedding

            self._embedder = TextEmbedding(model_name=settings.EMBEDDING_MODEL)
        return self._embedder

    def _embed(self, text: str) -> list[float]:
        embedder = self._get_embedder()
        embeddings = list(embedder.embed([text]))
        return embeddings[0].tolist()

    # ── PostgreSQL: Sessions ─────────────────────────────────────

    async def create_session(
        self, db: AsyncSession, title: str = "New Session"
    ) -> Session:
        session = Session(title=title)
        db.add(session)
        await db.flush()
        return session

    async def get_session(
        self, db: AsyncSession, session_id: uuid.UUID
    ) -> Session | None:
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_all_sessions(self, db: AsyncSession) -> list[Session]:
        result = await db.execute(
            select(Session).order_by(desc(Session.updated_at))
        )
        return list(result.scalars().all())

    # ── PostgreSQL: Messages ─────────────────────────────────────

    async def add_message(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        role: MessageRole,
        content: str,
        audio_path: str | None = None,
        metadata: dict | None = None,
    ) -> Message:
        msg = Message(
            session_id=session_id,
            role=role,
            content=content,
            audio_path=audio_path,
            metadata_=metadata,
        )
        db.add(msg)
        await db.flush()

        # Store embedding in Qdrant for semantic search
        try:
            embedding = self._embed(content)
            point = PointStruct(
                id=str(msg.id),
                vector=embedding,
                payload={
                    "session_id": str(session_id),
                    "message_id": str(msg.id),
                    "role": role.value,
                    "content": content,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            qdrant_client.upsert(
                collection_name=settings.QDRANT_COLLECTION,
                points=[point],
            )
        except Exception as e:
            # Non-critical: log and continue even if Qdrant is unavailable
            print(f"[memory] Warning – failed to store embedding in Qdrant: {e}")

        return msg

    async def get_chat_history(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        limit: int = 20,
    ) -> list[dict]:
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at)
            .limit(limit)
        )
        messages = result.scalars().all()
        return [{"role": m.role.value, "content": m.content} for m in messages]

    # ── Qdrant: Semantic Search ──────────────────────────────────

    def search_memory(
        self,
        query: str,
        session_id: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """Return the most semantically similar past messages."""
        try:
            embedding = self._embed(query)
        except Exception as e:
            print(f"[memory] Warning – failed to embed query for search: {e}")
            return []

        search_filter = None
        if session_id:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="session_id",
                        match=MatchValue(value=session_id),
                    )
                ]
            )

        try:
            # qdrant-client API differs across versions:
            # - older: client.search(...)
            # - newer: client.query_points(...)
            if hasattr(qdrant_client, "query_points"):
                query_result = qdrant_client.query_points(
                    collection_name=settings.QDRANT_COLLECTION,
                    query=embedding,
                    query_filter=search_filter,
                    limit=limit,
                    score_threshold=0.5,
                )
                results = getattr(query_result, "points", query_result)
            else:
                results = qdrant_client.search(
                    collection_name=settings.QDRANT_COLLECTION,
                    query_vector=embedding,
                    query_filter=search_filter,
                    limit=limit,
                    score_threshold=0.5,
                )
        except Exception as e:
            # Non-critical: memory retrieval should not break chat pipeline
            print(f"[memory] Warning – failed to search memory in Qdrant: {e}")
            return []

        return [
            {
                "content": r.payload.get("content", ""),
                "role": r.payload.get("role", ""),
                "score": r.score,
                "session_id": r.payload.get("session_id", ""),
            }
            for r in results
        ]


memory_service = MemoryService()
