"""Voice error codes for user-facing technical failures.

Codes are stable and can be documented (e.g. on a transparency page).
Users can report a code when asking for support.
"""

from __future__ import annotations

from typing import Literal

# Technical failure codes (voice verification / enrollment pipeline)
VoiceErrorCode = Literal["V001", "V002", "V003", "V004"]

# Human-readable descriptions for docs/support (not sent to user in Telegram)
VOICE_ERROR_DESCRIPTIONS: dict[VoiceErrorCode, str] = {
    "V001": "Audio validation failed (too short or too long)",
    "V002": "Could not download audio from platform",
    "V003": "Voice service error (transcription or embedding)",
    "V004": "Scoring error (embedding format or comparison)",
}
