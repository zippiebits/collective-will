"""Voice error codes for user-facing technical failures.

Codes are stable and can be documented (e.g. on a transparency page).
Users can report a code when asking for support.
"""

from __future__ import annotations

from typing import Literal

# Technical failure codes only (pipeline failures for debugging).
# Duration validation (too short/long) is user-facing and uses voice_audio_too_short / voice_audio_too_long.
VoiceErrorCode = Literal["V002", "V003", "V004"]

# Human-readable descriptions for docs/support (not sent to user in Telegram)
VOICE_ERROR_DESCRIPTIONS: dict[VoiceErrorCode, str] = {
    "V002": "Could not download audio from platform",
    "V003": "Voice service error (transcription or embedding)",
    "V004": "Scoring error (embedding format or comparison)",
}
