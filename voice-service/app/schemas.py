from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ProcessRequest(BaseModel):
    audio_b64: str = Field(..., description="Base64-encoded audio (OGG Opus or WAV)")
    expected_phrase: str = Field(..., description="Expected transcription text for scoring")
    language: Optional[str] = Field(
        default=None,
        description="Language code for transcription (e.g. 'en', 'fa'). If omitted, faster-whisper auto-detects.",
    )


class ProcessResponse(BaseModel):
    transcription: str
    transcription_score: float
    embedding: list[float]
    model_version: str


class HealthResponse(BaseModel):
    status: str
