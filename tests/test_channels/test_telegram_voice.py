"""Tests for Telegram voice message parsing and file download."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.channels.telegram import TelegramChannel


@pytest.fixture
def channel() -> TelegramChannel:
    session = AsyncMock()
    with patch("src.channels.telegram.get_settings") as mock_settings:
        mock_settings.return_value.telegram_http_timeout_seconds = 5.0
        ch = TelegramChannel(bot_token="test-token", session=session)
    return ch


class TestVoiceParsing:
    @pytest.mark.asyncio
    async def test_parse_voice_message(self, channel: TelegramChannel) -> None:
        payload = {
            "message": {
                "message_id": 123,
                "chat": {"id": 456},
                "date": 1700000000,
                "voice": {
                    "file_id": "voice_file_abc",
                    "duration": 5,
                },
            }
        }

        with patch(
            "src.channels.telegram.get_or_create_account_ref",
            new_callable=AsyncMock,
            return_value="ref-456",
        ):
            msg = await channel.parse_webhook(payload)

        assert msg is not None
        assert msg.voice_file_id == "voice_file_abc"
        assert msg.voice_duration == 5
        assert msg.text == ""
        assert msg.platform == "telegram"

    @pytest.mark.asyncio
    async def test_parse_text_message_no_voice(self, channel: TelegramChannel) -> None:
        payload = {
            "message": {
                "message_id": 123,
                "chat": {"id": 456},
                "date": 1700000000,
                "text": "hello",
            }
        }

        with patch(
            "src.channels.telegram.get_or_create_account_ref",
            new_callable=AsyncMock,
            return_value="ref-456",
        ):
            msg = await channel.parse_webhook(payload)

        assert msg is not None
        assert msg.voice_file_id is None
        assert msg.text == "hello"

    @pytest.mark.asyncio
    async def test_parse_voice_without_text(self, channel: TelegramChannel) -> None:
        """Voice messages should be parsed even without text field."""
        payload = {
            "message": {
                "message_id": 123,
                "chat": {"id": 456},
                "date": 1700000000,
                "voice": {"file_id": "abc", "duration": 3},
            }
        }

        with patch(
            "src.channels.telegram.get_or_create_account_ref",
            new_callable=AsyncMock,
            return_value="ref-456",
        ):
            msg = await channel.parse_webhook(payload)

        assert msg is not None
        assert msg.voice_file_id == "abc"


class TestDownloadFile:
    @pytest.mark.asyncio
    async def test_download_file(self, channel: TelegramChannel) -> None:
        get_file_response = MagicMock()
        get_file_response.json.return_value = {
            "result": {"file_path": "voice/file_0.oga"}
        }
        get_file_response.raise_for_status = MagicMock()

        download_response = MagicMock()
        download_response.content = b"audio-bytes-here"
        download_response.raise_for_status = MagicMock()

        channel.client = AsyncMock()
        channel.client.post = AsyncMock(return_value=get_file_response)
        channel.client.get = AsyncMock(return_value=download_response)

        result = await channel.download_file("voice_file_abc")
        assert result == b"audio-bytes-here"

        # Verify getFile was called
        channel.client.post.assert_called_once()
        # Verify download was called
        channel.client.get.assert_called_once()
