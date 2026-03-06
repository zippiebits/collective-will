"""Modal serverless function for speaker embedding using ECAPA2.

Deploy: modal deploy modal_functions/voice_embedding.py
Test:   modal run modal_functions/voice_embedding.py
"""

from __future__ import annotations

import modal

app = modal.App("collective-will-voice")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install(
        "torch",
        "torchaudio",
        "huggingface_hub",
        "pydub",
        "soundfile",
        "numpy",
        "fastapi[standard]",  # required for @modal.fastapi_endpoint
    )
    # Bake the ECAPA2 model into the image so cold starts don't download it
    .run_commands("python -c \"from huggingface_hub import hf_hub_download; hf_hub_download('Jenthe/ECAPA2', 'ecapa2.pt')\"")
)

MODEL_VERSION = "Jenthe/ECAPA2"


@app.cls(image=image, cpu=2, memory=1024, timeout=600, secrets=[modal.Secret.from_name("huggingface", required_keys=["HF_TOKEN"])])
class VoiceEmbedding:
    @modal.enter()
    def load_model(self) -> None:
        import torch
        from huggingface_hub import hf_hub_download

        model_path = hf_hub_download(MODEL_VERSION, "ecapa2.pt")
        self.model = torch.jit.load(model_path, map_location="cpu")
        self.model.eval()

    def _audio_to_waveform(self, audio_bytes: bytes) -> object:
        """Convert raw audio bytes (OGG/WAV) to 16kHz mono waveform tensor.

        Uses pydub + soundfile to avoid torchaudio.load() (torchaudio 2.10+ requires torchcodec).
        """
        import io
        import tempfile

        import soundfile as sf
        import torch
        import torchaudio
        from pydub import AudioSegment

        # Decode with pydub (ffmpeg-backed), normalize to 16kHz mono 16-bit WAV
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
            segment = segment.set_channels(1).set_frame_rate(16000).set_sample_width(2)
            segment.export(tmp.name, format="wav")
            tmp.flush()
            data, sr = sf.read(tmp.name, dtype="float32")

        # [samples] -> [1, samples], resample if pydub gave something else
        waveform = torch.from_numpy(data).unsqueeze(0) if data.ndim == 1 else torch.from_numpy(data).T.unsqueeze(0)
        if sr != 16000:
            waveform = torchaudio.transforms.Resample(sr, 16000)(waveform)
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        return waveform

    @modal.method()
    def get_embedding(self, audio_b64: str) -> dict:
        """Extract 192-dim speaker embedding from base64-encoded audio."""
        import base64

        import torch

        audio_bytes = base64.b64decode(audio_b64)
        waveform = self._audio_to_waveform(audio_bytes)

        with torch.no_grad():
            embedding = self.model(waveform)

        return {
            "embedding": embedding.squeeze().tolist(),
            "model_version": MODEL_VERSION,
        }


@app.function(image=image)
@modal.fastapi_endpoint(method="POST")
def process(request: dict) -> dict:
    """HTTP endpoint: receives {"audio_b64": "..."}, returns {"embedding": [...], "model_version": "..."}."""
    embedder = VoiceEmbedding()
    return embedder.get_embedding.remote(request["audio_b64"])


@app.local_entrypoint()
def main(audio_b64: str = "") -> None:
    """Dry-run: build image, load ECAPA2, run embedding.

    Pass --audio-b64 for custom audio, otherwise uses a fixture .ogg file.
    Usage: modal run modal_functions/voice_embedding.py
           modal run modal_functions/voice_embedding.py --audio-b64 "$(base64 -i your.ogg)"
    """
    if not audio_b64:
        import base64
        from pathlib import Path

        fixture = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "voice-samples" / "en-01-s1.ogg"
        if not fixture.exists():
            print(f"ERROR: fixture not found at {fixture}")
            print("Pass --audio-b64 manually or ensure test fixtures exist.")
            return
        audio_b64 = base64.b64encode(fixture.read_bytes()).decode("ascii")
        print(f"Using fixture: {fixture.name}")

    embedder = VoiceEmbedding()
    out = embedder.get_embedding.remote(audio_b64)
    print(f"Embedding dim: {len(out['embedding'])}")
    print(f"Model: {out['model_version']}")
