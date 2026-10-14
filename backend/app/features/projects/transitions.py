"""The project state machine, as a plain table (spec: "State machines", Projects).

A project may only move along a pair listed here, and only by one of the listed roles.
Everything else is refused with 409. Day 3 only creates `draft`; the moves are made from Day 4
(BoQ submit and approval) and by escrow (last milestone released).

"system" is not a person: it is the backend acting on a confirmed event.
"""

from enum import StrEnum

from app.features.projects.models import ProjectStatus as S


class ActorRole(StrEnum):
    CLIENT = "client"
    CONTRACTOR = "contractor"
    OPS = "ops"
    SYSTEM = "system"


R = ActorRole

ALLOWED_TRANSITIONS: dict[tuple[S, S], frozenset[ActorRole]] = {
    # Contractor submits the BoQ
    (S.DRAFT, S.BOQ_REVIEW): frozenset({R.CONTRACTOR}),
    # BoQ sent back for changes by any of the three approvers
    (S.BOQ_REVIEW, S.DRAFT): frozenset({R.CLIENT, R.CONTRACTOR, R.OPS}),
    # Client, contractor and ops have all approved the BoQ
    (S.BOQ_REVIEW, S.ACTIVE): frozenset({R.SYSTEM}),
    # Ops pauses and resumes work
    (S.ACTIVE, S.PAUSED): frozenset({R.OPS}),
    (S.PAUSED, S.ACTIVE): frozenset({R.OPS}),
    # The last milestone has been released
    (S.ACTIVE, S.COMPLETED): frozenset({R.SYSTEM}),
}


def is_allowed(current: S, target: S, role: ActorRole) -> bool:
    return role in ALLOWED_TRANSITIONS.get((current, target), frozenset())
