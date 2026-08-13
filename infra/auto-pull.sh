#!/usr/bin/env bash
# Auto-pull: verifica se houve push no repo e, se sim, atualiza a VM.
# Instalado como systemd timer (a cada 2 min) pelo deploy-gcp.sh.
set -euo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
COMPOSE_FILE="$REPO_DIR/infra/docker-compose.oracle.yml"
LOG_TAG="auto-pull"

cd "$REPO_DIR"

# fetch rapido (sem merge)
FETCH_LOG="$(timeout 30 git fetch origin main 2>&1)" || {
  echo "[$LOG_TAG] git fetch falhou:"
  echo "$FETCH_LOG"
  exit 0
}

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
  exit 0
fi

echo "[$LOG_TAG] mudanca detectada: $LOCAL -> $REMOTE"
echo "[$LOG_TAG] git pull..."
git pull --ff-only origin main

echo "[$LOG_TAG] docker compose up --build..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo "[$LOG_TAG] deploy automatico concluido."