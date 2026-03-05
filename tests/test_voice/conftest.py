"""Shared fixtures for voice tests."""

from __future__ import annotations

import pytest

import src.voice.phrases as phrases_mod

SAMPLE_EN = [f"Test phrase number {i} for English" for i in range(20)]
SAMPLE_FA = [f"جمله آزمایشی شماره {i} برای فارسی" for i in range(20)]


@pytest.fixture(autouse=True)
def _preload_phrases() -> None:  # type: ignore[misc]
    """Inject test phrases so no JSON file is needed."""
    phrases_mod._phrases = {"en": SAMPLE_EN, "fa": SAMPLE_FA}
    yield
    phrases_mod._phrases = None
