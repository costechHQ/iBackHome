"""The seeded people have agreed to the current terms and privacy policy (seed.py v6)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service
from scripts import seed


async def test_seeded_people_have_consented_and_seeding_again_changes_nothing(
    db_session: AsyncSession,
) -> None:
    person = seed.USERS[0]
    user = await seed.upsert_user(db_session, person)
    assert service.consent_required(user) is False
    first = user.consented_at
    again = await seed.upsert_user(db_session, person)
    assert again.consented_at == first
