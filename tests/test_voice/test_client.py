"""Tests for VoiceServiceClient HTTP interactions."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.voice.client import VoiceServiceClient


@pytest.fixture(autouse=True)
def _mock_settings() -> None:  # type: ignore[misc]
    """Mock settings for all tests in this module."""
    mock_settings = MagicMock()
    mock_settings.voice_service_url = "http://test-voice:8001"
    mock_settings.voice_service_timeout_seconds = 5.0
    mock_settings.voice_http_max_retries = 2
    with patch("src.voice.client.get_settings", return_value=mock_settings):
        yield


class TestVoiceServiceClient:
    @pytest.mark.asyncio
    async def test_process_audio_success(self) -> None:
        response_data = {
            "transcription": "hello world",
            "transcription_score": 0.95,
            "embedding": [0.1] * 192,
            "model_version": "test-v1",
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            client = VoiceServiceClient()
            result = await client.process_audio(b"fake-audio", "hello world")

            assert result.transcription == "hello world"
            assert result.transcription_score == 0.95
            assert len(result.embedding) == 192
            assert result.model_version == "test-v1"

    @pytest.mark.asyncio
    async def test_process_audio_retry_on_timeout(self) -> None:
        """Should retry on timeout and eventually raise."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            client = VoiceServiceClient()
            with pytest.raises(httpx.TimeoutException):
                await client.process_audio(b"fake-audio", "hello world")

    @pytest.mark.asyncio
    async def test_health_check_success(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            client = VoiceServiceClient()
            assert await client.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self) -> None:
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            client = VoiceServiceClient()
            assert await client.health_check() is False
