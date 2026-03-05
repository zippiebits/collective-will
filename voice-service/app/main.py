"""Voice inference service — SpeechBrain embedding + faster-whisper transcription."""

from __future__ import annotations

import base64
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException

from app.audio import convert_to_wav16k
from app.embed import MODEL_VERSION, extract_embedding, load_model as load_embed_model
from app.schemas import HealthResponse, ProcessRequest, ProcessResponse
from app.transcribe import load_model as load_transcribe_model, transcribe_audio

logger = logging.getLogger(__name__)

_models_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _models_ready
    logger.info("Warming up models...")
    load_embed_model()
    load_transcribe_model()
    _models_ready = True
    logger.info("Models ready")
    yield


app = FastAPI(title="Voice Inference Service", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    if not _models_ready:
        raise HTTPException(status_code=503, detail="Models not ready")
    return HealthResponse(status="ok")


@app.post("/process", response_model=ProcessResponse)
def process(req: ProcessRequest) -> ProcessResponse:
    """Sync handler — FastAPI runs it in a thread pool automatically,
    preventing CPU-bound SpeechBrain/faster-whisper inference from blocking
    the event loop (and starving /health checks)."""
    if not _models_ready:
        raise HTTPException(status_code=503, detail="Models not ready")

    try:
        audio_bytes = base64.b64decode(req.audio_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 audio data")

    wav_bytes = convert_to_wav16k(audio_bytes)
    embedding = extract_embedding(wav_bytes)
    transcription, transcription_score = transcribe_audio(
        wav_bytes, req.expected_phrase, language=req.language
    )

    return ProcessResponse(
        transcription=transcription,
        transcription_score=transcription_score,
        embedding=embedding,
        model_version=MODEL_VERSION,
    )
