from __future__ import annotations

from pydantic import BaseModel, Field


class ProcessRequest(BaseModel):
    audio_b64: str = Field(..., description="Base64-encoded audio (OGG Opus or WAV)")
    expected_phrase: str = Field(..., description="Expected transcription text for scoring")


class ProcessResponse(BaseModel):
    transcription: str
    transcription_score: float
    embedding: list[float]
    model_version: str


class HealthResponse(BaseModel):
    status: str
