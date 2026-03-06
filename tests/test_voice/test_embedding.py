"""Tests for Modal cloud embedding client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.voice.embedding import get_speaker_embedding


@pytest.fixture(autouse=True)
def _mock_settings() -> None:  # type: ignore[misc]
    mock_settings = MagicMock()
    mock_settings.voice_embedding_endpoint_url = "https://test--process.modal.run"
    mock_settings.voice_embedding_auth_token = "test-token"
    mock_settings.voice_embedding_timeout_seconds = 10.0
    mock_settings.voice_cloud_max_retries = 2
    with patch("src.voice.embedding.get_settings", return_value=mock_settings):
        yield


class TestGetSpeakerEmbedding:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        response_data = {
            "embedding": [0.1] * 192,
            "model_version": "Jenthe/ECAPA2",
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

            embedding, model_version = await get_speaker_embedding(b"fake-audio")

        assert len(embedding) == 192
        assert model_version == "Jenthe/ECAPA2"

    @pytest.mark.asyncio
    async def test_sends_auth_header(self) -> None:
        response_data = {"embedding": [0.1] * 192, "model_version": "test"}
        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            await get_speaker_embedding(b"fake-audio")

            call_kwargs = mock_client.post.call_args
            headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
            assert "Bearer test-token" in str(headers)

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self) -> None:
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            with pytest.raises(httpx.TimeoutException):
                await get_speaker_embedding(b"fake-audio")

            assert mock_client.post.call_count == 2
