"""Request and response shapes for the website assistant (ADR 0006)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AssistantChatIn(BaseModel):
    """One question. `extra="forbid"`: nothing else is accepted, and nothing typed is stored."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=2, max_length=500, examples=["How does escrow work?"])


class AssistantRelatedQuestion(BaseModel):
    question: str


class AssistantChatOut(BaseModel):
    answer: str
    # Other questions people ask on the same topic: sending one back returns that answer.
    related: list[AssistantRelatedQuestion]
    # True when the answer points to a person; the panel then shows the contact buttons.
    handoff: bool
    # `faq`: a vetted answer matched. `none`: nothing matched well enough, so this is a handoff.
    source: Literal["faq", "none"]
