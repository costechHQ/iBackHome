"""Message templates. Owner: Lilian.

Each feature keeps its own templates in its `messages.py` and passes one to notify():

    from app.base.notifications import Template

    MILESTONE_CLAIMED = Template(
        name="milestone.claimed",
        title="Milestone claimed",
        text="{contractor} says '{milestone}' is done. Your supervisor will check it next.",
    )

`text` is the body for every channel (SMS, push, WhatsApp, email). `{name}` placeholders are filled
from the `data` passed to notify(); a missing one is a programming error and raises at once.
"""

import string
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

_FORMATTER = string.Formatter()


@dataclass(frozen=True)
class Rendered:
    """A message ready to send."""

    template: str
    text: str
    title: str
    subject: str


@dataclass(frozen=True)
class Template:
    name: str  # stored on the notification row, e.g. "milestone.claimed"
    text: str
    title: str = "iBackHome"  # push title
    subject: str | None = None  # email subject; defaults to the title

    def __post_init__(self) -> None:
        for _, field, _, _ in _FORMATTER.parse(self.text):
            if field is not None and not field.isidentifier():
                raise ValueError(f"template {self.name}: use plain {{names}} only, not {{{field}}}")

    def placeholders(self) -> set[str]:
        return {field for _, field, _, _ in _FORMATTER.parse(self.text) if field}

    def render(self, data: Mapping[str, Any]) -> Rendered:
        missing = self.placeholders() - set(data)
        if missing:
            raise ValueError(f"template {self.name} needs {sorted(missing)}")
        text = self.text.format_map({k: data[k] for k in self.placeholders()})
        return Rendered(template=self.name, text=text, title=self.title, subject=self.subject or self.title)


# Login codes (Christopher's OTP sender calls notify_address() with this).
LOGIN_CODE = Template(
    name="auth.login_code",
    title="Your iBackHome code",
    text="Your iBackHome code is {code}. It expires in 5 minutes. Never share it with anyone.",
)
