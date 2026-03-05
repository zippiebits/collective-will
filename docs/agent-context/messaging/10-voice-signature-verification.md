# Task: Voice Signature Verification

## Depends on
- `messaging/01-channel-base-types` (`BaseChannel.download_file`, `UnifiedMessage.voice_file_id`)
- `messaging/08-message-commands` (voice gate in `route_message`, bot states)
- `messaging/09-telegram-test-channel` (`TelegramChannel.download_file`)
- `database/03-core-models` (User model: voice columns)
- `database/04-evidence-store` (`voice_enrolled`, `voice_verified` event types)
- `database/06-docker-compose` (voice-service container)

## Goal

Verify user identity via voice biometrics before allowing high-trust actions (submit, vote, endorse). Users read randomized phrases aloud; the system compares speaker embeddings (SpeechBrain ECAPA-TDNN) and transcription accuracy (WhisperX) against stored enrollment data. This dual-verification approach prevents both replay attacks and voice impersonation while remaining accessible over standard messaging voice notes.

## Files

### New modules

- `src/voice/__init__.py` — package marker
- `src/voice/client.py` — `VoiceServiceClient`: async HTTP client for voice-service `/process`
- `src/voice/audio.py` — `download_and_validate_audio`, `AudioValidationError`: duration checks + channel download
- `src/voice/phrases.py` — 100 phrases per language (FA/EN), `select_phrases`, `get_phrase` (uses `secrets` for selection)
- `src/voice/scoring.py` — `cosine_similarity`, `voice_decision` (decision matrix), `serialize_embedding`, `deserialize_embedding`, `average_embeddings`
- `src/voice/enrollment.py` — Multi-step enrollment state machine: `init_enrollment_state`, `start_enrollment`, `get_current_phrase`, `process_enrollment_audio`, `finalize_enrollment`
- `src/voice/verification.py` — Session verification: `pick_verification_phrase`, `verify_voice`

### Voice inference service (separate container)

- `voice-service/Dockerfile` — `python:3.11-slim` base, CPU-only PyTorch, ffmpeg, pre-downloads SpeechBrain model at build time
- `voice-service/requirements.txt` — Pinned dependencies (torch, speechbrain, whisperx, pydub, fastapi, uvicorn, pydantic, numpy)
- `voice-service/app/__init__.py` — package marker
- `voice-service/app/main.py` — FastAPI app: `/health` (GET) and `/process` (POST), sync handlers (thread-pool for CPU inference)
- `voice-service/app/schemas.py` — `ProcessRequest` (audio_b64, expected_phrase), `ProcessResponse` (transcription, transcription_score, embedding, model_version), `HealthResponse`
- `voice-service/app/embed.py` — SpeechBrain ECAPA-TDNN: `load_model`, `extract_embedding` → 192-dim float32 vector
- `voice-service/app/transcribe.py` — WhisperX: `load_model`, `transcribe_audio`, `word_overlap_score` → (text, score)
- `voice-service/app/audio.py` — `convert_to_wav16k`: pydub OGG Opus → 16kHz mono WAV

### Modified files

- `src/models/user.py` — Added columns: `voice_enrolled_at`, `voice_verified_at`, `voice_embedding` (LargeBinary), `voice_model_version`; properties: `is_voice_enrolled`, `is_voice_session_active`
- `src/handlers/commands.py` — Voice gate in `route_message`, enrollment/verification handlers, i18n strings (FA/EN), session extension on vote/endorse
- `src/channels/base.py` — Added abstract method `download_file(file_id: str) -> bytes`
- `src/channels/types.py` — Added `UnifiedMessage.voice_file_id` and `voice_duration` fields
- `src/channels/telegram.py` — Implemented `download_file`, voice message parsing in `parse_webhook`
- `src/channels/whatsapp.py` — `download_file` raises `NotImplementedError` (post-MVP)
- `src/db/evidence.py` — Added `voice_enrolled`, `voice_verified` to `VALID_EVENT_TYPES`
- `src/config.py` — Added all `voice_*` settings
- `src/api/rate_limit.py` — Added `check_voice_rate_limit` (sliding-window, 5/hour per user)
- `migrations/versions/004_voice_verification.py` — Adds voice columns to `users` table
- `docker-compose.yml` — Added `voice-service` with health check and `voice-models` volume
- `deploy/docker-compose.prod.yml` — Added `voice-service` with health check and `voice-models` volume
- `.github/workflows/ci.yml` — Added `build-voice` job

## Specification

### Configuration (`src/config.py`)

| Setting | Default | Purpose |
|---------|---------|---------|
| `voice_service_url` | `http://voice-service:8001` | Voice inference service base URL |
| `voice_service_timeout_seconds` | `30.0` | HTTP timeout for voice service calls |
| `voice_http_max_retries` | `2` | Retry count on voice service failures |
| `voice_embedding_similarity_high` | `0.50` | High-confidence embedding similarity threshold |
| `voice_embedding_similarity_moderate` | `0.35` | Moderate-confidence embedding similarity threshold |
| `voice_transcription_score_standard` | `0.70` | Standard transcription match threshold |
| `voice_transcription_score_strict` | `0.90` | Strict transcription match (compensates for moderate similarity) |
| `voice_enrollment_phrases_per_session` | `3` | Phrases required per enrollment |
| `voice_enrollment_max_phrase_failures` | `3` | Total phrase failures before blocking |
| `voice_enrollment_attempts_per_phrase` | `2` | Retries per individual phrase |
| `voice_session_duration_minutes` | `30` | Voice session TTL from last activity |
| `voice_verification_max_attempts` | `4` | Max verification attempts per session |
| `voice_verification_rate_limit_count` | `5` | Voice verification attempts per window |
| `voice_verification_rate_limit_window_seconds` | `3600` | Rate limit window (1 hour) |
| `voice_audio_min_duration_seconds` | `2` | Minimum audio length |
| `voice_audio_max_duration_seconds` | `15` | Maximum audio length |

### User Model Columns (`src/models/user.py`)

| Column | Type | Purpose |
|--------|------|---------|
| `voice_enrolled_at` | `DateTime(tz)`, nullable | Timestamp of completed enrollment |
| `voice_verified_at` | `DateTime(tz)`, nullable | Timestamp of last verification (session timer base) |
| `voice_embedding` | `LargeBinary`, nullable | Averaged 192-dim ECAPA-TDNN embedding (768 bytes, float32 packed) |
| `voice_model_version` | `String(128)`, nullable | Model identifier for embedding compatibility checks |

Computed properties:
- `is_voice_enrolled` → `voice_enrolled_at is not None and voice_embedding is not None`
- `is_voice_session_active` → `voice_verified_at` is within `voice_session_duration_minutes` of now

### Enrollment Flow (`src/voice/enrollment.py`)

1. **Trigger**: `route_message` calls `_start_voice_enrollment` after successful account linking, or when an unenrolled user sends a voice message
2. **State**: Stored in `user.bot_state_data` as dict: `{enrollment, step, phrase_ids, collected_embeddings, attempt, failures, failed_phrase_ids}`
3. **Bot state**: `user.bot_state = "enrolling_voice"`
4. **Per phrase**: User reads phrase → audio downloaded via `BaseChannel.download_file` → sent to voice-service → transcription score checked against `voice_transcription_score_standard`
5. **Accept**: Embedding stored in state as base64; advance to next phrase
6. **Retry**: Attempt counter incremented; if attempts ≥ `voice_enrollment_attempts_per_phrase`, phrase replaced with a new one
7. **Block**: If total failures ≥ `voice_enrollment_max_phrase_failures`, enrollment blocked
8. **Finalize**: After all phrases collected, `finalize_enrollment` averages embeddings, stores on user, sets `voice_enrolled_at` and `voice_verified_at`, logs `voice_enrolled` evidence event

### Verification Flow (`src/voice/verification.py`)

1. **Trigger**: `route_message` voice gate detects `is_voice_enrolled and not is_voice_session_active`
2. **Prompt**: Random phrase selected via `pick_verification_phrase`; stored in `user.bot_state_data["phrase_id"]`
3. **Bot state**: `user.bot_state = "awaiting_voice"`
4. **Check**: Audio processed by voice-service → `cosine_similarity` against stored embedding + `word_overlap_score` against expected phrase → `voice_decision` applies dual-threshold matrix
5. **Accept**: `voice_verified_at` updated, `voice_verified` evidence logged, user proceeds to main menu
6. **Reject**: New phrase prompted (re-verification)
7. **Rate limit**: `check_voice_rate_limit` (5 attempts/hour per user) checked before each attempt

### Decision Matrix (`src/voice/scoring.py: voice_decision`)

| Embedding Similarity | Transcription Score | Result |
|---------------------|---------------------|--------|
| ≥ `sim_high` (0.50) | ≥ `trans_standard` (0.70) | **accept** |
| ≥ `sim_moderate` (0.35) | ≥ `trans_strict` (0.90) | **accept** |
| Otherwise | — | **reject** |

### Voice Gate in `route_message`

After account lookup, before any action routing:

1. **Voice message** (`voice_file_id is not None`) → route to `_handle_voice_message`
2. **Not enrolled** → nudge to send voice message (`voice_enroll_needed`)
3. **Session expired** → start verification (`_start_voice_verification`) or nudge if already awaiting
4. **Session active** → proceed to normal action routing

Session extension: `voice_verified_at` updated on successful vote and endorsement.

### Voice Inference Service (`voice-service/`)

Separate FastAPI container running SpeechBrain ECAPA-TDNN and WhisperX on CPU.

- **Endpoints**: `GET /health` (model readiness), `POST /process` (embedding + transcription)
- **Input**: `ProcessRequest` with `audio_b64` (base64-encoded audio) and `expected_phrase`
- **Output**: `ProcessResponse` with `transcription`, `transcription_score` (word overlap), `embedding` (192 floats), `model_version`
- **Audio pipeline**: Base64 decode → pydub convert to 16kHz mono WAV → parallel embedding extraction + transcription
- **Threading**: Sync route handlers — FastAPI auto-runs in thread pool to avoid blocking the event loop
- **Docker**: `python:3.11-slim`, CPU-only PyTorch via `--index-url https://download.pytorch.org/whl/cpu`, SpeechBrain model pre-downloaded at build time, `voice-models` volume for caching
- **Health check**: `interval=30s, start_period=120s` (model loading takes ~60-90s)

### Evidence Logging

| Event | Payload (no biometric data) |
|-------|-----------------------------|
| `voice_enrolled` | `{phrases_used, model_version}` |
| `voice_verified` | `{decision, embedding_similarity, transcription_score, phrase_id}` |

### Channel Integration

- `BaseChannel.download_file(file_id: str) -> bytes` — abstract method for downloading platform files
- `UnifiedMessage.voice_file_id` / `voice_duration` — optional fields populated by channel adapters
- `TelegramChannel`: Parses voice messages from webhook, implements `download_file` via Bot API `getFile` + download
- `WhatsAppChannel`: `download_file` raises `NotImplementedError` (post-MVP)

## Constraints

- Embeddings stored as raw bytes (`LargeBinary`), not in core tables that get exported
- Evidence log entries contain only scores and phrase IDs — never raw audio, embeddings, or biometric data
- All voice settings config-backed via `src/config.py` — no magic numbers in business logic
- Voice service runs CPU-only; no GPU dependency
- Phrase selection uses `secrets.randbelow` for cryptographic randomness
- Rate limiting via in-process sliding-window counter (5 attempts/hour per user)
- No pyannote.audio or speaker diarization — verification is speaker-to-embedding comparison only

## Tests

| File | Coverage |
|------|----------|
| `tests/test_voice/test_scoring.py` | Cosine similarity, decision matrix, embedding serialization/deserialization, averaging |
| `tests/test_voice/test_phrases.py` | Phrase selection, exclusion, edge cases, `get_phrase` validation |
| `tests/test_voice/test_client.py` | `VoiceServiceClient`: success, retry on failure, health check |
| `tests/test_voice/test_enrollment.py` | State machine: init, phrase accept/retry/replace/block, finalize |
| `tests/test_voice/test_verification.py` | Accept, reject, audio error, service error, evidence logging |
| `tests/test_handlers/test_commands_voice.py` | Voice gate integration: enrollment start, verification flow, session extension, rate limiting |
| `tests/test_channels/test_telegram_voice.py` | Voice message parsing, file download |

### Migration

`migrations/versions/004_voice_verification.py` — adds `voice_enrolled_at`, `voice_verified_at`, `voice_embedding`, `voice_model_version` columns to `users` table.
