# Security Hardening (2025-03-02)

**Commit**: `78f5cd5`
**Scope**: Auth endpoints, webhook verification, token handling, HTTP headers, CORS

---

## Changes Applied

### Critical Fixes

1. **Telegram webhook signature verification** (`src/api/routes/webhooks.py`, `src/config.py`)
   - New config: `TELEGRAM_WEBHOOK_SECRET`
   - Verifies `X-Telegram-Bot-Api-Secret-Token` header via `hmac.compare_digest`
   - Operator must set the secret when calling Telegram's `setWebhook` API

2. **Token consumption race condition** (`src/db/verification_tokens.py`)
   - `consume_token()` now uses `SELECT ... FOR UPDATE` + `await session.flush()`
   - Prevents TOCTOU: two parallel requests can no longer both consume the same token

3. **Auth endpoint rate limiting** (`src/api/rate_limit.py` — new file)
   - In-process sliding-window counters per IP
   - `/auth/subscribe`: 5/min, `/auth/verify`: 10/min, `/auth/web-session`: 5/min
   - Disputes: 3/hour per user_id
   - For horizontal scaling, swap to Redis-backed counters

### High-Priority Fixes

4. **Security headers** (`deploy/Caddyfile`)
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Server` header stripped

5. **CORS tightening** (`src/api/main.py`)
   - `allow_methods`: `["GET", "POST", "OPTIONS"]` (was `["*"]`)
   - `allow_headers`: `["Content-Type", "Authorization"]` (was `["*"]`)

6. **IP spoofing prevention** (`src/api/rate_limit.py`)
   - `get_request_ip()` prefers `CF-Connecting-IP` (non-spoofable behind Cloudflare)
   - Falls back to `X-Forwarded-For` then `request.client.host`

7. **Generic auth error messages** (`src/api/routes/auth.py`)
   - Verify: `"Invalid or expired verification link"`
   - Web-session: `"Invalid or expired session code"`
   - Prevents account/token enumeration

### Medium-Priority Fixes

8. **Linking code entropy** (`src/handlers/identity.py`)
   - `secrets.token_urlsafe(16)` — 128 bits (was 64 bits)

9. **Timing side-channel** (`src/handlers/identity.py`)
   - Email comparison uses `hmac.compare_digest()` (was `!=`)

10. **Token removed from subscribe response** (`src/api/routes/auth.py`)
    - Magic link token is no longer returned in the API response
    - Token is delivered only via email

11. **Evidence endpoint validation** (`src/api/routes/analytics.py`)
    - `event_type` query param validated against `VALID_EVENT_TYPES` whitelist

12. **Dispute rate limiting** (`src/api/routes/user.py`)
    - 3 disputes per hour per user (prevents LLM cost abuse)

13. **Email cookie security** (`web/lib/user-session.ts`)
    - Added `Secure` flag

---

## Operator Actions Required

### Set Telegram Webhook Secret

Generate a secret and register it with Telegram:

```bash
# Generate secret
export TG_WEBHOOK_SECRET=$(openssl rand -hex 32)

# Set in env
echo "TELEGRAM_WEBHOOK_SECRET=$TG_WEBHOOK_SECRET" >> .env.secrets

# Re-register webhook with Telegram (include secret_token parameter)
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=https://staging.collectivewill.org/api/webhooks/telegram" \
  -d "secret_token=$TG_WEBHOOK_SECRET"
```

Until `TELEGRAM_WEBHOOK_SECRET` is set, the webhook accepts all requests (backward compatible).

---

## Addressed (2026-03)

- **Content-Security-Policy**: Added via `next.config.ts` `headers()` — `default-src 'self'`, `script-src 'self' 'unsafe-inline'` (required for Next.js hydration), `frame-src 'none'`, `object-src 'none'`, `base-uri 'self'`, `frame-ancestors 'none'`, `upgrade-insecure-requests`. No external script/font/connect origins allowed.
- **HttpOnly flag on email cookie**: Moved `cw_user_email` cookie from client-side `document.cookie` to server-side Next.js API route (`/api/user/set-email-cookie`) with `httpOnly: true`, `secure: true`, `sameSite: lax`.

## Remaining Considerations (Not Yet Addressed)

- **Evidence endpoint authentication**: Currently public by design for transparency; document threat model
- **Database SSL enforcement**: Only relevant for remote/production database connections
- **CSP nonce support**: Current policy uses `'unsafe-inline'` for scripts due to Next.js hydration. Consider adding nonce-based CSP via middleware for stricter protection.
