"""The audit log table.

One row = one thing someone (or the system) did: who, what, to which object, the object
before and after, from which IP and device, and when.

The table is insert-only. The migration adds a database trigger that refuses every UPDATE,
DELETE and TRUNCATE, and removes those rights from the app's database user. So even a bug
or a bad actor with the app's credentials cannot rewrite history.

Unlike other tables this one has `at` instead of `created_at`/`updated_at`: rows never change,
so an `updated_at` column would be meaningless.

`actor_id` has no foreign key to `users` yet (Christopher's `users` table lands the same day).
It is empty (NULL) for actions done by the system, such as an escrow webhook.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base


class AuditEntry(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_object", "object_type", "object_id"),
        Index("ix_audit_log_at_id", "at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    object_type: Mapped[str] = mapped_column(String(60), nullable=False)
    object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(String(45))
    device_id: Mapped[str | None] = mapped_column(String(128))
    # clock_timestamp(), not now(): several entries in one transaction still get distinct times.
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("clock_timestamp()"), nullable=False
    )
