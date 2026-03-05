"""SpeechBrain ECAPA-TDNN 192-dim embedding extraction."""

from __future__ import annotations

import io
import logging
import os

import numpy  # noqa: F401 — must be imported before torch to avoid double-load of C extension
import torch
import torchaudio
from speechbrain.inference.speaker import EncoderClassifier

logger = logging.getLogger(__name__)

_model: EncoderClassifier | None = None
MODEL_VERSION = "speechbrain/spkrec-ecapa-voxceleb"
_DEFAULT_SAVEDIR = "/app/models/ecapa"


def load_model() -> EncoderClassifier:
    """Load (or return cached) ECAPA-TDNN model."""
    global _model
    if _model is None:
        savedir = os.environ.get("ECAPA_MODEL_DIR", _DEFAULT_SAVEDIR)
        logger.info("Loading ECAPA-TDNN model: %s (savedir=%s)", MODEL_VERSION, savedir)
        _model = EncoderClassifier.from_hparams(
            source=MODEL_VERSION,
            savedir=savedir,
            run_opts={"device": "cpu"},
        )
        logger.info("ECAPA-TDNN model loaded")
    return _model


def extract_embedding(wav_bytes: bytes) -> list[float]:
    """Extract 192-dim speaker embedding from 16kHz mono WAV bytes."""
    model = load_model()

    waveform, sample_rate = torchaudio.load(io.BytesIO(wav_bytes), format="wav")

    if sample_rate != 16000:
        resampler = torchaudio.transforms.Resample(sample_rate, 16000)
        waveform = resampler(waveform)

    with torch.no_grad():
        embedding = model.encode_batch(waveform)

    return embedding.squeeze().tolist()
