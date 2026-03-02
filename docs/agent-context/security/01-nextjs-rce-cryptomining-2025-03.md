# Security Incident: Next.js RCE → Cryptomining (2025-03)

**Date**: 2025-03-02  
**Severity**: Critical (CVSS 10.0 RCE, exploited in production)  
**Status**: Remediated

---

## Summary

The staging web container (`ghcr.io/civil-whisper/collective-will-web`) was compromised via a **remote code execution (RCE) vulnerability** in Next.js React Server Components. An attacker exploited this to inject and run **XMRig cryptomining malware** inside the container. The miner consumed ~2 CPU cores and ~2.3GB RAM, causing Docker pulls to crawl (~0.14 MB/s vs normal ~5 MB/s) and deploy runs to hit the SSH timeout.

**Root cause**: Next.js 15.2.0 + React 19.0.0 were vulnerable to CVE-2025-66478 / GHSA-9qr9-h5gf-34mp (RCE in React flight protocol).

---

## Attack Chain

1. **Exploitation**: Attacker sends crafted HTTP request to the Next.js App Router (React Server Components protocol).
2. **RCE**: Vulnerability triggers unintended server-side code execution.
3. **Payload delivery**: Malicious code uses `wget` (available in Alpine base image) to download XMRig binaries.
4. **Execution**: Miner written to `/app/.next/` (vHN6YfrC, MnDW78UK, PM config); spawned as child of `next-server` ~9 minutes after container start.
5. **Impact**: CPU and memory exhaustion → slow Docker pulls → deploy timeouts; Monero mining to attacker-controlled pools (91.200.100.7, 45.196.97.119, 185.155.235.180, 91.208.184.203).

**Malware indicators**:
- Process names: `vHN6YfrC`, `MnDW78UK` (random strings)
- Config file: `/app/.next/PM` (XMRig config, worker ID `imeatingpoop`)
- 40+ zombie `sh` / `pkill` child processes

---

## Remediation Applied

| Action | Location |
|--------|----------|
| Upgraded Next.js | 15.2.0 → 15.5.12 |
| Upgraded React / React-DOM | 19.0.0 → 19.0.1 |
| Hardened web Dockerfile | Remove `wget`/`curl` from runtime; make `.next` read-only where possible |
| `npm audit fix` | Resolved minimatch, rollup dev-deps |
| Deploy timeout | Set to 10m so future anomalies fail fast and alert |

---

## Ongoing Guardrails

### Web Dependency Requirements

- **Next.js**: Keep at 15.5.12 or later. Do not downgrade below 15.2.6.
- **React / React-DOM**: Keep at 19.0.1 or later. Do not downgrade below 19.0.1.
- **npm audit**: Must show 0 vulnerabilities before merge/deploy. Run `npm audit` in `web/` as part of CI.
- **Web Dockerfile**: Do not add `wget`, `curl`, or other download tools to the runner stage. If a build step needs them, use a multi-stage build and ensure the final image is minimal.

### Deploy Timeout

- SSH `command_timeout` is **10 minutes**. This is deliberately tight so that:
  - Normal deploys (≈1–2 min) have ample headroom.
  - If the VPS is under heavy load (e.g. cryptominer, CPU exhaustion), the deploy fails quickly and the operator is alerted.

Do **not** increase the timeout to mask performance degradation. Investigate root cause instead.

### Post-Incident Operator Actions (One-Time)

After any confirmed RCE or container compromise:

1. **Rotate all VPS secrets**: `DB_PASSWORD`, `WEB_ACCESS_TOKEN_SECRET`, `TELEGRAM_BOT_TOKEN`, API keys, etc. The attacker had code execution and could have read env vars.
2. **Rotate GHCR PAT** on the VPS: Ensure `docker login ghcr.io` uses a token with `read:packages` scope. Replace if uncertain.
3. **Rotate GitHub Actions secrets** if they were ever passed into a compromised container.

---

## References

- [GHSA-9qr9-h5gf-34mp](https://github.com/advisories/GHSA-9qr9-h5gf-34mp) — Next.js React Flight Protocol RCE
- [CVE-2025-66478](https://nextjs.org/cve-2025-66478) — Next.js security advisory
- Fixed versions: Next.js 15.2.6+, 15.5.7+; React 19.0.1+
