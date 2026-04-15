"""
Speech-to-Text service.

Supports two engines:
  • "groq"  – Uses the Groq Whisper API (default, recommended).
  • "local" – Uses faster-whisper running on the CPU.
"""

import os
from backend.config import settings


class STTService:
    """Transcribes audio files to text."""

    def __init__(self):
        self.engine = settings.STT_ENGINE
        self._local_model = None
        self._groq_client = None

    # ── Lazy loaders ─────────────────────────────────────────────

    def _get_local_model(self):
        if self._local_model is None:
            from faster_whisper import WhisperModel

            self._local_model = WhisperModel(
                settings.WHISPER_MODEL_SIZE,
                device="cpu",
                compute_type="int8",
            )
        return self._local_model

    def _get_groq_client(self):
        if self._groq_client is None:
            from groq import Groq

            self._groq_client = Groq(api_key=settings.GROQ_API_KEY)
        return self._groq_client

    # ── Public API ───────────────────────────────────────────────

    async def transcribe(self, audio_path: str) -> str:
        """Transcribe an audio file and return the text."""
        if self.engine == "groq":
            return await self._transcribe_groq(audio_path)
        return await self._transcribe_local(audio_path)

    # ── Private backends ─────────────────────────────────────────

    async def _transcribe_groq(self, audio_path: str) -> str:
        client = self._get_groq_client()
        with open(audio_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_path), f),
                model=settings.GROQ_STT_MODEL,
                response_format="text",
            )
        return transcription.strip()

    async def _transcribe_local(self, audio_path: str) -> str:
        model = self._get_local_model()
        segments, _ = model.transcribe(audio_path, beam_size=5)
        return " ".join(seg.text for seg in segments).strip()


stt_service = STTService()
