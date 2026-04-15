"""
SQLAlchemy ORM models for PostgreSQL.

Tables:
  - sessions:        Chat sessions / conversations
  - messages:        Individual messages within a session
  - tool_executions: Records of tool invocations and their outcomes
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


# ── Base ─────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


# ── Enums ────────────────────────────────────────────────────────

class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ActionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Models ───────────────────────────────────────────────────────

class Session(Base):
    """A chat session / conversation."""
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), default="New Session")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    messages = relationship(
        "Message", back_populates="session", cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    """A single message within a session."""
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(SAEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    audio_path = Column(String(512), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    session = relationship("Session", back_populates="messages")
    tool_executions = relationship(
        "ToolExecution", back_populates="message", cascade="all, delete-orphan",
    )


class ToolExecution(Base):
    """Record of a tool invocation triggered by the agent."""
    __tablename__ = "tool_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    tool_name = Column(String(100), nullable=False)
    tool_args = Column(JSON, nullable=False)
    status = Column(
        SAEnum(ActionStatus), default=ActionStatus.PENDING, nullable=False,
    )
    result = Column(Text, nullable=True)
    requires_approval = Column(Boolean, default=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    message = relationship("Message", back_populates="tool_executions")
