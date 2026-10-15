"""The agent run log. Owner: James.

Every run is saved, success or failure (spec: AI agents), with the prompt and model version so
a report can be reproduced, and every tool call the model made.
"""

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase


class RunStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AgentRun(TimestampedBase):
    __tablename__ = "agent_runs"
    __table_args__ = (CheckConstraint("status IN ('succeeded', 'failed')", name="status_valid"),)

    agent: Mapped[str] = mapped_column(String(60), index=True, nullable=False)  # e.g. "report"
    # Who triggered it; None for scheduled runs (Celery Beat).
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # system prompt, prompt, tools
    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    output: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(80), nullable=False)  # the exact model version that answered
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
