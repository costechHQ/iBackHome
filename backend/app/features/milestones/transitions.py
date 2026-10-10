"""The milestone state machine, as a plain table. 

A milestone may only move along a pair listed here, and only by one of the listed roles.
Everything else is refused. The table mirrors the "State machines" section of the spec.

"system" is not a person: it is the backend acting on a confirmed event
(an escrow webhook saying the money is held or released).
"""

from enum import StrEnum

from app.features.milestones.models import MilestoneStatus as S


class ActorRole(StrEnum):
    CLIENT = "client"
    CONTRACTOR = "contractor"
    SUPERVISOR = "supervisor"
    OPS = "ops"
    SYSTEM = "system"


R = ActorRole

ALLOWED_TRANSITIONS: dict[tuple[S, S], frozenset[ActorRole]] = {
    # Escrow funding for this milestone confirmed by webhook
    (S.PENDING, S.FUNDED): frozenset({R.SYSTEM}),
    # Contractor says the work is done (project must be active: checked by the caller)
    (S.FUNDED, S.CLAIMED): frozenset({R.CONTRACTOR}),
    # Assigned supervisor verifies with accepted evidence
    (S.CLAIMED, S.VERIFIED): frozenset({R.SUPERVISOR}),
    # Supervisor rejects the claim; contractor reworks and claims again
    (S.CLAIMED, S.FUNDED): frozenset({R.SUPERVISOR}),
    # Client approves the verified work
    (S.VERIFIED, S.APPROVED): frozenset({R.CLIENT}),
    # Client disputes the verified work
    (S.VERIFIED, S.DISPUTED): frozenset({R.CLIENT}),
    # Escrow provider confirms the release
    (S.APPROVED, S.RELEASED): frozenset({R.SYSTEM}),
    # Ops resolves the dispute in the contractor's favour (two ops approvals, checked by escrow)
    (S.DISPUTED, S.RELEASED): frozenset({R.OPS}),
    # Ops resolves the dispute as rework needed
    (S.DISPUTED, S.FUNDED): frozenset({R.OPS}),
}


def is_allowed(current: S, target: S, role: ActorRole) -> bool:
    return role in ALLOWED_TRANSITIONS.get((current, target), frozenset())
