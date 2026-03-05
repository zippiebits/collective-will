"""Tests for voice gate in route_message and voice-related command flows."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.channels.types import UnifiedMessage
from src.handlers.commands import route_message


def _make_user(
    *,
    enrolled: bool = False,
    session_active: bool = False,
    bot_state: str | None = None,
    bot_state_data: dict | None = None,
) -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.locale = "en"
    user.messaging_account_ref = "ref-test"
    user.bot_state = bot_state
    user.bot_state_data = bot_state_data
    user.is_voice_enrolled = enrolled
    user.is_voice_session_active = session_active
    user.voice_embedding = b"\x00" * 768 if enrolled else None
    user.voice_enrolled_at = datetime.now(UTC) if enrolled else None
    user.voice_verified_at = datetime.now(UTC) if session_active else None
    return user


def _make_text_message(text: str = "hello") -> UnifiedMessage:
    return UnifiedMessage(
        text=text,
        sender_ref="ref-test",
        platform="telegram",
        message_id="msg-1",
    )


def _make_voice_message(file_id: str = "voice-123", duration: int = 5) -> UnifiedMessage:
    return UnifiedMessage(
        text="",
        sender_ref="ref-test",
        platform="telegram",
        message_id="msg-2",
        voice_file_id=file_id,
        voice_duration=duration,
    )


class TestVoiceGateNotEnrolled:
    """User exists but is not voice-enrolled."""

    @pytest.mark.asyncio
    async def test_text_message_prompts_enrollment(self) -> None:
        user = _make_user(enrolled=False)
        session = AsyncMock()
        channel = AsyncMock()
        msg = _make_text_message()

        # Mock user lookup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        session.execute = AsyncMock(return_value=mock_result)

        result = await route_message(session=session, message=msg, channel=channel)
        assert result == "voice_enrollment_needed"
        channel.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_voice_message_starts_enrollment(self) -> None:
        user = _make_user(enrolled=False)
        session = AsyncMock()
        channel = AsyncMock()
        msg = _make_voice_message()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        session.execute = AsyncMock(return_value=mock_result)

        with patch("src.handlers.commands.start_enrollment", new_callable=AsyncMock) as mock_enroll:
            mock_enroll.return_value = {
                "enrollment": True, "step": 0, "phrase_ids": [1, 2, 3],
                "collected_embeddings": [], "attempt": 0, "failures": 0,
                "failed_phrase_ids": [],
            }
            result = await route_message(session=session, message=msg, channel=channel)

        assert result == "voice_enrollment_started"


class TestVoiceGateExpiredSession:
    """User is enrolled but session expired."""

    @pytest.mark.asyncio
    async def test_text_triggers_verification_prompt(self) -> None:
        user = _make_user(enrolled=True, session_active=False)
        session = AsyncMock()
        channel = AsyncMock()
        msg = _make_text_message()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        session.execute = AsyncMock(return_value=mock_result)

        with patch("src.handlers.commands.check_voice_rate_limit", return_value=True):
            result = await route_message(session=session, message=msg, channel=channel)

        assert result == "voice_verification_prompted"


class TestVoiceGateActiveSession:
    """User is enrolled and session is active — should pass through."""

    @pytest.mark.asyncio
    async def test_text_message_shows_menu(self) -> None:
        user = _make_user(enrolled=True, session_active=True)
        session = AsyncMock()
        channel = AsyncMock()
        msg = _make_text_message()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        session.execute = AsyncMock(return_value=mock_result)

        result = await route_message(session=session, message=msg, channel=channel)
        assert result == "menu_resent"


class TestVoiceRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limited_verification(self) -> None:
        user = _make_user(enrolled=True, session_active=False)
        session = AsyncMock()
        channel = AsyncMock()
        msg = _make_text_message()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        session.execute = AsyncMock(return_value=mock_result)

        with patch("src.handlers.commands.check_voice_rate_limit", return_value=False):
            result = await route_message(session=session, message=msg, channel=channel)

        assert result == "voice_rate_limited"
