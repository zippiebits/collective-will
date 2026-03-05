"""WhisperX transcription with word-overlap scoring."""

from __future__ import annotations

import logging
import re
import tempfile
from typing import Any

import whisperx

logger = logging.getLogger(__name__)

_model: Any = None


def load_model() -> Any:
    """Load (or return cached) WhisperX model."""
    global _model
    if _model is None:
        logger.info("Loading WhisperX model")
        _model = whisperx.load_model(
            "base",
            device="cpu",
            compute_type="int8",
        )
        logger.info("WhisperX model loaded")
    return _model


def _normalize_text(text: str) -> list[str]:
    """Lowercase, strip punctuation, split into words."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    return text.split()


def word_overlap_score(transcription: str, expected: str) -> float:
    """Compute word overlap score between transcription and expected phrase.

    Returns a float in [0, 1] representing the fraction of expected words
    found in the transcription.
    """
    trans_words = set(_normalize_text(transcription))
    expected_words = _normalize_text(expected)

    if not expected_words:
        return 1.0

    matches = sum(1 for w in expected_words if w in trans_words)
    return matches / len(expected_words)


def transcribe_audio(wav_bytes: bytes, expected_phrase: str) -> tuple[str, float]:
    """Transcribe audio and score against expected phrase.

    Returns (transcription_text, overlap_score).
    """
    model = load_model()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        tmp.write(wav_bytes)
        tmp.flush()
        audio = whisperx.load_audio(tmp.name)

    result = model.transcribe(audio)
    segments = result.get("segments", [])
    transcription = " ".join(seg.get("text", "") for seg in segments).strip()

    score = word_overlap_score(transcription, expected_phrase)
    return transcription, score
