"""
Application configuration loaded from environment variables.
Uses pydantic-settings for type-safe configuration management.
"""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Central configuration for the Voice Agent application."""

    # ── App ──────────────────────────────────────────────────────
    APP_NAME: str = "Voice Agent"
    DEBUG: bool = False

    # ── Paths ────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    OUTPUT_DIR: Path = BASE_DIR / "output"
    UPLOADS_DIR: Path = BASE_DIR / "uploads"

    # ── PostgreSQL ───────────────────────────────────────────────
    POSTGRES_USER: str = "voiceagent"
    POSTGRES_PASSWORD: str = "voiceagent"
    POSTGRES_DB: str = "voiceagent"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ── Qdrant ───────────────────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "conversations"

    # ── Groq ─────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_STT_MODEL: str = "whisper-large-v3"

    # ── STT Engine ───────────────────────────────────────────────
    STT_ENGINE: str = "groq"  # "groq" or "local"
    WHISPER_MODEL_SIZE: str = "base"

    # ── Embedding ────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIM: int = 384

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
