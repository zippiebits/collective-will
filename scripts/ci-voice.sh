#!/usr/bin/env bash
# Voice-service CI: install deps and run unit tests (Farsi scoring, no Docker/ML models).
# Run from repo root. Same pattern as ci-backend.sh / ci-web.sh.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VOICE_DIR="${ROOT_DIR}/voice-service"
cd "$VOICE_DIR"

if [[ ! -f requirements.txt ]]; then
  echo "Error: voice-service/requirements.txt not found" >&2
  exit 1
fi

echo "==> Installing voice-service dependencies..."
python -m pip install -q -r requirements.txt

echo "==> Running voice-service tests (PYTHONPATH=app)..."
PYTHONPATH=app python -m pytest tests/ -v --tb=short -q

echo "==> Voice CI passed."
