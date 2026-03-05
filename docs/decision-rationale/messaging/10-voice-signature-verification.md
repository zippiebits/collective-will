# Decision Rationale — messaging/10-voice-signature-verification.md

> **Corresponds to**: [`docs/agent-context/messaging/10-voice-signature-verification.md`](../../agent-context/messaging/10-voice-signature-verification.md)
>
> When a decision changes in either file, update the other.

---

## Decision Alignment

Voice verification implements the identity assurance layer referenced in shared context. It ensures that high-trust actions (submit, vote, endorse) require a biometrically verified session, not just account linkage. The design prioritizes accessibility (standard voice notes, no special apps), auditability (evidence-logged scores), and self-hosting (no third-party biometric APIs).

---

## Decision: Dual verification — embedding similarity + transcription match

**Why this is correct**

- Embedding-only is vulnerable to replay attacks (pre-recorded audio of the enrolled user)
- Transcription-only is vulnerable to voice impersonation (someone else reading the correct phrase)
- Dual check with randomized phrases defeats both attack vectors simultaneously
- The decision matrix allows high-confidence embeddings to pass with standard transcription, and moderate embeddings to pass only with strict transcription, balancing security with usability

**Risk**

- Environmental noise or poor microphone quality may degrade both scores simultaneously, causing legitimate users to fail
- Threshold values may need per-deployment tuning

**Guardrail**

- All thresholds are config-backed (embedding: per language-pair high + delta for moderate; transcription: EN/FA standard and strict) — tunable without code changes
- Evidence logs record both scores for every verification attempt, enabling threshold analysis
- Failed phrases are replaced (not repeated) to reduce frustration from phrase-specific pronunciation difficulty

**Verdict**: **Keep with guardrail**

---

## Decision: SpeechBrain ECAPA-TDNN + WhisperX, self-hosted CPU inference

**Why this is correct**

- Biometric data must not leave the deployment boundary — rules out cloud speech APIs
- ECAPA-TDNN produces compact 192-dim embeddings with strong speaker discrimination on VoxCeleb benchmarks
- WhisperX provides word-level timestamps and accurate multilingual transcription (Farsi + English)
- CPU inference is sufficient for per-user interactive verification (1-3s latency acceptable for voice note UX)
- Separate container isolates heavy ML dependencies from the main backend

**Risk**

- Model updates (SpeechBrain version, ECAPA weights) can change embedding space, invalidating enrolled embeddings
- WhisperX internal API may change between versions

**Guardrail**

- `voice-service/requirements.txt` pins exact versions (torch, speechbrain, whisperx)
- `voice_model_version` stored on each user record for compatibility tracking
- Re-enrollment mechanism planned for post-MVP model migration
- SpeechBrain model pre-downloaded at Docker build time to avoid cold-start delays
- Sync route handlers in voice-service prevent CPU-bound inference from blocking the event loop

**Verdict**: **Keep with guardrail**

---

## Decision: No pyannote.audio / speaker diarization

**Why this is correct**

- The system performs **speaker verification** (1:1 comparison against a stored enrollment), not speaker diarization (identifying who-spoke-when in a multi-speaker recording)
- Diarization adds complexity, GPU requirements, and latency without providing verification value
- Voice notes are single-speaker by nature — only one person records a Telegram voice message

**Risk**

- None identified — diarization solves a different problem

**Guardrail**

- No diarization library in dependencies; this decision is enforced by absence

**Verdict**: **Keep — not applicable to verification use case**

---

## Decision: Enroll immediately after account linking

**Why this is correct**

- Captures the voice signature at the moment of highest user attention and motivation
- Avoids a separate enrollment prompt that users might ignore
- Enrollment completes before the user can take any high-trust action, ensuring the voice gate is always active

**Risk**

- Users may not understand why they need to send voice messages right after linking
- Enrollment failure on first try may cause drop-off

**Guardrail**

- Clear i18n prompt explaining the purpose (FA + EN)
- Failed phrases are replaced with new ones (not repeated)
- Blocked users can retry the next day
- 3 phrases × 2 attempts each = reasonable effort before block

**Verdict**: **Keep with guardrail**

---

## Decision: 30-minute sliding session from last meaningful activity

**Why this is correct**

- Short enough to limit the damage window if a device is compromised
- Long enough that a normal voting/submission session completes without re-verification
- Session extends on successful vote and endorsement, so active users don't get interrupted

**Risk**

- Users who browse for >30 minutes without acting will need to re-verify
- Clock skew between containers could cause premature expiry

**Guardrail**

- `voice_session_duration_minutes` is config-backed (default 30)
- Session extension happens on vote and endorsement (the high-trust actions)
- All timestamps use UTC with timezone awareness

**Verdict**: **Keep with guardrail**

---

## Decision: Evidence logs contain scores only — no biometric data

**Why this is correct**

- The evidence log is append-only and partially public (`GET /analytics/evidence` strips PII)
- Storing embeddings, audio, or transcription text in evidence would leak biometric information
- Scores + phrase ID provide sufficient audit trail for dispute investigation

**Risk**

- Without stored audio, disputed verification outcomes cannot be independently reproduced

**Guardrail**

- Evidence payloads limited to: `{decision, embedding_similarity, transcription_score, phrase_id}` for verification, `{phrases_used, model_version}` for enrollment
- Encrypted audio retention (24h) planned for post-MVP dispute resolution
- Public evidence endpoint already strips user IDs from payloads

**Verdict**: **Keep with guardrail**

---

## Decision: Rate limiting voice verification (5 attempts / hour per user)

**Why this is correct**

- Prevents brute-force attempts to pass verification with different recordings
- Sliding window of 1 hour is generous enough for legitimate retries (noise, pronunciation errors)
- Per-user rate limiting prevents one attacker from degrading service for others

**Risk**

- Legitimate users with persistent audio quality issues may exhaust the limit

**Guardrail**

- `voice_verification_rate_limit_count` (5) and `voice_verification_rate_limit_window_seconds` (3600) are config-backed
- Clear user-facing message when rate-limited (FA + EN)
- In-process sliding-window counter via `check_voice_rate_limit` in `src/api/rate_limit.py`

**Verdict**: **Keep with guardrail**

---

## Decision: Externalized phrase pool (dynamic size, `secrets` for selection)

**Why this is correct**

- Large pools (200 EN, 200 FA purpose-written phrases) make phrase prediction difficult for replay attacks
- EN phrases use A1-B1 vocabulary only — designed for Farsi-speaking ESL users with clear, predictable pronunciation
- FA phrases use everyday conversational vocabulary — no literary, religious, or archaic language
- All phrases are 5-8 words, giving reliable transcription scoring while being comfortable to read
- `secrets.randbelow` ensures cryptographic randomness in phrase selection
- Excluded phrase tracking prevents repeating failed phrases during enrollment
- Phrases stored in `voice-phrases.json` (gitignored, deployed as secret) — not committed to the repo

**Risk**

- Phrase pools could be memorized over time if not refreshed
- Missing or corrupted phrases file prevents voice features from working

**Guardrail**

- `voice-phrases.json` deployed to VPS via `push-env.sh` alongside `.env.secrets`
- `voice-phrases.json.example` provides format reference
- `_load_phrases` validates structure (both locales, min 3 phrases, no empty strings) at startup
- `select_phrases` accepts `exclude_ids` to avoid repetition within a session
- Pool sizes are dynamic — code adapts to however many phrases the file contains
- Post-MVP: dynamic phrase generation could supplement the static pool

**Verdict**: **Keep with guardrail**
