"""
Chat API routes.

Endpoints:
  POST /api/chat/audio              – Send audio for transcription + agent processing
  POST /api/chat/text               – Send text directly to the agent
  GET  /api/chat/sessions           – List all sessions
  GET  /api/chat/sessions/{id}/history – Get message history for a session
"""

import os
import uuid

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database.postgres import get_db
from backend.services.agent import agent_service
from backend.services.memory import memory_service
from backend.services.stt import stt_service

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/audio")
async def chat_audio(
    audio: UploadFile = File(...),
    session_id: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Accept audio, transcribe it, and process via the agent."""

    # ── Save uploaded audio ──────────────────────────────────────
    settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    file_ext = os.path.splitext(audio.filename or "audio.wav")[1] or ".wav"
    audio_filename = f"{uuid.uuid4()}{file_ext}"
    audio_path = str(settings.UPLOADS_DIR / audio_filename)

    async with aiofiles.open(audio_path, "wb") as f:
        content = await audio.read()
        await f.write(content)

    # ── Transcribe ───────────────────────────────────────────────
    try:
        transcription = await stt_service.transcribe(audio_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {e}",
        )

    if not transcription:
        raise HTTPException(
            status_code=400,
            detail="Could not transcribe audio. Please try again.",
        )

    # ── Resolve session ──────────────────────────────────────────
    session = None
    if session_id:
        sid = uuid.UUID(session_id)
        session = await memory_service.get_session(db, sid)

    if session is None:
        session = await memory_service.create_session(
            db, title=transcription[:50],
        )

    # ── Run agent ────────────────────────────────────────────────
    result = await agent_service.process_message(
        db, session.id, transcription, audio_path=audio_path,
    )
    result["session_id"] = str(session.id)
    return result


@router.post("/text")
async def chat_text(
    message: str = Form(...),
    session_id: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Accept text and process via the agent (no transcription needed)."""

    session = None
    if session_id:
        sid = uuid.UUID(session_id)
        session = await memory_service.get_session(db, sid)

    if session is None:
        session = await memory_service.create_session(
            db, title=message[:50],
        )

    result = await agent_service.process_message(db, session.id, message)
    result["session_id"] = str(session.id)
    return result


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """Return all sessions ordered by most recent."""
    sessions = await memory_service.get_all_sessions(db)
    return [
        {
            "id": str(s.id),
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}/history")
async def get_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return the full message history for a session."""
    sid = uuid.UUID(session_id)
    history = await memory_service.get_chat_history(db, sid, limit=50)
    return history
