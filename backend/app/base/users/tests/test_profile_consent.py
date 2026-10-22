"""PATCH /me (own name, country, time zone) and NDPA 2023 consent (GET/POST /me/consent)."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.models import AuditEntry
from app.base.users import service
from app.base.users.models import User
from app.base.users.tests.conftest import make_user
from app.core.config import get_settings


def _bearer(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {service.create_access_token(user)}"}


async def _audit(session: AsyncSession, user_id: object, action: str) -> list[AuditEntry]:
    rows = await session.scalars(
        select(AuditEntry).where(AuditEntry.object_id == user_id, AuditEntry.action == action)
    )
    return list(rows)


async def test_a_person_updates_their_own_name_country_and_time_zone(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    response = await client.patch(
        "/api/v1/me",
        json={"full_name": "  Adaeze Okafor ", "country": "GB", "timezone": "Europe/London"},
        headers=_bearer(user),
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["full_name"], body["country"], body["timezone"]) == ("Adaeze Okafor", "GB", "Europe/London")

    # Audited with only the fields that changed, never the phone or email.
    (entry,) = await _audit(db_session, user.id, "user.profile_updated")
    assert entry.before == {"full_name": None, "country": None, "timezone": "UTC"}
    assert entry.after == {"full_name": "Adaeze Okafor", "country": "GB", "timezone": "Europe/London"}
    assert "phone" not in (entry.after or {})


async def test_only_the_fields_sent_change_and_nothing_changed_writes_no_audit(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    user.full_name = "Chukwuemeka Nwosu"
    await db_session.flush()
    response = await client.patch("/api/v1/me", json={"country": "NG"}, headers=_bearer(user))
    assert response.json()["full_name"] == "Chukwuemeka Nwosu"
    again = await client.patch("/api/v1/me", json={"country": "NG"}, headers=_bearer(user))
    assert again.status_code == 200
    assert len(await _audit(db_session, user.id, "user.profile_updated")) == 1


async def test_bad_values_and_identifiers_are_refused(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    headers = _bearer(user)
    bad_zone = await client.patch("/api/v1/me", json={"timezone": "Mars/Olympus"}, headers=headers)
    assert (bad_zone.status_code, bad_zone.json()["error"]["code"]) == (422, "invalid_timezone")
    blank = await client.patch("/api/v1/me", json={"full_name": "   "}, headers=headers)
    assert (blank.status_code, blank.json()["error"]["code"]) == (422, "invalid_full_name")
    assert (await client.patch("/api/v1/me", json={"country": "gbr"}, headers=headers)).status_code == 422
    # Phone and email are sign-in identifiers: not changeable here.
    assert (
        await client.patch("/api/v1/me", json={"email": "x@example.com"}, headers=headers)
    ).status_code == 422
    assert (
        await client.patch("/api/v1/me", json={"phone": "+447911123456"}, headers=headers)
    ).status_code == 422
    assert (await client.patch("/api/v1/me", json={"role": "ops"}, headers=headers)).status_code == 422


async def test_signed_out_can_t_update_or_consent(client: AsyncClient) -> None:
    assert (await client.patch("/api/v1/me", json={"country": "GB"})).status_code == 401
    assert (await client.get("/api/v1/me/consent")).status_code == 401


async def test_consent_to_the_current_versions(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    headers = _bearer(user)
    settings = get_settings()

    me = (await client.get("/api/v1/me", headers=headers)).json()
    assert me["consent_required"] is True
    current = (await client.get("/api/v1/me/consent", headers=headers)).json()
    assert current == {
        "terms_version": settings.terms_version,
        "privacy_version": settings.privacy_version,
        "consented_at": None,
        "consent_required": True,
    }

    agreed = await client.post(
        "/api/v1/me/consent",
        json={"terms_version": settings.terms_version, "privacy_version": settings.privacy_version},
        headers=headers,
    )
    assert agreed.status_code == 200
    assert agreed.json()["consent_required"] is False
    assert agreed.json()["consented_at"] is not None
    assert (await client.get("/api/v1/me", headers=headers)).json()["consent_required"] is False
    assert len(await _audit(db_session, user.id, "user.consented")) == 1

    # Agreeing again changes nothing and writes no second entry.
    await client.post(
        "/api/v1/me/consent",
        json={"terms_version": settings.terms_version, "privacy_version": settings.privacy_version},
        headers=headers,
    )
    assert len(await _audit(db_session, user.id, "user.consented")) == 1


async def test_consent_to_an_outdated_version_is_refused(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    response = await client.post(
        "/api/v1/me/consent",
        json={"terms_version": "1999-01-01", "privacy_version": get_settings().privacy_version},
        headers=_bearer(user),
    )
    assert (response.status_code, response.json()["error"]["code"]) == (409, "consent_version_outdated")
    assert user.consented_at is None


async def test_a_new_version_asks_everyone_again(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    settings = get_settings()
    await service.record_consent(db_session, user, settings.terms_version, settings.privacy_version)
    assert service.consent_required(user, settings) is False
    newer = settings.model_copy(update={"privacy_version": "2099-01-01"})
    assert service.consent_required(user, newer) is True
