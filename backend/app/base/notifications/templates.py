"""Message templates.

Each feature keeps its own templates in its `messages.py` and passes one to notify():

    from app.base.notifications import Template

    MILESTONE_CLAIMED = Template(
        name="milestone.claimed",
        title="Milestone claimed",
        text="{contractor} says '{milestone}' is done. Your supervisor will check it next.",
        whatsapp_template="milestone_claimed",   # the name approved by Meta (optional)
    )

`text` is the body for every channel (SMS, push, WhatsApp, email). `{name}` placeholders are filled
from the `data` passed to notify(); a missing one is a programming error and raises at once.

WhatsApp only lets a business start a conversation with a template Meta has approved. Submit one
per `whatsapp_template` with the same wording, its {{1}}, {{2}}... in the order the placeholders
first appear in `text`. A template without `whatsapp_template` goes as plain text, which WhatsApp
delivers only inside the 24 hours after the person last wrote to us (otherwise notify() falls back
to the next channel).

Every template registers itself by name, so notifications.retry_failed can rebuild a saved message.
"""

import string
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

_FORMATTER = string.Formatter()
_REGISTRY: dict[str, "Template"] = {}


@dataclass(frozen=True)
class Rendered:
    """A message ready to send."""

    template: str
    text: str
    title: str
    subject: str
    params: tuple[str, ...] = ()  # placeholder values, in order (WhatsApp template parameters)
    whatsapp_template: str | None = None
    whatsapp_button: str | None = None  # value for a copy-code button (login codes)


@dataclass(frozen=True)
class Template:
    name: str  # stored on the notification row, e.g. "milestone.claimed"
    text: str
    title: str = "iBackHome"  # push title
    subject: str | None = None  # email subject; defaults to the title
    whatsapp_template: str | None = None  # Meta-approved template name
    whatsapp_button_param: str | None = None  # placeholder whose value fills a copy-code button

    def __post_init__(self) -> None:
        for _, field, _, _ in _FORMATTER.parse(self.text):
            if field is not None and not field.isidentifier():
                raise ValueError(f"template {self.name}: use plain {{names}} only, not {{{field}}}")
        if self.whatsapp_button_param and self.whatsapp_button_param not in self.placeholders():
            raise ValueError(f"template {self.name}: {self.whatsapp_button_param} is not a placeholder")
        _REGISTRY[self.name] = self

    def ordered_placeholders(self) -> list[str]:
        """Placeholder names in the order they first appear in the text."""
        seen: list[str] = []
        for _, field, _, _ in _FORMATTER.parse(self.text):
            if field and field not in seen:
                seen.append(field)
        return seen

    def placeholders(self) -> set[str]:
        return set(self.ordered_placeholders())

    def render(self, data: Mapping[str, Any]) -> Rendered:
        names = self.ordered_placeholders()
        missing = set(names) - set(data)
        if missing:
            raise ValueError(f"template {self.name} needs {sorted(missing)}")
        text = self.text.format_map({k: data[k] for k in names})
        return Rendered(
            template=self.name,
            text=text,
            title=self.title,
            subject=self.subject or self.title,
            params=tuple(str(data[k]) for k in names),
            whatsapp_template=self.whatsapp_template,
            whatsapp_button=str(data[self.whatsapp_button_param]) if self.whatsapp_button_param else None,
        )


def get_template(name: str) -> Template | None:
    """The template registered under `name` (its module must have been imported)."""
    return _REGISTRY.get(name)


# Login codes (Christopher's OTP sender calls notify_address() with this). On WhatsApp it needs an
# "authentication" template with a copy-code button.
LOGIN_CODE = Template(
    name="auth.login_code",
    title="Your iBackHome code",
    text="Your iBackHome code is {code}. It expires in 5 minutes. Never share it with anyone.",
    whatsapp_template="login_code",
    whatsapp_button_param="code",
)
