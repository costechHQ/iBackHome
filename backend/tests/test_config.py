import pytest

from app.core.config import Settings


@pytest.mark.parametrize("scheme", ["postgresql", "postgres"])
def test_plain_postgres_url_gets_the_psycopg_driver(scheme):
    settings = Settings(database_url=f"{scheme}://u:p@host:5432/db")
    assert settings.database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_url_with_driver_is_unchanged():
    url = "postgresql+psycopg://u:p@host:5432/db"
    assert Settings(database_url=url).database_url == url
