"""Settings for escrow, kept here so core/config.py stays Christopher's. Owner: Gabriel.

ESCROW_PROVIDER=simulated   # which EscrowProvider get_escrow_provider() returns
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class EscrowSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Add the real partner's name here once one signs (spec, open decision 2).
    escrow_provider: Literal["simulated"] = "simulated"


@lru_cache
def get_escrow_settings() -> EscrowSettings:
    return EscrowSettings()
