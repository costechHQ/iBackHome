"""Request and response shapes (Pydantic) for payments. Owner: Gabriel."""

from pydantic import BaseModel


class WebhookAck(BaseModel):
    received: bool
    duplicate: bool  # true when this event was already stored; nothing was done again
