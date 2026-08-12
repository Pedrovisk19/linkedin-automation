#!/usr/bin/env bash
# Deploy da API (+ bot Discord gateway) em VM e2-micro do GCP (Always Free).
# Uso:  bash infra/deploy-gcp.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo "=== Deploy GCP e2-micro — API + Discord bot ==="

# ---- Swap (e2-micro tem 1GB RAM; build precisa de mais) ----------------------
if ! swapon --show | grep -q swapfile; then
  echo "[swap] criando 2GB de swap..."
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

# ---- Docker ------------------------------------------------------------------
if ! command -v docker &>/dev/null; then
  echo "[docker] instalando..."
  sudo apt-get update -qq
  sudo apt-get install -y -qq ca-certificates curl gnupg
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  . /etc/os-release
  DIST="debian"
  CODENAME="$VERSION_CODENAME"
  case "$CODENAME" in
    trixie) CODENAME="bookworm" ;;
  esac
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${DIST} ${CODENAME} stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
  sudo usermod -aG docker "$USER"
fi

# ---- .env --------------------------------------------------------------------
if [ ! -f .env ]; then
  echo "[env] .env nao encontrado — preenchendo interativamente..."
  cp .env.example .env

  read -rp "DATABASE_URL (Neon): " db_url
  read -rp "DISCORD_BOT_TOKEN: " discord_token
  read -rp "DISCORD_ALLOWED_CHANNEL_ID: " discord_channel
  read -rp "DISCORD_TENANT_ID (mesmo do NEWS_TENANT_ID): " discord_tenant
  read -rp "OPENAI_API_KEY: " openai_key
  read -rp "OPENAI_BASE_URL (vazio se OpenAI direto): " openai_base
  read -rp "OPENAI_CHAT_MODEL (ex: gpt-4o-mini): " openai_model

  jwt_secret=$(head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 40)

  sed -i \
    -e "s|^DATABASE_URL=.*|DATABASE_URL=${db_url}|" \
    -e "s|^JWT_SECRET=.*|JWT_SECRET=${jwt_secret}|" \
    -e "s|^DISCORD_BOT_TOKEN=.*|DISCORD_BOT_TOKEN=${discord_token}|" \
    -e "s|^DISCORD_ALLOWED_CHANNEL_ID=.*|DISCORD_ALLOWED_CHANNEL_ID=${discord_channel}|" \
    -e "s|^DISCORD_TENANT_ID=.*|DISCORD_TENANT_ID=${discord_tenant}|" \
    -e "s|^NEWS_TENANT_ID=.*|NEWS_TENANT_ID=${discord_tenant}|" \
    -e "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=${openai_key}|" \
    -e "s|^OPENAI_BASE_URL=.*|OPENAI_BASE_URL=${openai_base}|" \
    -e "s|^OPENAI_CHAT_MODEL=.*|OPENAI_CHAT_MODEL=${openai_model}|" \
    -e "s|^TELEGRAM_POLLING=.*|TELEGRAM_POLLING=false|" \
    .env

  echo "[env] .env preenchido. JWT_SECRET gerado automaticamente."
else
  echo "[env] .env ja existe — pulando."
fi

# ---- Build + up --------------------------------------------------------------
echo "[docker] build + start..."
docker compose -f infra/docker-compose.oracle.yml up -d --build

# ---- Health check ------------------------------------------------------------
echo "[check] aguardando API subir..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/healthz >/dev/null 2>&1; then
    echo "[check] API saudavel!"
    break
  fi
  sleep 2
  [ "$i" -eq 30 ] && { echo "[check] API nao respondeu em 60s"; docker compose -f infra/docker-compose.oracle.yml logs --tail 30; exit 1; }
done

# ---- systemd (auto-restart) --------------------------------------------------
echo "[systemd] configurando auto-restart..."
cat <<'UNIT' | sudo tee /etc/systemd/system/linkedin-api.service >/dev/null
[Unit]
Description=LinkedIn Automation API + Discord bot
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=PLACEHOLDER_REPO
ExecStart=/usr/bin/docker compose -f infra/docker-compose.oracle.yml up -d
ExecStop=/usr/bin/docker compose -f infra/docker-compose.oracle.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
UNIT

sudo sed -i "s|PLACEHOLDER_REPO|${REPO_DIR}|g" /etc/systemd/system/linkedin-api.service
sudo systemctl daemon-reload
sudo systemctl enable linkedin-api

echo ""
echo "=== Deploy concluido ==="
echo "  API:       http://$(curl -s http://checkip.amazonaws.com):8000/healthz"
echo "  Bot:       $(docker compose -f infra/docker-compose.oracle.yml logs --tail 5 2>&1 | grep -i 'discord\|bot\|gateway' | tail -1 || echo 'verifique logs')"
echo "  Logs:      docker compose -f infra/docker-compose.oracle.yml logs -f"
echo "  Restart:   docker compose -f infra/docker-compose.oracle.yml restart"