#!/usr/bin/env bash
# Auto-pull: verifica se houve push no repo e, se sim, atualiza a VM.
# Instalado como systemd timer (a cada 2 min) pelo deploy-gcp.sh.
set -euo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
COMPOSE_FILE="$REPO_DIR/infra/docker-compose.oracle.yml"
LOG_TAG="auto-pull"

cd "$REPO_DIR"

# Serializa execucoes: se outra instancia do auto-pull esta rodando
# (fetch/pull/up concorrentes causam "cannot lock ref ... but expected"),
# sai silenciosamente — o timer roda de novo em 2 min.
exec 9>"$REPO_DIR/.auto-pull.lock"
flock -n 9 || {
  echo "[$LOG_TAG] outra execucao em andamento, pulando."
  exit 0
}

# fetch rapido (sem merge). Refspec com '+' forca a atualizacao da ref
# remota mesmo que o valor esperado esteja defasado por um fetch concorrente.
FETCH_LOG="$(timeout 30 git fetch origin +main:refs/remotes/origin/main 2>&1)" || {
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