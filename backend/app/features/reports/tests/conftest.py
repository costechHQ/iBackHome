"""Fixtures for report tests."""

from collections.abc import Iterator
from typing import Any

import pytest
from google import genai


@pytest.fixture(autouse=True)
def _never_call_gemini(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Tests use fake models; creating a real Gemini client fails the test instead of using the quota."""

    def refuse(*_: Any, **__: Any) -> None:
        raise RuntimeError("a test tried to call the real Gemini API; pass a fake client instead")

    monkeypatch.setattr(genai, "Client", refuse)
    yield
