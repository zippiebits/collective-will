"""Phrase pool for voice enrollment and verification.

Phrases are loaded from an external JSON file (not committed to repo).
The file path is configured via VOICE_PHRASES_FILE setting.
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path

_phrases: dict[str, list[str]] | None = None


def _load_phrases() -> dict[str, list[str]]:
    global _phrases
    if _phrases is not None:
        return _phrases

    from src.config import get_settings

    settings = get_settings()
    path = Path(settings.voice_phrases_file)
    if not path.is_file():
        raise FileNotFoundError(
            f"Voice phrases file not found: {path.resolve()}. "
            "See voice-phrases.json.example for the expected format."
        )

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict) or "en" not in data or "fa" not in data:
        raise ValueError("voice-phrases.json must contain 'en' and 'fa' keys")

    for locale in ("en", "fa"):
        pool = data[locale]
        if not isinstance(pool, list) or len(pool) < 3:
            raise ValueError(f"voice-phrases.json '{locale}' must have at least 3 phrases")
        for i, phrase in enumerate(pool):
            if not isinstance(phrase, str) or not phrase.strip():
                raise ValueError(f"voice-phrases.json '{locale}[{i}]' is empty or not a string")

    _phrases = {"en": data["en"], "fa": data["fa"]}
    return _phrases


def _get_pool(locale: str) -> list[str]:
    phrases = _load_phrases()
    return phrases["fa"] if locale == "fa" else phrases["en"]


def pool_size(locale: str) -> int:
    """Return the number of phrases available for the given locale."""
    return len(_get_pool(locale))


def select_phrases(
    locale: str,
    count: int,
    exclude_ids: list[int] | None = None,
) -> list[int]:
    """Select `count` random phrase IDs for the given locale.

    Args:
        locale: "fa" or "en".
        count: Number of phrases to select.
        exclude_ids: Phrase IDs to exclude (already used/failed).

    Returns:
        List of phrase indices (0-based) into the phrase pool.
    """
    pool = _get_pool(locale)
    available = list(range(len(pool)))
    if exclude_ids:
        available = [i for i in available if i not in set(exclude_ids)]

    if len(available) < count:
        raise ValueError(f"Not enough phrases: need {count}, have {len(available)}")

    selected: list[int] = []
    remaining = list(available)
    for _ in range(count):
        idx = secrets.randbelow(len(remaining))
        selected.append(remaining.pop(idx))
    return selected


def get_phrase(locale: str, phrase_id: int) -> str:
    """Get phrase text by locale and ID."""
    pool = _get_pool(locale)
    if phrase_id < 0 or phrase_id >= len(pool):
        raise ValueError(f"Invalid phrase_id {phrase_id} for locale {locale}")
    return pool[phrase_id]


def _reset_cache() -> None:
    """Reset loaded phrases (for testing only)."""
    global _phrases
    _phrases = None
