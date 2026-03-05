"""HTTP client for the voice inference service."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VoiceProcessResult:
    transcription: str
    transcription_score: float
    embedding: list[float]
    model_version: str


class VoiceServiceClient:
    """Thin async HTTP client wrapping the voice-service /process endpoint."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.voice_service_url.rstrip("/")
        self._timeout = settings.voice_service_timeout_seconds
        self._max_retries = settings.voice_http_max_retries

    async def process_audio(
        self, audio_bytes: bytes, expected_phrase: str
    ) -> VoiceProcessResult:
        """Send audio to the voice service for embedding + transcription.

        Raises httpx.HTTPError on failure after retries.
        """
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        payload = {"audio_b64": audio_b64, "expected_phrase": expected_phrase}

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        f"{self._base_url}/process", json=payload
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return VoiceProcessResult(
                        transcription=data["transcription"],
                        transcription_score=data["transcription_score"],
                        embedding=data["embedding"],
                        model_version=data["model_version"],
                    )
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                last_exc = exc
                logger.warning(
                    "Voice service attempt %d/%d failed: %s",
                    attempt, self._max_retries, exc,
                )

        raise last_exc  # type: ignore[misc]

    async def health_check(self) -> bool:
        """Return True if the voice service is healthy."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/health")
                return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False
