"""Voice processing client: cloud transcription + cloud embedding + local scoring."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from src.voice.embedding import get_speaker_embedding
from src.voice.transcription import transcribe_audio
from src.voice.transcription_scoring import score_transcription

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VoiceProcessResult:
    transcription: str
    transcription_score: float
    embedding: list[float]
    model_version: str


class VoiceCloudClient:
    """Calls OpenAI for transcription + Modal for embedding, scores locally."""

    async def process_audio(
        self,
        audio_bytes: bytes,
        expected_phrase: str,
        language: str | None = None,
    ) -> VoiceProcessResult:
        """Process audio: transcribe (OpenAI) + embed (Modal) in parallel, score locally.

        Raises on API failure after retries.
        """
        lang = (language or "en").strip().lower()

        # Run transcription and embedding in parallel
        transcript_task = transcribe_audio(audio_bytes, language=lang)
        embedding_task = get_speaker_embedding(audio_bytes)

        transcript, (embedding, model_version) = await asyncio.gather(
            transcript_task, embedding_task,
        )

        score = score_transcription(transcript, expected_phrase, lang)

        return VoiceProcessResult(
            transcription=transcript,
            transcription_score=score,
            embedding=embedding,
            model_version=model_version,
        )
