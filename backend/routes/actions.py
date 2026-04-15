"""
Action API routes – Human-in-the-Loop approval flow.

Endpoints:
  POST /api/actions/approve  – Approve a pending tool execution
  POST /api/actions/reject   – Reject a pending tool execution
"""

import uuid
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database.models import ActionStatus, Message, ToolExecution
from backend.database.postgres import get_db
from backend.services.agent import agent_service

router = APIRouter(prefix="/api/actions", tags=["Actions"])


class ActionRequest(BaseModel):
    action_id: str


def _extract_summary_payloads(rows: list[ToolExecution]) -> list[dict]:
    summaries: list[dict] = []
    for row in rows:
        if not row.result:
            continue
        try:
            parsed = json.loads(row.result)
        except json.JSONDecodeError:
            continue
        summary_text = parsed.get("summary")
        if not summary_text:
            continue
        summaries.append(
            {
                "action_id": str(row.id),
                "message_id": str(row.message_id),
                "summary": summary_text,
                "created_at": row.created_at.isoformat(),
                "completed_at": (
                    row.completed_at.isoformat() if row.completed_at else None
                ),
                "original_length": parsed.get("original_length"),
                "summary_length": parsed.get("summary_length"),
            }
        )
    return summaries


@router.post("/approve")
async def approve_action(
    req: ActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Approve and execute a pending tool action."""
    try:
        action_id = uuid.UUID(req.action_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid action ID.")

    result = await agent_service.approve_action(db, action_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/summaries/{session_id}")
async def list_summaries(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return all completed summarize_text outputs for a session."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID.")

    result = await db.execute(
        select(ToolExecution)
        .join(Message, ToolExecution.message_id == Message.id)
        .where(
            Message.session_id == sid,
            ToolExecution.tool_name == "summarize_text",
            ToolExecution.status == ActionStatus.COMPLETED,
        )
        .order_by(ToolExecution.created_at.desc())
    )
    rows = list(result.scalars().all())
    summaries = _extract_summary_payloads(rows)
    return {"session_id": session_id, "count": len(summaries), "summaries": summaries}


@router.post("/summaries/{session_id}/export")
async def export_summaries_markdown(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Export session summaries to a markdown file and return it."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID.")

    result = await db.execute(
        select(ToolExecution)
        .join(Message, ToolExecution.message_id == Message.id)
        .where(
            Message.session_id == sid,
            ToolExecution.tool_name == "summarize_text",
            ToolExecution.status == ActionStatus.COMPLETED,
        )
        .order_by(ToolExecution.created_at.asc())
    )
    rows = list(result.scalars().all())
    summaries = _extract_summary_payloads(rows)
    if not summaries:
        raise HTTPException(status_code=404, detail="No summaries found for session.")

    export_dir = Path(settings.OUTPUT_DIR) / "summaries"
    export_dir.mkdir(parents=True, exist_ok=True)
    export_path = export_dir / f"{session_id}.md"

    md_lines = [f"# Session Summaries ({session_id})", ""]
    for idx, s in enumerate(summaries, start=1):
        md_lines.extend(
            [
                f"## Summary {idx}",
                f"- Action ID: `{s['action_id']}`",
                f"- Message ID: `{s['message_id']}`",
                f"- Created: `{s['created_at']}`",
                (
                    f"- Completed: `{s['completed_at']}`"
                    if s["completed_at"]
                    else "- Completed: `N/A`"
                ),
                (
                    f"- Length: `{s['summary_length']}` / `{s['original_length']}`"
                    if s["summary_length"] is not None and s["original_length"] is not None
                    else "- Length: `N/A`"
                ),
                "",
                s["summary"],
                "",
                "---",
                "",
            ]
        )

    export_path.write_text("\n".join(md_lines).strip() + "\n", encoding="utf-8")
    return FileResponse(
        path=str(export_path),
        media_type="text/markdown",
        filename=export_path.name,
    )


@router.post("/reject")
async def reject_action(
    req: ActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending tool action."""
    try:
        action_id = uuid.UUID(req.action_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid action ID.")

    result = await agent_service.reject_action(db, action_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result
