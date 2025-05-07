#!/usr/bin/env bash
# Rebuild and restart the backend container with new dependencies.
# Usage: ./scripts/rebuild_backend.sh

set -euo pipefail

ROOT_DIR="$( cd -- "$(dirname "$0")/.." >/dev/null 2>&1 ; pwd -P )"
cd "$ROOT_DIR"

if ! command -v docker &>/dev/null; then
  echo "[ERROR] Docker is not installed or not in PATH." >&2
  exit 1
fi

export OPENAI_MODEL=${OPENAI_MODEL:-gpt-4.1}

# Stop existing containers gracefully
printf "\n👉 Shutting down running containers...\n"
docker compose down --remove-orphans

# Build only the backend image (faster) and recreate container
printf "\n🚧 Building backend image (this may take a moment)...\n"
docker compose build backend

printf "\n🚀 Starting stack...\n"
docker compose up -d backend localstack

printf "\n✅ Backend rebuilt and running. Tail logs with:\n   docker compose logs -f backend\n" 