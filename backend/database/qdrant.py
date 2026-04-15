"""
Qdrant vector-database client and collection initialisation.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from backend.config import settings


client = QdrantClient(
    host=settings.QDRANT_HOST,
    port=settings.QDRANT_PORT,
)


def init_qdrant():
    """Ensure the conversations collection exists."""
    existing = [c.name for c in client.get_collections().collections]
    if settings.QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )
