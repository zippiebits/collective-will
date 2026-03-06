"""Tests for voice enrollment state machine."""

from __future__ import annotations

import base64
import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.voice.enrollment import (
    finalize_enrollment,
    get_current_phrase,
    init_enrollment_state,
    process_enrollment_audio,
)


@pytest.fixture(autouse=True)
def _mock_settings() -> None:  # type: ignore[misc]
    mock_settings = MagicMock()
    mock_settings.voice_enrollment_phrases_per_session = 3
    mock_settings.voice_enrollment_attempts_per_phrase = 2
    mock_settings.voice_enrollment_max_phrase_failures = 3
    mock_settings.voice_transcription_score_standard = 0.65
    mock_settings.voice_transcription_score_strict = 0.75
    mock_settings.voice_audio_min_duration_seconds = 2
    mock_settings.voice_audio_max_duration_seconds = 15
    mock_settings.voice_embedding_endpoint_url = "https://test.modal.run"
    mock_settings.voice_embedding_auth_token = None
    mock_settings.voice_embedding_timeout_seconds = 10.0
    mock_settings.voice_transcription_timeout_seconds = 5.0
    mock_settings.voice_cloud_max_retries = 1
    mock_settings.openai_api_key = "sk-test"
    with (
        patch("src.voice.enrollment.get_settings", return_value=mock_settings),
        patch("src.voice.audio.get_settings", return_value=mock_settings),
    ):
        yield


class TestInitEnrollmentState:
    def test_creates_state_with_correct_shape(self) -> None:
        state = init_enrollment_state("en")
        assert state["enrollment"] is True
        assert state["step"] == 0
        assert len(state["phrase_ids"]) == 3
        assert state["collected_embeddings"] == []
        assert state["attempt"] == 0
        assert state["failures"] == 0

    def test_excludes_ids(self) -> None:
        state = init_enrollment_state("en", exclude_ids=[0, 1, 2])
        for pid in state["phrase_ids"]:
            assert pid not in {0, 1, 2}


class TestGetCurrentPhrase:
    def test_returns_correct_phrase(self) -> None:
        state = {"step": 0, "phrase_ids": [5, 10, 15]}
        phrase_id, text = get_current_phrase(state, "en")
        assert phrase_id == 5
        assert isinstance(text, str)
        assert len(text) > 0


class TestProcessEnrollmentAudio:
    @pytest.mark.asyncio
    async def test_accepted_phrase(self) -> None:
        fake_embedding = [0.1] * 192
        mock_result = MagicMock()
        mock_result.transcription_score = 0.92  # >= strict (0.75) for acceptance
        mock_result.embedding = fake_embedding
        mock_result.model_version = "test"

        state = init_enrollment_state("en")
        user = MagicMock()
        user.locale = "en"
        channel = AsyncMock()
        channel.download_file = AsyncMock(return_value=b"fake-audio")
        session = AsyncMock()

        with patch("src.voice.enrollment.VoiceCloudClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.process_audio.return_value = mock_result
            MockClient.return_value = mock_client

            status, updated = await process_enrollment_audio(
                user=user, state=state, channel=channel,
                file_id="test_file", duration=5, session=session,
            )

        assert status == "phrase_accepted"
        assert updated["step"] == 1
        assert len(updated["collected_embeddings"]) == 1

    @pytest.mark.asyncio
    async def test_rejected_phrase_retry(self) -> None:
        mock_result = MagicMock()
        mock_result.transcription_score = 0.30  # Below strict threshold (0.90)
        mock_result.embedding = [0.1] * 192

        state = init_enrollment_state("en")
        user = MagicMock()
        user.id = MagicMock()
        user.locale = "en"
        channel = AsyncMock()
        channel.download_file = AsyncMock(return_value=b"fake-audio")
        session = AsyncMock()

        with patch("src.voice.enrollment.VoiceCloudClient") as MockClient, patch(
            "src.voice.enrollment.append_evidence", new_callable=AsyncMock
        ):
            mock_client = AsyncMock()
            mock_client.process_audio.return_value = mock_result
            MockClient.return_value = mock_client

            status, updated = await process_enrollment_audio(
                user=user, state=state, channel=channel,
                file_id="test_file", duration=5, session=session,
            )

        assert status == "phrase_retry"
        assert updated["attempt"] == 1

    @pytest.mark.asyncio
    async def test_voice_service_raises_returns_service_error(self) -> None:
        """When VoiceCloudClient.process_audio raises (500, timeout, etc.), return service_error."""
        state = init_enrollment_state("en")
        user = MagicMock()
        user.locale = "en"
        channel = AsyncMock()
        channel.download_file = AsyncMock(return_value=b"fake-audio")
        session = AsyncMock()

        with patch("src.voice.enrollment.VoiceCloudClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.process_audio.side_effect = Exception("voice-service 500")
            MockClient.return_value = mock_client

            status, updated = await process_enrollment_audio(
                user=user, state=state, channel=channel,
                file_id="test_file", duration=5, session=session,
            )

        assert status == "service_error"
        assert updated == state

    @pytest.mark.asyncio
    async def test_enrollment_complete_after_all_phrases(self) -> None:
        fake_embedding = [0.1] * 192
        emb_bytes = struct.pack(f"<{len(fake_embedding)}f", *fake_embedding)
        emb_b64 = base64.b64encode(emb_bytes).decode("ascii")

        mock_result = MagicMock()
        mock_result.transcription_score = 0.92  # >= strict (0.75) for acceptance
        mock_result.embedding = fake_embedding
        mock_result.model_version = "test"

        state = init_enrollment_state("en")
        # Simulate 2 already collected
        state["step"] = 2
        state["collected_embeddings"] = [emb_b64, emb_b64]

        user = MagicMock()
        user.locale = "en"
        channel = AsyncMock()
        channel.download_file = AsyncMock(return_value=b"fake-audio")
        session = AsyncMock()

        with patch("src.voice.enrollment.VoiceCloudClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.process_audio.return_value = mock_result
            MockClient.return_value = mock_client

            status, updated = await process_enrollment_audio(
                user=user, state=state, channel=channel,
                file_id="test_file", duration=5, session=session,
            )

        assert status == "enrollment_complete"


class TestFinalizeEnrollment:
    @pytest.mark.asyncio
    async def test_stores_averaged_embedding(self) -> None:
        emb1 = [1.0] * 192
        emb2 = [3.0] * 192
        emb1_bytes = struct.pack("<192f", *emb1)
        emb2_bytes = struct.pack("<192f", *emb2)

        state = {
            "collected_embeddings": [
                base64.b64encode(emb1_bytes).decode("ascii"),
                base64.b64encode(emb2_bytes).decode("ascii"),
            ],
            "phrase_ids": [0, 1, 2],
        }

        user = MagicMock()
        user.id = MagicMock()
        session = AsyncMock()

        with patch("src.voice.enrollment.append_evidence", new_callable=AsyncMock):
            await finalize_enrollment(user, state, session)

        assert user.voice_embedding is not None
        assert user.voice_enrolled_at is not None
        assert user.voice_verified_at is not None
        assert user.voice_model_version == "Jenthe/ECAPA2"
