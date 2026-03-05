# Deploy Failures (2025-03)

**Date**: 2025-03-05  
**Scope**: GitHub Actions Deploy workflow; staging VPS  
**Status**: Documented for troubleshooting. No code change in this repo required for fixes described below.

---

## Summary

Two distinct failure modes were observed via `gh run list` and `gh run view --log-failed`:

| Run duration | Failure type | Cause |
|--------------|--------------|--------|
| **10m35s** | SSH command timeout | Image pull/extract exceeded 10-minute `command_timeout` |
| **1m25s** | Deploy script exit 1 | voice-service never "running" → only 4/5 services → script fails |

---

## 1. Timeout (10-minute SSH limit)

### What happened

- The "Deploy via SSH" step uses `command_timeout: 10m` (`.github/workflows/deploy.yml`).
- The step runs: Caddy apply (if needed) + `deploy.sh` (preflight, pull, up, verify, Caddy check).
- The run was still inside **`docker compose pull`** when 10 minutes elapsed — logs show repeated "Extracting …" for image layers (e.g. `ddf28d03bb63`).
- GitHub Actions then reported: `2026/03/05 19:09:13 Run Command Timeout` and the process exited with code 1.

### Root cause

- **Pull** (and layer extract) took longer than 10 minutes. Slow pull can be due to:
  - Network speed from VPS to GHCR (ghcr.io).
  - Large images (backend, web, voice).
  - VPS under load (e.g. CPU/disk) — in our case the host was verified clean (no mining).

### What to do

- **Confirm**: In the failed run, the last log line for "Deploy via SSH" should be "Extracting …" or "Pulling …".
- **Measure**: On the VPS run `cd /opt/collective-will/staging && time docker compose pull` to see actual pull time.
- **Option**: If pull is legitimately slow and VPS is healthy, consider increasing `command_timeout` (e.g. to 15m) in the workflow. Do not increase the timeout to mask degradation (see `docs/agent-context/security/01-nextjs-rce-cryptomining-2025-03.md`).

---

## 2. Script failure (4/5 services running)

### What happened

- `deploy.sh` requires a minimum number of **running** services: `EXPECTED_RUNNING = total_services - migrate_count` (migrate is one-shot).
- For staging that is 5: postgres, backend, scheduler, voice-service, web.
- **voice-service** never reaches state "running": it crashes on startup and stays in Restarting.
- So `RUNNING=4`, `EXPECTED_RUNNING=5` → the script prints "WARNING: Only 4/5 services running", dumps logs, and exits 1.

### voice-service crash

- **Error**: `ImportError: cannot load module more than once per process` when loading numpy (via torch) during app startup (`app/embed.py` → `import torch` → numpy).
- This is a known class of issue with Python/numpy in some Docker/embedding environments (native module loaded in a way that triggers double init).
- **Fix**: In the **voice-service** repo (not this app repo): dependency versions (numpy/torch), Dockerfile, or import strategy (e.g. avoid double import, or isolate heavy imports in a subprocess). No change required in the main collective-will application code.

### Postgres "database collective does not exist"

- Logs also showed: `FATAL: database "collective" does not exist` (repeated).
- Compose and app use database name **`collective_will`** (`POSTGRES_DB: collective_will` in deploy compose).
- So some process or connection string is using the wrong name **`collective`**.
- **Fix**: On the VPS (and in any env used by deploy), ensure every `DATABASE_URL`, `PGDATABASE`, or similar uses database name **`collective_will`**. Check `/opt/collective-will/staging/.env` and `.env.secrets` (and any other compose/env). This is configuration only; no app code change.

### What to do

1. **Fix voice-service** (long-term): Resolve numpy/torch import in the voice-service image so the container stays running; then deploy will see 5/5 services.
2. **Allow deploy without voice-service** (short-term): Change `deploy.sh` so that voice-service is not required for success (e.g. exclude it from `EXPECTED_RUNNING` or allow "restarting"). Deploy will succeed; voice features will be degraded until voice-service is fixed.
3. **Fix DB name**: Find and correct any config that uses database name `collective` so everything uses `collective_will`.

---

## References

- Deploy workflow: `.github/workflows/deploy.yml` (`command_timeout: 10m`, SSH step).
- Deploy script: `deploy/deploy.sh` (`REQUIRED_SERVICES`, `EXPECTED_RUNNING`, `pull_with_retry`).
- Security note on timeout: `docs/agent-context/security/01-nextjs-rce-cryptomining-2025-03.md` (do not increase timeout to mask performance degradation).
- Inspect failures: `gh run list --workflow=deploy.yml`, `gh run view <run_id> --log-failed`.
