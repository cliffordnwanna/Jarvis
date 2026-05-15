#!/usr/bin/env bash
set -euo pipefail

# JARVIS v2 VPS deploy helper
#
# Assumptions:
# - This repo is cloned on the VPS
# - docker + docker compose are installed
# - You deploy with docker-compose.prod.yml

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_NAME="${PROJECT_NAME:-jarvis}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_BRANCH="${GIT_BRANCH:-main}"

HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/health}"
HEALTH_RETRIES="${HEALTH_RETRIES:-20}"
HEALTH_SLEEP_S="${HEALTH_SLEEP_S:-2}"

cd "$REPO_DIR"

echo "==> Repo: $REPO_DIR"
echo "==> Git: $GIT_REMOTE/$GIT_BRANCH"
echo "==> Compose: $COMPOSE_FILE (project=$PROJECT_NAME)"

echo "==> Pulling latest code..."
git fetch --prune "$GIT_REMOTE"
git pull --ff-only "$GIT_REMOTE" "$GIT_BRANCH"

echo "==> Building + starting containers..."
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --build --remove-orphans

echo "==> Containers:"
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" ps

if command -v curl >/dev/null 2>&1; then
  echo "==> Health check: $HEALTH_URL"
  for i in $(seq 1 "$HEALTH_RETRIES"); do
    if curl -fsS "$HEALTH_URL" >/dev/null; then
      echo "==> OK"
      exit 0
    fi
    sleep "$HEALTH_SLEEP_S"
  done
  echo "==> Health check failed after $HEALTH_RETRIES attempts."
  exit 1
else
  echo "==> curl not found; skipping health check."
fi

