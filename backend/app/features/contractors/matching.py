"""Contractor matching: a client asks, ops shortlist, the client chooses (ADR 0007, phase 2).

Owner: Christopher.

Every state change is checked against ALLOWED below (the state machine in Docs/spec.md), audited, and an
invalid move is 409. The client only ever sees ContractorCard fields: a contractor's phone number and email
never reach a client from here, so nobody goes around us. Money is untouched: no fee, no payment.
"""

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import Request
from sqlalchemy import delete, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import audit
from app.base.payments.after_commit import after_commit
from app.base.users import service as users
from app.base.users.models import Role, User, UserStatus
from app.core import pagination
from app.core.errors import AppError
from app.features.contractors import match_notices
from app.features.contractors.models import (
    ACTIVE_MATCH_STATUSES,
    ContractorProfile,
    MatchRequest,
    MatchShortlist,
    MatchStatus,
    ProfileStatus,
)
from app.features.contractors.schemas import (
    ContractorCard,
    MatchRequestIn,
    MatchRequestOpsItem,
    MatchRequestOut,
)
from app.features.projects import service as projects
from app.features.projects.models import Project, ProjectStatus

Actor = Literal["client", "ops"]

# (from, to) -> who may make the move. Anything else is 409 invalid_transition.
ALLOWED: dict[tuple[MatchStatus, MatchStatus], frozenset[Actor]] = {
    (MatchStatus.OPEN, MatchStatus.SHORTLISTED): frozenset({"ops"}),
    (MatchStatus.SHORTLISTED, MatchStatus.OPEN): frozenset({"ops"}),
    (MatchStatus.SHORTLISTED, MatchStatus.MATCHED): frozenset({"client"}),
    (MatchStatus.OPEN, MatchStatus.CANCELLED): frozenset({"client", "ops"}),
    (MatchStatus.SHORTLISTED, MatchStatus.CANCELLED): frozenset({"client", "ops"}),
}


def _move(row: MatchRequest, to: MatchStatus, actor: Actor) -> None:
    """Change the request's status if the state machine allows this actor to, else raise."""
    current = MatchStatus(row.status)
    who = ALLOWED.get((current, to))
    if who is None:
        raise AppError(
            "invalid_transition", f"A match request can't move from '{current.value}' to '{to.value}'.", 409
        )
    if actor not in who:
        raise AppError(
            "transition_not_allowed",
            f"A {actor} can't move a match request from '{current.value}' to '{to.value}'.",
            403,
        )
    row.status = to.value


def _not_found() -> AppError:
    return AppError("match_request_not_found", "That match request doesn't exist.", 404)


async def _get(session: AsyncSession, request_id: uuid.UUID, *, lock: bool = False) -> MatchRequest:
    query = select(MatchRequest).where(MatchRequest.id == request_id)
    if lock:
        query = query.with_for_update()
    row = await session.scalar(query)
    if row is None:
        raise _not_found()
    return row


def _require_owner(row: MatchRequest, user: User) -> None:
    """The client who made the request. Anyone else is told it doesn't exist, so ids can't be probed."""
    if user.role != Role.CLIENT.value or row.client_id != user.id:
        raise _not_found()


async def _require_open_project(
    session: AsyncSession, project_id: uuid.UUID, *, lock: bool = False
) -> Project:
    """A draft project with no contractor: the only kind that can be matched."""
    project = await projects.get_project(session, project_id, lock=lock)
    if project.status != ProjectStatus.DRAFT.value:
        raise AppError(
            "project_not_draft", "A contractor can only be matched while the project is a draft.", 409
        )
    if project.contractor_id is not None:
        raise AppError("project_has_contractor", "This project already has a contractor.", 409)
    return project


# --- Reading ------------------------------------------------------------------------------------------------


async def _profiles(session: AsyncSession, row: MatchRequest) -> list[ContractorProfile]:
    """The shortlisted profiles, in the order ops chose."""
    rows = await session.scalars(
        select(ContractorProfile)
        .join(MatchShortlist, MatchShortlist.contractor_id == ContractorProfile.id)
        .where(MatchShortlist.request_id == row.id)
        .order_by(MatchShortlist.position)
    )
    return list(rows)


async def view(session: AsyncSession, row: MatchRequest) -> MatchRequestOut:
    """The request with its shortlist as client-safe cards."""
    profiles = await _profiles(session, row)
    cards = [ContractorCard.model_validate(p) for p in profiles]
    chosen = next(
        (c for p, c in zip(profiles, cards, strict=True) if p.user_id == row.chosen_contractor_id), None
    )
    return MatchRequestOut(
        id=row.id,
        project_id=row.project_id,
        status=row.status,
        state=row.state,
        city=row.city,
        work_type=row.work_type,
        timeline=row.timeline,
        notes=row.notes,
        budget_minor=row.budget_minor,
        currency=row.currency,
        created_at=row.created_at,
        decided_at=row.decided_at,
        cancel_reason=row.cancel_reason,
        shortlist=cards,
        chosen=chosen,
    )


async def get_for_project(session: AsyncSession, user: User, project_id: uuid.UUID) -> MatchRequest:
    """The project's latest request. The project's client or ops only; 404 match_request_not_found if none."""
    project = await projects.get_project(session, project_id)
    if user.role != Role.OPS.value and not (user.role == Role.CLIENT.value and project.client_id == user.id):
        raise AppError("not_project_member", "You are not on this project.", 403)
    row = await session.scalar(
        select(MatchRequest)
        .where(MatchRequest.project_id == project_id)
        .order_by(MatchRequest.created_at.desc(), MatchRequest.id.desc())
        .limit(1)
    )
    if row is None:
        raise _not_found()
    return row


async def list_requests(
    session: AsyncSession, *, status: MatchStatus, cursor: str | None, limit: int
) -> tuple[list[MatchRequestOpsItem], str | None]:
    """Requests with this status, oldest first (the queue ops work through)."""
    query = select(MatchRequest).where(MatchRequest.status == status.value)
    if cursor is not None:
        at, row_id = pagination.decode_cursor(cursor)
        query = query.where(tuple_(MatchRequest.created_at, MatchRequest.id) > tuple_(at, row_id))
    rows = list(
        await session.scalars(query.order_by(MatchRequest.created_at, MatchRequest.id).limit(limit + 1))
    )
    page, next_cursor = pagination.page(rows, limit, lambda r: (r.created_at, r.id))
    counts = {
        request_id: n
        for request_id, n in (
            await session.execute(
                select(MatchShortlist.request_id, func.count())
                .where(MatchShortlist.request_id.in_([r.id for r in page]))
                .group_by(MatchShortlist.request_id)
            )
        ).all()
    }
    items = []
    for r in page:
        project = await projects.get_project(session, r.project_id)
        items.append(
            MatchRequestOpsItem(
                id=r.id,
                project_id=r.project_id,
                project_title=project.title,
                client_id=r.client_id,
                status=r.status,
                state=r.state,
                city=r.city,
                work_type=r.work_type,
                timeline=r.timeline,
                notes=r.notes,
                budget_minor=r.budget_minor,
                currency=r.currency,
                created_at=r.created_at,
                shortlist_count=counts.get(r.id, 0),
            )
        )
    return items, next_cursor


# --- Writing ------------------------------------------------------------------------------------------------


async def request_match(
    session: AsyncSession,
    client: User,
    project_id: uuid.UUID,
    data: MatchRequestIn,
    *,
    request: Request | None = None,
) -> MatchRequest:
    """A client asks for a contractor for their own draft project (the caller commits).

    - 403 not_project_member: not this project's client
    - 409 project_not_draft / project_has_contractor
    - 409 match_request_exists: an open or shortlisted request is already there
    """
    project = await _require_open_project(session, project_id, lock=True)
    if client.role != Role.CLIENT.value or project.client_id != client.id:
        raise AppError("not_project_member", "You are not on this project.", 403)
    active = await session.scalar(
        select(MatchRequest.id).where(
            MatchRequest.project_id == project_id, MatchRequest.status.in_(ACTIVE_MATCH_STATUSES)
        )
    )
    if active is not None:
        raise AppError("match_request_exists", "This project already has a contractor request.", 409)
    row = MatchRequest(
        project_id=project.id,
        client_id=client.id,
        state=data.state,
        city=data.city,
        work_type=data.work_type,
        timeline=data.timeline,
        notes=data.notes,
        budget_minor=project.budget_minor,
        currency=project.currency,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    await audit.record(
        session,
        client.id,
        "match_request.created",
        "match_request",
        row.id,
        None,
        audit.snapshot(row),
        request,
    )
    after_commit(session, match_notices.enqueue_ops_email, row.id)
    return row


async def _usable_profiles(session: AsyncSession, profile_ids: list[uuid.UUID]) -> list[ContractorProfile]:
    """The profiles, in the order asked, each approved, listed and with an active account; else 422."""
    found = {
        p.id: p
        for p in await session.scalars(select(ContractorProfile).where(ContractorProfile.id.in_(profile_ids)))
    }
    result = []
    for profile_id in profile_ids:
        profile = found.get(profile_id)
        user = await users.get_user(session, profile.user_id) if profile else None
        if (
            profile is None
            or profile.vetting_status != ProfileStatus.APPROVED.value
            or not profile.listed
            or user is None
            or user.status != UserStatus.ACTIVE.value
        ):
            raise AppError(
                "contractor_not_available",
                "Every contractor must be approved, listed and have an active account.",
                422,
            )
        result.append(profile)
    return result


async def shortlist(
    session: AsyncSession,
    request_id: uuid.UUID,
    contractor_ids: list[uuid.UUID],
    note: str | None,
    actor: User,
    *,
    request: Request | None = None,
) -> MatchRequest:
    """Ops put 1 to 3 contractors forward, or replace the list already there (the caller commits).

    - 404 match_request_not_found
    - 409 invalid_transition: the request is matched or cancelled
    - 409 project_not_draft / project_has_contractor: the project moved on
    - 422 contractor_not_available: a contractor isn't approved, listed and active
    """
    row = await _get(session, request_id, lock=True)
    if MatchStatus(row.status) in (MatchStatus.MATCHED, MatchStatus.CANCELLED):
        raise AppError(
            "invalid_transition", f"A match request can't be shortlisted when it is {row.status}.", 409
        )
    await _require_open_project(session, row.project_id)
    profiles = await _usable_profiles(session, contractor_ids)

    before = audit.snapshot(row)
    before["shortlist"] = [str(p.id) for p in await _profiles(session, row)]
    if row.status == MatchStatus.SHORTLISTED.value:
        _move(row, MatchStatus.OPEN, "ops")  # replacing a list goes back through open
        await session.execute(delete(MatchShortlist).where(MatchShortlist.request_id == row.id))
        await session.flush()
    for position, profile in enumerate(profiles, start=1):
        session.add(
            MatchShortlist(
                request_id=row.id, contractor_id=profile.id, position=position, added_by=actor.id, note=note
            )
        )
    _move(row, MatchStatus.SHORTLISTED, "ops")
    row.shortlist_version += 1
    await session.flush()
    await session.refresh(row)
    after = audit.snapshot(row)
    after["shortlist"] = [str(p.id) for p in profiles]
    await audit.record(
        session, actor.id, "match_request.shortlisted", "match_request", row.id, before, after, request
    )
    after_commit(session, match_notices.enqueue_notice, row.id, "shortlist")
    return row


async def choose(
    session: AsyncSession,
    request_id: uuid.UUID,
    contractor_id: uuid.UUID,
    client: User,
    *,
    request: Request | None = None,
) -> MatchRequest:
    """The client picks one shortlisted contractor: they are set on the project and told (the caller commits).

    - 404 match_request_not_found: not this client's request
    - 409 invalid_transition: the request isn't shortlisted
    - 422 contractor_not_on_shortlist
    - 409 contractor_not_available: they are no longer approved, listed and active
    - 409 project_not_draft / project_has_contractor: the project moved on
    """
    row = await _get(session, request_id, lock=True)
    _require_owner(row, client)
    if MatchStatus(row.status) is not MatchStatus.SHORTLISTED:
        raise AppError(
            "invalid_transition", f"A match request can't be chosen from when it is {row.status}.", 409
        )
    profiles = await _profiles(session, row)
    profile = next((p for p in profiles if p.id == contractor_id), None)
    if profile is None:
        raise AppError("contractor_not_on_shortlist", "Choose one of the contractors on your shortlist.", 422)
    contractor = await users.get_user(session, profile.user_id)
    if (
        contractor is None
        or profile.vetting_status != ProfileStatus.APPROVED.value
        or not profile.listed
        or contractor.status != UserStatus.ACTIVE.value
    ):
        raise AppError("contractor_not_available", "This contractor is no longer available.", 409)
    await _require_open_project(session, row.project_id, lock=True)
    assert contractor.phone is not None  # contractor accounts are made from a phone number
    # The same rules as inviting a contractor by phone: it must be an active contractor account.
    await users.invite_contractor(session, contractor.phone)

    before = audit.snapshot(row)
    _move(row, MatchStatus.MATCHED, "client")
    row.chosen_contractor_id = contractor.id
    row.decided_at = datetime.now(UTC)
    await projects.set_contractor(session, row.project_id, contractor.id, client.id, request=request)
    await session.flush()
    await session.refresh(row)
    await audit.record(
        session,
        client.id,
        "match_request.matched",
        "match_request",
        row.id,
        before,
        audit.snapshot(row),
        request,
    )
    after_commit(session, match_notices.enqueue_notice, row.id, "chosen")
    return row


async def cancel(
    session: AsyncSession,
    request_id: uuid.UUID,
    reason: str | None,
    user: User,
    *,
    request: Request | None = None,
) -> MatchRequest:
    """The client who made it, or ops, cancels an open or shortlisted request (the caller commits).

    - 404 match_request_not_found: not this client's request
    - 409 invalid_transition: it is already matched or cancelled
    """
    row = await _get(session, request_id, lock=True)
    actor: Actor = "ops" if user.role == Role.OPS.value else "client"
    if actor == "client":
        _require_owner(row, user)
    before = audit.snapshot(row)
    _move(row, MatchStatus.CANCELLED, actor)
    row.cancel_reason = reason or None
    row.decided_at = datetime.now(UTC)
    await session.flush()
    await session.refresh(row)
    await audit.record(
        session,
        user.id,
        "match_request.cancelled",
        "match_request",
        row.id,
        before,
        audit.snapshot(row),
        request,
    )
    return row
