"""Response shapes (Pydantic) for the in-app notification feed. Owner: Lilian.

Other features call notify() / notify_address(); the only HTTP endpoints are the signed-in user's own
feed (`GET /me/notifications`, `POST /me/notifications/{id}/read`).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class FeedItem(BaseModel):
    """One message the user was sent. `title` and `text` are the words the user saw, never the raw payload."""

    id: uuid.UUID
    template: str  # e.g. "milestone.claimed"; lets an app pick an icon or a screen to open
    title: str
    text: str
    created_at: datetime
    read_at: datetime | None


class FeedPage(BaseModel):
    items: list[FeedItem]
    next_cursor: str | None
    unread_count: int  # all unread messages, not just this page: for a badge


class PreferencesIn(BaseModel):
    """Both settings, always (a PUT replaces them). Spot-check SMS is not a setting: it stays on."""

    push_enabled: bool = Field(strict=True)
    hide_previews: bool = Field(strict=True)


class PreferencesOut(BaseModel):
    push_enabled: bool
    hide_previews: bool
