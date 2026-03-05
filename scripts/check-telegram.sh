#!/usr/bin/env bash
# Verify Telegram bot token and show current webhook.
# Usage: ./scripts/check-telegram.sh [bot-token]
#   If token is omitted, uses TELEGRAM_BOT_TOKEN from .env.secrets or the environment.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_SECRETS="${REPO_ROOT}/.env.secrets"

if [[ -z "${1:-}" ]]; then
  if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]] && [[ -f "$ENV_SECRETS" ]]; then
    TELEGRAM_BOT_TOKEN=$(grep -E '^TELEGRAM_BOT_TOKEN=' "$ENV_SECRETS" 2>/dev/null | cut -d= -f2- | sed 's/^"//;s/"$//' | head -1)
  fi
fi

TOKEN="${1:-${TELEGRAM_BOT_TOKEN:-}}"
if [[ -z "$TOKEN" ]]; then
  echo "Usage: $0 [bot-token]" >&2
  echo "  Or set TELEGRAM_BOT_TOKEN in .env.secrets or the environment." >&2
  exit 1
fi

echo "Checking Telegram bot..."
ME=$(curl -sS "https://api.telegram.org/bot${TOKEN}/getMe")
if echo "$ME" | grep -q '"ok":true'; then
  USERNAME=$(echo "$ME" | sed -n 's/.*"username":"\([^"]*\)".*/\1/p')
  echo "  Token: valid (bot: @${USERNAME:-?})"
else
  echo "  Token: invalid or network error" >&2
  echo "$ME" >&2
  exit 1
fi

echo ""
INFO=$(curl -sS "https://api.telegram.org/bot${TOKEN}/getWebhookInfo")
if ! echo "$INFO" | grep -q '"ok":true'; then
  echo "getWebhookInfo failed: $INFO" >&2
  exit 1
fi
URL=$(echo "$INFO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('result',{}).get('url') or '')" 2>/dev/null || true)
if [[ -z "$URL" ]]; then
  echo "Webhook: not set — Telegram will not send updates. Run scripts/register-telegram-webhook.sh"
else
  echo "Webhook: $URL"
fi
