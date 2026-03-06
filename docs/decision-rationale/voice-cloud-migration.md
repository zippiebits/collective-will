# Decision Rationale: Voice Cloud Migration

**Date**: 2026-03
**Status**: Implemented

## Problem

Local voice-service Docker container (SpeechBrain ECAPA-TDNN + faster-whisper) was impractical:
- 60-120s per phrase on the staging VPS (2 vCPU, no AVX)
- MKLDNN/oneDNN crashes on no-AVX CPUs required workarounds
- ~2GB Docker image, slow to pull/build
- Separate service to maintain, deploy, and monitor

## Decision

Replace local voice-service with cloud APIs:
- **Transcription**: OpenAI GPT-4o-transcribe ($0.003/min, best multilingual accuracy)
- **Speaker embedding**: Modal serverless function running ECAPA2 ($30/month free tier, ~$0.05/month actual)
- **Scoring**: Moved into backend process (no separate service)

## Alternatives Considered

### Transcription
| Option | Cost | Accuracy | Why not |
|--------|------|----------|---------|
| OpenAI GPT-4o-transcribe | $0.003/min | Best (1.0 on test fixtures) | **Chosen** |
| Deepgram | $0.0043/min | Good | More expensive, less accurate on Farsi |
| Google Speech-to-Text | $0.006/min | Good | More expensive |
| AssemblyAI | $0.0065/min | Good | Most expensive |
| Keep faster-whisper local | Free | Marginal on weak VPS | 60-120s latency, MKLDNN issues |

### Speaker Embedding
| Option | Cost | Why not |
|--------|------|---------|
| Modal serverless (ECAPA2) | ~$0.05/month | **Chosen** — best model (0.34% EER), free tier covers it |
| Azure Speaker Recognition | Retired Sept 2025 | Dead |
| AWS Voice ID | EOL May 2026 | Dying |
| Replicate/RunPod | $0.10+/month | More expensive, worse DX |

### Embedding Model
| Model | EER | Dims | Why not |
|-------|-----|------|---------|
| ECAPA2 (Jenthe/ECAPA2) | 0.34% | 192 | **Chosen** — state of the art |
| ECAPA-TDNN (SpeechBrain) | ~1.0% | 192 | Previous model, lower accuracy |
| Resemblyzer | ~3-5% | 256 | Much lower accuracy |

## Key Design Decisions

### Unified thresholds (no per-locale split)
GPT-4o-transcribe produces perfect scores (1.0) for both English and Farsi, and ECAPA2 gives strong same-speaker similarity across languages (min 0.57 EN-FA). The per-locale threshold complexity is unnecessary:
- Embedding high: 0.45 (unified) with 0.12 guard above cross-speaker max (0.31)
- Embedding moderate: 0.38 with 0.07 guard above cross-speaker max
- Transcription standard: 0.65, strict: 0.75 (both languages)

### Enrollment audio storage
Raw OGG audio (~15-25KB per phrase) stored in `enrollment_audio` table for model portability. If we switch embedding models, we can re-compute embeddings from stored audio without re-enrolling users.

### Parallel API calls
Backend calls OpenAI (transcription) and Modal (embedding) simultaneously via `asyncio.gather`, achieving ~3-5s total latency vs sequential 6-10s.

### Model baked into Modal image
ECAPA2 weights are downloaded during Modal image build (`.run_commands(...)`) rather than at container startup, eliminating cold-start model downloads.

## Measured Results (12 fixture samples, 2 speakers, EN + FA)

- Transcription: 12/12 perfect (1.000)
- Same-speaker similarity: avg 0.6958, min 0.5729, max 0.8143
- Cross-speaker similarity: avg 0.1099, min -0.0380, max 0.3094
- Separation gap: 0.2635 (same-speaker min - cross-speaker max)
- Latency: ~3.7s including cold start

## Guardrails

- Old voice-service code remains in git history for rollback
- `enrollment_audio` table is additive (harmless if reverted)
- Modal dashboard monitors function health and cold starts
- OpenAI status page monitors transcription availability
- Graceful degradation: cloud API errors return `service_error`, users retry
