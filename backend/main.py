"""
FastAPI application entry-point.

Initialises databases on startup, registers all route modules,
and configures CORS for the Next.js frontend.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database.postgres import init_db
from backend.database.qdrant import init_qdrant
from backend.routes import actions, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup / shutdown logic."""
    # ── Startup ──────────────────────────────────────────────────
    settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    await init_db()
    init_qdrant()

    print(f"[startup] {settings.APP_NAME} is ready")
    yield
    # ── Shutdown ─────────────────────────────────────────────────
    print(f"[shutdown] {settings.APP_NAME} shutting down")


app = FastAPI(
    title="Voice Agent API",
    description=(
        "Voice-Controlled Local AI Agent powered by Groq LLM "
        "with PostgreSQL + Qdrant memory layer."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (allow Next.js frontend) ───────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(actions.router)


@app.get("/api/health")
async def health():
    """Simple health-check endpoint."""
    return {"status": "healthy", "service": settings.APP_NAME}
