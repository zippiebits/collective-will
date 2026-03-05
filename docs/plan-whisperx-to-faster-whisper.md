# Plan: Switch voice-service from WhisperX to faster-whisper

This document is a step-by-step migration plan for replacing WhisperX with faster-whisper in the voice-service. It also answers whether to keep the voice-service as a separate Docker service or merge it into the backend.

---

## 1. Why switch

- **We only use transcription** — no diarization, no word-level timestamps. WhisperX pulls in pyannote-audio and torchcodec, which complicate Docker (e.g. no linux/arm64 wheel for torchcodec, forcing `platform: linux/amd64`).
- **faster-whisper** is the engine WhisperX uses for ASR; using it directly gives the same transcription with a lighter dependency set and no pyannote/torchcodec.
- **Same quality for our use case** — segment-level text for phrase scoring (EN overlap + Farsi subsequence/homophones).

---

## 2. API mapping (WhisperX → faster-whisper)

Researched from [faster-whisper README](https://github.com/SYSTRAN/faster-whisper) and PyPI.

| Current (WhisperX) | Target (faster-whisper) |
|-------------------|--------------------------|
| `import whisperx` | `from faster_whisper import WhisperModel` |
| `whisperx.load_model("small", device="cpu", compute_type="int8")` | `WhisperModel("small", device="cpu", compute_type="int8")` |
| `whisperx.load_audio(path)` then `model.transcribe(audio, language=...)` | `model.transcribe(path, language=...)` — **accepts file path directly**; no separate load_audio. |
| `result["segments"]` → list of `{"text": "..."}` | `segments, info = model.transcribe(...)` — **`segments` is a generator** of objects with `.start`, `.end`, `.text`. Must consume it (e.g. `list(segments)` or loop) for transcription to run. |
| Optional `language` (e.g. `"en"`, `"fa"`) | Supported: `model.transcribe(path, language="fa", beam_size=5)`. Use `language=None` for auto-detect. |
| N/A | `info.language`, `info.language_probability` for detected language. |

Important details:

- **File path**: `WhisperModel.transcribe(audio, ...)` accepts a path (str) or an audio segment. We already write to a temp WAV file in `transcribe_audio`, so we can pass `tmp.name` and remove the `whisperx.load_audio` step.
- **Generator**: `segments` must be iterated (e.g. `list(segments)`) before the transcription actually runs; otherwise no work is done.
- **Optional**: `vad_filter=True` (Silero VAD) can reduce hallucination; we can enable it for short voice notes. `beam_size=5` is the default in the README.

---

## 3. Step-by-step implementation plan

### Step 1: Update `voice-service/requirements.txt`

- Remove: `whisperx==3.8.1`.
- Add: `faster-whisper>=1.1.1` (or pin to a specific version, e.g. `1.2.1` from current PyPI).
- Keep: `torch`, `torchaudio`, `speechbrain`, `soundfile`, `pydub`, `fastapi`, `uvicorn`, `numpy`, `pydantic`, `pytest`. **Torch/torchaudio are required for SpeechBrain** (ECAPA embedding in `embed.py`), not for faster-whisper (which uses CTranslate2).
- Keep the PyTorch index (`--index-url https://download.pytorch.org/whl/cpu`) for SpeechBrain/torch/torchaudio.

### Step 2: Rewrite `voice-service/app/transcribe.py`

- Replace `import whisperx` with `from faster_whisper import WhisperModel`.
- **`load_model()`**:  
  - Replace `whisperx.load_model("small", device="cpu", compute_type="int8")` with  
  - `WhisperModel("small", device="cpu", compute_type="int8")`.  
  - Cache and return the same way (global `_model`, lazy load).
- **`transcribe_audio()`**:
  - Keep the temp file write of `wav_bytes` to a WAV file.
  - Instead of `whisperx.load_audio(tmp.name)` and `model.transcribe(audio, language=language)`:
    - Call `segments, info = model.transcribe(tmp.name, language=language or None, beam_size=5)` (and optionally `vad_filter=True`).
    - Consume the generator: `segments = list(segments)`.
    - Build full text: `raw = " ".join(s.text for s in segments).strip()`.
  - Keep the rest unchanged: `_strip_punctuation(raw)`, `word_overlap_score` / `_farsi_phrase_score`, return `(transcription, score)`.
- Update the module docstring from "WhisperX" to "faster-whisper" (or "faster-whisper transcription with word-overlap scoring").

### Step 3: Tests

- Run existing voice-service tests (e.g. `scripts/ci-voice.sh` or `PYTHONPATH=app pytest voice-service/tests/`).
- If there are tests that mock or depend on WhisperX, update them to the new API (e.g. mock `WhisperModel` and `transcribe` returning `(iter([segment_with_text]), info)`).
- Optionally run `scripts/test-voice-transcription.py` against a local voice-service (Docker or local venv) to confirm end-to-end transcription and scoring.

### Step 4: Docker and platform

- **Remove** `platform: linux/amd64` (and its comment) from the `voice-service` service in `docker-compose.yml` and from `deploy/docker-compose.prod.yml` if present. With faster-whisper we no longer depend on torchcodec, so the image can build and run on native arch (e.g. linux/arm64 on Apple Silicon).
- Rebuild the voice-service image and run `docker compose up voice-service` (or equivalent) and re-run the integration script to confirm.

### Step 5: Documentation and context

- Update any docs that mention WhisperX in the voice-service context to say "faster-whisper" (e.g. `docs/agent-context/messaging/10-voice-signature-verification.md`, `docs/decision-rationale/messaging/10-voice-signature-verification.md`, `CLAUDE.md`, `AGENTS.md` if they reference the stack).
- In decision/rationale docs, adjust the "WhisperX" bullet to "faster-whisper" and note that we use it for transcription only (no diarization); keep the guardrails about pinned versions and `voice_model_version`.
- Update `docs/agent-context/ACTIVE-action-plan.md` if it lists "WhisperX" as part of the voice-service stack.

### Step 6: CI

- Ensure `.github/workflows/ci.yml` (or any job that builds the voice-service image) does not rely on amd64; the build should succeed on the default runner arch.
- Run full CI (backend + web + voice-service build) and fix any remaining references or test failures.

---

## 4. Do we still need a separate Docker service, or should we merge?

**Recommendation: keep the voice-service as a separate Docker service.**

Reasons:

1. **Dependency isolation**  
   The main backend (`pyproject.toml`) uses a light stack (asyncpg, FastAPI, SQLAlchemy, numpy<2, etc.). The voice-service uses **torch and torchaudio for SpeechBrain** (ECAPA-TDNN embeddings in `embed.py`), plus faster-whisper (CTranslate2, no PyTorch) and audio tooling (pydub, soundfile). Merging would either:
   - Add all ML/audio deps to the backend image, increasing size and dependency conflict risk (e.g. numpy version constraints), or
   - Require a second Python environment inside the same container, which is more complex and brittle.

2. **CPU-bound inference**  
   Transcription and embedding extraction are CPU-bound. The voice-service runs them in **sync** handlers so that FastAPI runs them in a thread pool and does not block the event loop. If we merged into the backend, we would either:
   - Run the same sync code in the backend (still need a thread pool and the same ML stack in the backend image), or
   - Call out to a subprocess that runs the current voice-service code (effectively re-introducing a separate process, just not in its own container).

3. **Scaling and resource limits**  
   A separate service allows you to scale or resource-limit the voice workload independently (e.g. more memory for the voice-service, or running it only on nodes that have enough RAM for the models).

4. **Existing contract**  
   The backend already talks to the voice-service over HTTP (`VoiceServiceClient`, `voice_service_url`). Keeping this boundary avoids touching the backend’s dependency graph and keeps the API contract (e.g. `/process` request/response) unchanged.

**When merging might be considered**

- Single-binary or single-container deployment is a hard requirement and you are willing to accept a larger backend image and a single process running both API and ML.
- You move to a serverless/GPU runner that only runs the voice workload and you no longer need a long-lived voice container.

For the current design (self-hosted, CPU inference, clear separation of API and ML), **keeping the separate voice-service container is the right choice** even after switching to faster-whisper.

---

## 5. Summary checklist

- [ ] Step 1: requirements.txt — remove whisperx, add faster-whisper.
- [ ] Step 2: transcribe.py — WhisperModel, transcribe(path, ...), consume segments, same scoring logic.
- [ ] Step 3: Run voice-service tests and optional integration script.
- [ ] Step 4: Remove platform: linux/amd64 from compose files; rebuild and test Docker.
- [ ] Step 5: Update docs and agent-context (WhisperX → faster-whisper, keep guardrails).
- [ ] Step 6: CI and any remaining references.

No backend or API contract changes are required; only the voice-service implementation and its dependencies change.
