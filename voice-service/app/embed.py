"""SpeechBrain ECAPA-TDNN 192-dim embedding extraction."""

from __future__ import annotations

import io
import logging

import torch
import torchaudio
from speechbrain.inference.speaker import EncoderClassifier

logger = logging.getLogger(__name__)

_model: EncoderClassifier | None = None
MODEL_VERSION = "speechbrain/spkrec-ecapa-voxceleb"


def load_model() -> EncoderClassifier:
    """Load (or return cached) ECAPA-TDNN model."""
    global _model
    if _model is None:
        logger.info("Loading ECAPA-TDNN model: %s", MODEL_VERSION)
        _model = EncoderClassifier.from_hparams(
            source=MODEL_VERSION,
            savedir="/app/models/ecapa",
            run_opts={"device": "cpu"},
        )
        logger.info("ECAPA-TDNN model loaded")
    return _model


def extract_embedding(wav_bytes: bytes) -> list[float]:
    """Extract 192-dim speaker embedding from 16kHz mono WAV bytes."""
    model = load_model()

    waveform, sample_rate = torchaudio.load(io.BytesIO(wav_bytes))
    if sample_rate != 16000:
        resampler = torchaudio.transforms.Resample(sample_rate, 16000)
        waveform = resampler(waveform)

    with torch.no_grad():
        embedding = model.encode_batch(waveform)

    return embedding.squeeze().tolist()
