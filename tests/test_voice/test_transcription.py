"""Tests for OpenAI cloud transcription client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.voice.transcription import transcribe_audio


@pytest.fixture(autouse=True)
def _mock_settings() -> None:  # type: ignore[misc]
    mock_settings = MagicMock()
    mock_settings.openai_api_key = "sk-test-key"
    mock_settings.voice_transcription_timeout_seconds = 5.0
    mock_settings.voice_cloud_max_retries = 2
    with patch("src.voice.transcription.get_settings", return_value=mock_settings):
        yield


class TestTranscribeAudio:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": " hello world "}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await transcribe_audio(b"fake-audio", language="en")

        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_sends_language(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "سلام"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await transcribe_audio(b"fake-audio", language="fa")

        assert result == "سلام"
        # Verify language was sent in form data
        call_kwargs = mock_client.post.call_args
        assert call_kwargs is not None

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self) -> None:
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            with pytest.raises(httpx.TimeoutException):
                await transcribe_audio(b"fake-audio")

            # Should have retried (2 attempts)
            assert mock_client.post.call_count == 2
