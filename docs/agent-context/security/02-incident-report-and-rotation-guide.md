# Security Incident Report & Rotation Guide

**Incident**: Next.js RCE → Cryptomining  
**Date**: 2025-03-02  
**Severity**: Critical  
**Status**: Remediated and verified clean (patched image deployed 2025-03-02)

---

## Part 1: What Happened

### Timeline

1. **Before the incident**: Staging was running `ghcr.io/civil-whisper/collective-will-web` with Next.js 15.2.0 and React 19.0.0. The web container is exposed to the internet via Caddy/Cloudflare.

2. **Exploitation**: An attacker sent a crafted HTTP request to the Next.js app. This request exploited CVE-2025-66478 (GHSA-9qr9-h5gf-34mp), a **Remote Code Execution** vulnerability in the React Server Components (RSC) protocol. The vulnerability allowed arbitrary code to run on the server.

3. **Payload delivery**: The malicious code ran inside the `next-server` process. It used `wget` (included in the Alpine base image) to download XMRig cryptomining binaries from the attacker's infrastructure.

4. **Execution**: ~9 minutes after each container start, the miner was written to `/app/.next/` and spawned as a child of the Next.js process. It consumed ~2 CPU cores and ~2.3GB RAM.

5. **Impact**: CPU and memory exhaustion caused Docker image pulls to slow from ~5 MB/s to ~0.14 MB/s. Deploy runs hit the SSH timeout. The miner sent Monero hashrate to attacker-controlled pools (91.200.100.7, 45.196.97.119, 185.155.235.180, 91.208.184.203).

---

## Part 2: How the Attacker Got Access

The attacker **did not** breach SSH, steal credentials, or exploit a dependency in our source code. Access was achieved purely by sending an HTTP request.

### Attack Path (Step by Step)

| Step | What Happened |
|------|---------------|
| 1 | Attacker discovers our staging app (staging.collectivewill.org) uses Next.js with App Router. |
| 2 | Attacker crafts a malicious HTTP request that targets the React Server Components (RSC) protocol—a binary protocol used for streaming server component payloads to the client. |
| 3 | The RSC deserializer in Next.js/React has a vulnerability: under certain crafted inputs, it executes unintended code paths that can lead to arbitrary code execution. |
| 4 | The request reaches our web container. Next.js processes it. The vulnerability is triggered. |
| 5 | Attacker's payload now runs with the same privileges as the Next.js process (user `nextjs`, uid 1001). |
| 6 | Payload runs `wget` to download XMRig binaries (vHN6YfrC, MnDW78UK) and config (PM) from attacker-controlled URLs. |
| 7 | Payload writes files to `/app/.next/` (writable by the nextjs user) and executes the miner. |
| 8 | Miner connects to mining pools and starts consuming CPU. |

### What the Attacker Could Access

- **Environment variables** of the web container. If a secret was in `env_file` or `environment` for the web service, the attacker could have read it.
- **Filesystem** inside the container (read/write in `/app`, `/tmp`).
- **Network** outbound from the container (mining pool connections).

### What the Attacker Did NOT Access

- Host (VPS) filesystem outside the container.
- Backend or scheduler containers (separate processes; no evidence of lateral movement).
- Database directly (the web container does not have `DATABASE_URL` in our compose; it talks to backend via HTTP).
- SSH keys or GitHub tokens stored on the VPS host (those live outside the container).

---

## Part 3: What We Did (Remediation)

| Action | Description |
|--------|-------------|
| Killed the miner | Restarted the web container to stop the malicious process. |
| Upgraded Next.js | 15.2.0 → 15.5.12 (patched for CVE-2025-66478). |
| Upgraded React | 19.0.0 → 19.0.1 (patched). |
| Hardened web Dockerfile | Removed `wget`/`curl` from the runtime image so future RCE cannot download binaries. Made `.next` read-only. |
| Fixed npm audit | Resolved all high/critical vulnerabilities in web dependencies. |
| Set deploy timeout to 10m | So slow/degraded deploys fail fast instead of masking problems. |
| Documented the incident | `docs/agent-context/security/01-nextjs-rce-cryptomining-2025-03.md` and this file. |

---

## Part 4: What We Need to Do (Operator Actions)

### 4.1 Is `.env.secrets` Compromised?

**Your local `.env.secrets` file** holds credentials for local development. It is **not** copied to the VPS by the deploy (deploy copies only `public.env.staging`, `public.env.production`, etc.).

**The VPS staging secrets** live at `/opt/collective-will/staging/.env` (or `.env.secrets` there). Those are built by `deploy.sh` from `public.env.*` + a secrets source on the VPS.

**Conclusion**: The secrets that were **running inside the web container on staging** are the ones the attacker could read. In `docker-compose.prod.yml`, the web service gets:

- `BACKEND_API_BASE_URL`
- `NEXTAUTH_URL`
- `NEXTAUTH_SECRET` (same as `WEB_ACCESS_TOKEN_SECRET`)
- `AUTH_TRUST_HOST`
- `OPS_CONSOLE_SHOW_IN_NAV`

So **`WEB_ACCESS_TOKEN_SECRET`** (and any other var passed to the web container) is **compromised** and must be rotated.

If your **local** `.env.secrets` uses the **same values** as staging (e.g. same `TELEGRAM_BOT_TOKEN` for a shared staging bot), then those values are compromised too. **Rotate any secret that was or is used on staging.**

### 4.2 Rotation Checklist

Use this checklist. Generate **new** values for each; never reuse old ones.

#### VPS Staging (at `/opt/collective-will/staging/.env` or `.env.secrets`)

**Important**: Rotating secrets does **not** delete or modify database data. All tables and records remain intact.

| Secret | How to Rotate | What Happens |
|--------|---------------|--------------|
| `DB_PASSWORD` | 1. Generate: `openssl rand -hex 32`<br>2. On VPS: `docker exec -it staging-postgres-1 psql -U collective -d collective_will -c "ALTER USER collective PASSWORD 'new_password';"`<br>3. Update VPS env with new password<br>4. Restart backend, scheduler | **Database unchanged.** Only the connection password changes. All data remains. |
| `WEB_ACCESS_TOKEN_SECRET` | 1. Generate: `openssl rand -hex 64`<br>2. Update VPS staging env<br>3. Restart web + backend | **Database unchanged.** Only web session signing key changes. All users must sign in again; no data loss. |
| `TELEGRAM_BOT_TOKEN` | 1. [@BotFather](https://t.me/BotFather) → `/revoke` or create new bot<br>2. Update VPS env<br>3. Restart backend | Bot gets new token; no DB impact. |
| `NEXTAUTH_SECRET` | Same as `WEB_ACCESS_TOKEN_SECRET` in our setup—rotate together | — |
| `RESEND_API_KEY` | Resend dashboard → Create new key, revoke old | — |
| `ANTHROPIC_API_KEY` | Anthropic console → Create new key, revoke old | You already rotated. |
| `OPENAI_API_KEY` | OpenAI dashboard → Create new key, revoke old | You already rotated. |
| `GOOGLE_API_KEY` | Google Cloud Console → Create new key or restrict | You already rotated. |

#### GHCR (Docker Registry) on VPS

| Action | Steps |
|--------|-------|
| New GitHub PAT for GHCR | 1. GitHub → Settings → Developer settings → Personal access tokens<br>2. Create token with `read:packages` scope<br>3. On VPS: `echo "NEW_TOKEN" | docker login ghcr.io -u USERNAME --password-stdin`<br>4. Revoke old token on GitHub |

#### GitHub Actions Secrets

| Secret | When to Rotate |
|--------|----------------|
| `VPS_SSH_KEY` | Only if you suspect it was exposed to a compromised container. The deploy SSH key is used by the runner to connect to the host—it is not passed into containers. Low risk. |
| `VPS_HOST`, `VPS_USER` | Not sensitive; no need to rotate. |
| `GITHUB_TOKEN` | Managed by GitHub; not in our control. |

#### Local `.env.secrets`

After rotating VPS secrets, update your **local** `.env.secrets` if you use the same values for local testing (e.g. same Telegram bot, same Resend key). Use the **new** rotated values so local and staging stay consistent where intended.

---

## Part 5: Summary

- **What happened**: Public exploit of a known Next.js RCE. No SSH breach, no stolen passwords.
- **How they got in**: One HTTP request to the vulnerable RSC endpoint.
- **What we fixed**: Patched Next.js/React, hardened the image, tightened deploy.
- **What you must do**: Rotate all secrets that were in the web container env, rotate GHCR PAT on the VPS, deploy the patched image, and update local `.env.secrets` where it shares values with staging.
