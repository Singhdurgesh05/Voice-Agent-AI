"""
Agent orchestrator – the central brain of the voice agent.

Pipeline:
  1. Store user message in Postgres + Qdrant.
  2. Retrieve relevant memories via semantic search.
  3. Send message + context to Groq LLM (with tool definitions).
  4. For tools that require approval (file ops), pause and return pending actions.
  5. For safe tools (summarise), execute immediately.
  6. Store assistant response.
"""

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import (
    ActionStatus,
    MessageRole,
    ToolExecution,
)
from backend.services.llm import llm_service
from backend.services.memory import memory_service
from backend.tools.file_ops import create_file, create_folder, write_code
from backend.tools.text_ops import summarize_text


# Tools that modify the filesystem need user approval first
TOOLS_REQUIRING_APPROVAL = {"create_file", "create_folder", "write_code"}


class AgentService:
    """Orchestrates STT → Memory → LLM → Tools → Response."""

    # ── Main entry point ─────────────────────────────────────────

    async def process_message(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        user_text: str,
        audio_path: str | None = None,
    ) -> dict:
        """Process a single user turn and return the agent's response."""

        # 1 ─ Store user message
        user_msg = await memory_service.add_message(
            db, session_id, MessageRole.USER, user_text, audio_path=audio_path,
        )

        # 2 ─ Build conversational context from Postgres
        chat_history = await memory_service.get_chat_history(
            db, session_id, limit=10,
        )
        # Exclude the message we just added
        context = chat_history[:-1] if len(chat_history) > 1 else []

        # 3 ─ Retrieve semantically similar past messages from Qdrant
        memory_results = memory_service.search_memory(
            user_text, str(session_id), limit=3,
        )
        memory_context = None
        if memory_results:
            snippets = [
                f"- {r['content']}"
                for r in memory_results
                if r["content"] != user_text
            ]
            if snippets:
                memory_context = "\n".join(snippets)

        # 4 ─ Send to Groq LLM
        llm_result = await llm_service.process(
            user_text, context=context, memory_context=memory_context,
        )

        # 5 ─ Execute or queue tool calls
        pending_actions: list[dict] = []
        executed_results: list[dict] = []

        for tool_call in llm_result.get("tool_calls", []):
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            if tool_name in TOOLS_REQUIRING_APPROVAL:
                # ── Human-in-the-Loop: pause for approval ────────
                tool_exec = ToolExecution(
                    message_id=user_msg.id,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    status=ActionStatus.PENDING,
                    requires_approval=True,
                )
                db.add(tool_exec)
                await db.flush()

                pending_actions.append(
                    {
                        "id": str(tool_exec.id),
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "status": "pending",
                    }
                )
            else:
                # ── Execute immediately ──────────────────────────
                result = self._execute_tool(tool_name, tool_args)
                tool_exec = ToolExecution(
                    message_id=user_msg.id,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    status=ActionStatus.COMPLETED,
                    result=json.dumps(result),
                    requires_approval=False,
                    completed_at=datetime.now(timezone.utc),
                )
                db.add(tool_exec)
                await db.flush()

                executed_results.append(
                    {
                        "id": str(tool_exec.id),
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "result": result,
                        "status": "completed",
                    }
                )

        # 6 ─ Build the assistant response text
        response_text = llm_result.get("response_text", "")

        if not response_text and executed_results:
            lines = [
                f"✅ **{r['tool_name']}**: {r['result'].get('message', 'Done')}"
                for r in executed_results
            ]
            response_text = "\n".join(lines)

        if pending_actions:
            approval_lines = ["\n⏳ **Awaiting your approval for:**"]
            for pa in pending_actions:
                if pa["tool_name"] == "write_code":
                    approval_lines.append(
                        f"- Write code to `{pa['tool_args'].get('filename', 'unknown')}`"
                    )
                elif pa["tool_name"] == "create_file":
                    approval_lines.append(
                        f"- Create file `{pa['tool_args'].get('filename', 'unknown')}`"
                    )
                elif pa["tool_name"] == "create_folder":
                    approval_lines.append(
                        f"- Create folder `{pa['tool_args'].get('foldername', 'unknown')}`"
                    )
            response_text = (response_text + "\n" + "\n".join(approval_lines)).strip()

        # 7 ─ Persist assistant message
        assistant_msg = await memory_service.add_message(
            db,
            session_id,
            MessageRole.ASSISTANT,
            response_text,
            metadata={
                "intent": llm_result["intent"],
                "tool_calls_count": len(llm_result.get("tool_calls", [])),
            },
        )

        return {
            "message_id": str(assistant_msg.id),
            "transcription": user_text,
            "intent": llm_result["intent"],
            "response": response_text,
            "pending_actions": pending_actions,
            "executed_actions": executed_results,
            "requires_approval": len(pending_actions) > 0,
        }

    # ── Action approval / rejection ──────────────────────────────

    async def approve_action(
        self, db: AsyncSession, action_id: uuid.UUID
    ) -> dict:
        result = await db.execute(
            select(ToolExecution).where(ToolExecution.id == action_id)
        )
        tool_exec = result.scalar_one_or_none()

        if not tool_exec:
            return {"success": False, "message": "Action not found."}
        if tool_exec.status != ActionStatus.PENDING:
            return {
                "success": False,
                "message": f"Action is already {tool_exec.status.value}.",
            }

        exec_result = self._execute_tool(tool_exec.tool_name, tool_exec.tool_args)

        tool_exec.status = ActionStatus.COMPLETED
        tool_exec.result = json.dumps(exec_result)
        tool_exec.completed_at = datetime.now(timezone.utc)
        await db.flush()

        return {
            "success": True,
            "message": "Action approved and executed.",
            "result": exec_result,
        }

    async def reject_action(
        self, db: AsyncSession, action_id: uuid.UUID
    ) -> dict:
        result = await db.execute(
            select(ToolExecution).where(ToolExecution.id == action_id)
        )
        tool_exec = result.scalar_one_or_none()

        if not tool_exec:
            return {"success": False, "message": "Action not found."}

        tool_exec.status = ActionStatus.REJECTED
        tool_exec.completed_at = datetime.now(timezone.utc)
        await db.flush()

        return {"success": True, "message": "Action rejected."}

    # ── Tool dispatcher ──────────────────────────────────────────

    @staticmethod
    def _execute_tool(tool_name: str, tool_args: dict) -> dict:
        if tool_name == "create_file":
            return create_file(**tool_args)
        elif tool_name == "create_folder":
            return create_folder(**tool_args)
        elif tool_name == "write_code":
            return write_code(**tool_args)
        elif tool_name == "summarize_text":
            return summarize_text(**tool_args)
        return {"success": False, "message": f"Unknown tool: {tool_name}"}


agent_service = AgentService()
