"""notifications: notify(user_id, template, data): WhatsApp, push, SMS, email with fallback.

Owner: Lilian (only Lilian edits this folder).
Spec: FR-20, "Background jobs and notifications". Use it from any feature:

    from app.base.notifications import Template, notify, notify_address
"""

from app.base.notifications.service import notify, notify_address
from app.base.notifications.templates import LOGIN_CODE, Template

__all__ = ["LOGIN_CODE", "Template", "notify", "notify_address"]
