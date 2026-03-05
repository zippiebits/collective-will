"""Audio download and validation for voice verification."""

from __future__ import annotations

import logging

from src.channels.base import BaseChannel
from src.config import get_settings

logger = logging.getLogger(__name__)


class AudioValidationError(Exception):
    """Raised when audio fails pre-checks (too short, too long)."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


async def download_and_validate_audio(
    channel: BaseChannel,
    file_id: str,
    duration: int | None,
) -> bytes:
    """Download audio via channel and validate duration.

    Args:
        channel: The messaging channel to download from.
        file_id: Platform-specific file identifier.
        duration: Duration in seconds reported by the platform (may be None).

    Returns:
        Raw audio bytes.

    Raises:
        AudioValidationError: If duration is outside allowed bounds.
    """
    settings = get_settings()

    if duration is not None:
        if duration < settings.voice_audio_min_duration_seconds:
            raise AudioValidationError("too_short")
        if duration > settings.voice_audio_max_duration_seconds:
            raise AudioValidationError("too_long")

    audio_bytes = await channel.download_file(file_id)
    return audio_bytes
