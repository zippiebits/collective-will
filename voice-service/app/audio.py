"""Audio conversion: OGG Opus -> 16kHz mono WAV for model input."""

from __future__ import annotations

import io
import tempfile

from pydub import AudioSegment


def convert_to_wav16k(audio_bytes: bytes) -> bytes:
    """Convert arbitrary audio bytes (OGG Opus, etc.) to 16kHz mono WAV.

    Returns raw WAV bytes suitable for SpeechBrain / WhisperX.
    """
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=True) as tmp:
        tmp.write(audio_bytes)
        tmp.flush()
        segment = AudioSegment.from_file(tmp.name)

    segment = segment.set_channels(1).set_frame_rate(16000).set_sample_width(2)

    buf = io.BytesIO()
    segment.export(buf, format="wav")
    return buf.getvalue()
