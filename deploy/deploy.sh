#!/usr/bin/env bash
set -euo pipefail

ENV="${1:?Usage: deploy.sh <production|staging> <image-tag>}"
IMAGE_TAG="${2:?Usage: deploy.sh <production|staging> <image-tag>}"

BASE_DIR="/opt/collective-will"
ENV_DIR="${BASE_DIR}/${ENV}"
DEPLOY_SRC="${BASE_DIR}/repo-deploy"
PUBLIC_ENV="${DEPLOY_SRC}/public.env.${ENV}"
SECRETS_ENV="${ENV_DIR}/.env.secrets"
LEGACY_ENV="${ENV_DIR}/.env"
RUNTIME_ENV="${ENV_DIR}/.env"
TMP_FILTERED_SECRETS="$(mktemp)"
TMP_RUNTIME_ENV="$(mktemp)"
PULL_RETRIES="${PULL_RETRIES:-3}"
PULL_RETRY_BACKOFF_SECONDS="${PULL_RETRY_BACKOFF_SECONDS:-15}"
HEALTH_RETRIES="${HEALTH_RETRIES:-12}"
HEALTH_RETRY_INTERVAL_SECONDS="${HEALTH_RETRY_INTERVAL_SECONDS:-3}"
MIN_DISK_AVAIL_GB="${MIN_DISK_AVAIL_GB:-2}"
MIN_MEM_AVAIL_MB="${MIN_MEM_AVAIL_MB:-256}"
REQUIRED_SERVICES=(postgres migrate backend scheduler web)

if [[ "$ENV" != "production" && "$ENV" != "staging" ]]; then
  echo "Error: environment must be 'production' or 'staging'" >&2
  exit 1
fi

if [[ "$ENV" == "production" ]]; then
  WEB_PORT=3000
  BACKEND_PORT=8000
  CADDY_HOST="collectivewill.org"
else
  WEB_PORT=3100
  BACKEND_PORT=8100
  CADDY_HOST="staging.collectivewill.org"
fi

check_ghcr_reachable() {
  local status
  status="$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 https://ghcr.io/v2/ || true)"
  case "$status" in
    200|401|403|405)
      echo "==> GHCR reachability check: HTTP ${status} (ok)"
      ;;
    *)
      echo "Error: GHCR reachability check failed (status=${status:-none})." >&2
      return 1
      ;;
  esac
}

check_resource_headroom() {
  local disk_avail_kb min_disk_kb mem_avail_kb min_mem_kb

  disk_avail_kb="$(df -Pk "${ENV_DIR}" | awk 'NR==2 {print $4}')"
  min_disk_kb=$((MIN_DISK_AVAIL_GB * 1024 * 1024))
  if [[ -n "$disk_avail_kb" && "$disk_avail_kb" -lt "$min_disk_kb" ]]; then
    echo "Error: low disk headroom (${disk_avail_kb}KB available; need >= ${min_disk_kb}KB)." >&2
    return 1
  fi

  mem_avail_kb="$(awk '/MemAvailable/ {print $2}' /proc/meminfo 2>/dev/null || true)"
  min_mem_kb=$((MIN_MEM_AVAIL_MB * 1024))
  if [[ -n "$mem_avail_kb" && "$mem_avail_kb" -lt "$min_mem_kb" ]]; then
    echo "Error: low memory headroom (${mem_avail_kb}KB available; need >= ${min_mem_kb}KB)." >&2
    return 1
  fi

  echo "==> Resource headroom check passed"
}

check_compose_services() {
  local services expected
  services="$(docker compose config --services)"
  echo "==> Compose services:"
  echo "${services}"

  for expected in "${REQUIRED_SERVICES[@]}"; do
    if ! grep -qx "${expected}" <<< "${services}"; then
      echo "Error: required compose service '${expected}' missing." >&2
      return 1
    fi
  done
}

check_url_status() {
  local url="$1"
  shift
  curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "$@" "${url}" || true
}

wait_for_healthy_url() {
  local label="$1"
  local url="$2"
  shift 2
  local status="" attempt=1

  while [[ "$attempt" -le "$HEALTH_RETRIES" ]]; do
    status="$(check_url_status "${url}" "$@")"
    if [[ "$status" =~ ^[23][0-9][0-9]$ ]]; then
      echo "==> Health check passed: ${label} (HTTP ${status})"
      return 0
    fi
    echo "==> Waiting for ${label} (attempt ${attempt}/${HEALTH_RETRIES}, status=${status:-none})"
    sleep "${HEALTH_RETRY_INTERVAL_SECONDS}"
    attempt=$((attempt + 1))
  done

  echo "Error: health check failed for ${label}; last status=${status:-none}" >&2
  return 1
}

pull_with_retry() {
  local attempt=1
  local sleep_for

  while [[ "$attempt" -le "$PULL_RETRIES" ]]; do
    echo "==> Pulling latest images (attempt ${attempt}/${PULL_RETRIES})..."
    if docker compose pull; then
      return 0
    fi

    if [[ "$attempt" -eq "$PULL_RETRIES" ]]; then
      echo "Error: docker compose pull failed after ${PULL_RETRIES} attempts." >&2
      return 1
    fi

    sleep_for=$((PULL_RETRY_BACKOFF_SECONDS * attempt))
    echo "==> Pull failed; retrying in ${sleep_for}s..."
    sleep "${sleep_for}"
    attempt=$((attempt + 1))
  done
}

cleanup() {
  rm -f "$TMP_FILTERED_SECRETS" "$TMP_RUNTIME_ENV"
}
trap cleanup EXIT

echo "==> Deploying ${ENV} with image tag: ${IMAGE_TAG}"

mkdir -p "${ENV_DIR}"

cp "${DEPLOY_SRC}/docker-compose.prod.yml" "${ENV_DIR}/docker-compose.yml"

if [[ ! -f "${PUBLIC_ENV}" ]]; then
  echo "Error: ${PUBLIC_ENV} not found. Ensure deploy/public.env.${ENV} is copied to the VPS." >&2
  exit 1
fi

SECRET_SOURCE=""
if [[ -f "${SECRETS_ENV}" ]]; then
  SECRET_SOURCE="${SECRETS_ENV}"
elif [[ -f "${LEGACY_ENV}" ]]; then
  SECRET_SOURCE="${LEGACY_ENV}"
  echo "==> Legacy mode: using ${LEGACY_ENV} as secret source"
  echo "==> Recommended: move secrets to ${SECRETS_ENV}"
else
  echo "Error: no secrets source found. Provide ${SECRETS_ENV} (preferred) or ${LEGACY_ENV}." >&2
  exit 1
fi

echo "==> Building merged runtime env at ${RUNTIME_ENV}"
awk -F= '
  FNR == NR {
    if ($0 ~ /^[[:space:]]*#/ || $0 ~ /^[[:space:]]*$/) next
    key = $1
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
    public_keys[key] = 1
    next
  }
  {
    if ($0 ~ /^[[:space:]]*#/ || $0 ~ /^[[:space:]]*$/) {
      print
      next
    }
    key = $1
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
    if (key in public_keys) {
      printf("Skipping duplicate key from secrets source: %s\n", key) > "/dev/stderr"
      next
    }
    print
  }
' "$PUBLIC_ENV" "$SECRET_SOURCE" > "$TMP_FILTERED_SECRETS"

{
  echo "# Autogenerated by deploy.sh (${ENV})"
  echo "# Public source: ${PUBLIC_ENV}"
  echo "# Secret source: ${SECRET_SOURCE}"
  echo
  cat "$PUBLIC_ENV"
  echo
  cat "$TMP_FILTERED_SECRETS"
} > "$TMP_RUNTIME_ENV"

install -m 600 "$TMP_RUNTIME_ENV" "$RUNTIME_ENV"

cd "${ENV_DIR}"

export IMAGE_TAG

echo "==> Preflight checks..."
check_resource_headroom
check_ghcr_reachable
check_compose_services

# ---------------------------------------------------------------------------
# Guard: tear down any stale stack whose project name differs from ours.
#
# The canonical project name is the directory basename (staging / production).
# A previous version of this script used COMPOSE_PROJECT_NAME="collective-will-<env>",
# which created a parallel stack that grabbed the same ports.  This block
# detects leftover containers from that (or any other) mismatched project
# name and removes them so the new deploy can bind its ports.
# ---------------------------------------------------------------------------
EXPECTED_PREFIX="${ENV}-"
STALE=$(docker ps -a --format '{{.Names}}' \
  | grep -i "${ENV}" \
  | grep -v "^${EXPECTED_PREFIX}" \
  || true)

if [[ -n "$STALE" ]]; then
  echo "==> Removing stale containers from a previous project name:"
  echo "$STALE"
  echo "$STALE" | xargs -r docker rm -f
fi

pull_with_retry

echo "==> Starting services..."
docker compose up -d --remove-orphans

echo "==> Cleaning up old images..."
docker image prune -f

echo "==> Verifying deployment..."
docker compose ps

RUNNING=$(docker compose ps --format '{{.Service}} {{.State}}' | grep -c "running" || true)
EXPECTED=$(docker compose config --services | wc -l | tr -d ' ')
MIGRATE_COUNT=$(docker compose config --services | grep -c "migrate" || true)
EXPECTED_RUNNING=$((EXPECTED - MIGRATE_COUNT))

if [[ "$RUNNING" -lt "$EXPECTED_RUNNING" ]]; then
  echo "WARNING: Only ${RUNNING}/${EXPECTED_RUNNING} services running. Check logs:" >&2
  docker compose ps
  docker compose logs --tail=20
  exit 1
fi

wait_for_healthy_url "web container on :${WEB_PORT}" "http://127.0.0.1:${WEB_PORT}/"
wait_for_healthy_url "backend openapi on :${BACKEND_PORT}" "http://127.0.0.1:${BACKEND_PORT}/openapi.json"

echo "==> Verifying Caddy routes..."
CADDY_HTTP_STATUS="$(check_url_status "http://${CADDY_HOST}/" --resolve "${CADDY_HOST}:80:127.0.0.1")"
CADDY_HTTPS_STATUS="$(check_url_status "https://${CADDY_HOST}/" --resolve "${CADDY_HOST}:443:127.0.0.1" -k)"
echo "==> Caddy HTTP (${CADDY_HOST}): ${CADDY_HTTP_STATUS}"
echo "==> Caddy HTTPS (${CADDY_HOST}): ${CADDY_HTTPS_STATUS}"

if [[ "$CADDY_HTTP_STATUS" == "000" || "$CADDY_HTTPS_STATUS" == "000" ]]; then
  echo "Error: Caddy is not responding on at least one route." >&2
  exit 1
fi

echo "==> Deploy complete for ${ENV} (${RUNNING}/${EXPECTED_RUNNING} services running)"
