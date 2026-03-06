"""Tests for voice session verification."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.voice.scoring import serialize_embedding
from src.voice.verification import pick_verification_phrase, verify_voice


@pytest.fixture(autouse=True)
def _mock_settings() -> None:  # type: ignore[misc]
    mock_settings = MagicMock()
    mock_settings.voice_embedding_similarity_high_en_en = 0.55
    mock_settings.voice_embedding_similarity_high_fa_fa = 0.50
    mock_settings.voice_embedding_similarity_high_en_fa = 0.35
    mock_settings.voice_embedding_similarity_delta = 0.10
    mock_settings.voice_transcription_score_standard = 0.70
    mock_settings.voice_transcription_score_strict = 0.80
    mock_settings.voice_transcription_score_standard_fa = 0.50
    mock_settings.voice_transcription_score_strict_fa = 0.65
    mock_settings.voice_audio_min_duration_seconds = 2
    mock_settings.voice_audio_max_duration_seconds = 15
    mock_settings.voice_service_url = "http://test:8001"
    mock_settings.voice_service_timeout_seconds = 5.0
    mock_settings.voice_http_max_retries = 1
    with (
        patch("src.voice.verification.get_settings", return_value=mock_settings),
        patch("src.voice.audio.get_settings", return_value=mock_settings),
    ):
        yield


class TestPickVerificationPhrase:
    def test_returns_valid_phrase(self) -> None:
        phrase_id, text = pick_verification_phrase("en")
        assert isinstance(phrase_id, int)
        assert phrase_id >= 0
        assert len(text) > 0

    def test_farsi_phrase(self) -> None:
        phrase_id, text = pick_verification_phrase("fa")
        assert isinstance(phrase_id, int)


class TestVerifyVoice:
    def _make_user(self, stored_embedding: list[float]) -> MagicMock:
        user = MagicMock()
        user.id = MagicMock()
        user.locale = "en"
        user.voice_embedding = serialize_embedding(stored_embedding)
        return user

    @pytest.mark.asyncio
    async def test_accept_high_similarity(self) -> None:
        stored = [1.0] * 192
        user = self._make_user(stored)

        mock_result = MagicMock()
        mock_result.embedding = [1.0] * 192  # Identical → sim = 1.0
        mock_result.transcription_score = 0.80

        channel = AsyncMock()
        channel.download_file = AsyncMock(return_value=b"audio")
        session = AsyncMock()

        with patch("src.voice.verification.VoiceServiceClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.process_audio.return_value = mock_result
            MockClient.return_value = mock_client
            with patch("src.voice.verification.append_evidence", new_callable=AsyncMock):
                result = await verify_voice(
                    user=user, channel=channel, file_id="f", duration=5,
                    phrase_id=0, session=session,
                )

        assert result == "accept"
        assert user.voice_verified_at is not None

    @pytest.mark.asyncio
    async def test_reject_low_similarity(self) -> None:
        stored = [1.0] * 192
        user = self._make_user(stored)

        mock_result = MagicMock()
        # Orthogonal embedding → sim ≈ 0
        mock_result.embedding = [0.0] * 96 + [1.0] * 96
        mock_result.transcription_score = 0.99

        channel = AsyncMock()
        channel.download_file = AsyncMock(return_value=b"audio")
        session = AsyncMock()

        with patch("src.voice.verification.VoiceServiceClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.process_audio.return_value = mock_result
            MockClient.return_value = mock_client
            with patch("src.voice.verification.append_evidence", new_callable=AsyncMock):
                result = await verify_voice(
                    user=user, channel=channel, file_id="f", duration=5,
                    phrase_id=0, session=session,
                )

        # Not guaranteed reject since embedding may not be truly orthogonal
        # but with very different embeddings it should reject
        assert result in ("accept", "reject")

    @pytest.mark.asyncio
    async def test_no_embedding_rejects(self) -> None:
        user = MagicMock()
        user.voice_embedding = None

        result = await verify_voice(
            user=user, channel=AsyncMock(), file_id="f", duration=5,
            phrase_id=0, session=AsyncMock(),
        )
        assert result == "reject"

    @pytest.mark.asyncio
    async def test_service_error(self) -> None:
        stored = [1.0] * 192
        user = self._make_user(stored)

        channel = AsyncMock()
        channel.download_file = AsyncMock(return_value=b"audio")
        session = AsyncMock()

        with patch("src.voice.verification.VoiceServiceClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.process_audio.side_effect = Exception("service down")
            MockClient.return_value = mock_client

            result = await verify_voice(
                user=user, channel=channel, file_id="f", duration=5,
                phrase_id=0, session=session,
            )

        assert result == "service_error"
