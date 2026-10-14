"""audit: Append-only audit log: audit.record(...) and GET /ops/audit.

Owner: Lilian (only Lilian edits this folder).
Spec: FR-23. Use it from any feature:

    from app.base import audit
    await audit.record(session, actor_id, "milestone.claimed", "milestone", milestone.id, ...)
"""

from app.base.audit.service import record, snapshot

__all__ = ["record", "snapshot"]
