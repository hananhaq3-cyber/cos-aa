#!/usr/bin/env bash
# ─── COS-AA Free-Tier VM Setup ───
# Run on a fresh Ubuntu 22.04 ARM VM (e.g., Oracle Cloud always-free).
# Usage: bash scripts/setup-free-tier.sh
set -euo pipefail

echo "============================================"
echo "  COS-AA Free-Tier Setup"
echo "============================================"

# ─── 1. Install Docker ───
if ! command -v docker &>/dev/null; then
    echo "==> Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo "==> Docker installed. You may need to log out and back in for group changes."
else
    echo "==> Docker already installed."
fi

# ─── 2. Install Caddy ───
if ! command -v caddy &>/dev/null; then
    echo "==> Installing Caddy..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https curl
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg 2>/dev/null
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
    sudo apt-get update -qq
    sudo apt-get install -y -qq caddy
    echo "==> Caddy installed."
else
    echo "==> Caddy already installed."
fi

# ─── 3. Open Firewall Ports ───
echo "==> Opening firewall ports 80 and 443..."
sudo iptables -C INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -C INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
if command -v netfilter-persistent &>/dev/null; then
    sudo netfilter-persistent save
else
    sudo apt-get install -y -qq iptables-persistent
    sudo netfilter-persistent save
fi
echo "==> Firewall ports opened."

# ─── 4. Navigate to Project ───
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"
echo "==> Working directory: $PROJECT_DIR"

# ─── 5. Create .env if it doesn't exist ───
if [ ! -f .env ]; then
    cp .env.example .env
    # Generate secure secrets
    JWT_SECRET=$(openssl rand -hex 32)
    APP_SECRET=$(openssl rand -hex 32)
    sed -i "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET|" .env
    sed -i "s|APP_SECRET_KEY=.*|APP_SECRET_KEY=$APP_SECRET|" .env
    sed -i "s|APP_ENV=.*|APP_ENV=production|" .env
    echo ""
    echo "============================================"
    echo "  IMPORTANT: Edit .env before continuing!"
    echo "  At minimum, set:"
    echo "    - OPENAI_API_KEY"
    echo "    - CORS_DOMAIN (your domain name)"
    echo "  File: $PROJECT_DIR/.env"
    echo "============================================"
    echo ""
    echo "After editing .env, run:"
    echo "  docker compose -f docker-compose.free-tier.yml up -d --build"
    echo "  docker compose -f docker-compose.free-tier.yml exec api alembic upgrade head"
    echo "  sudo DOMAIN=your-domain.com caddy run --config infra/caddy/Caddyfile"
    exit 0
fi

# ─── 6. Build & Start ───
echo "==> Building and starting COS-AA..."
docker compose -f docker-compose.free-tier.yml up -d --build

echo "==> Waiting for services to be healthy..."
sleep 10

# ─── 7. Run Migrations ───
echo "==> Running database migrations..."
docker compose -f docker-compose.free-tier.yml exec -T api alembic upgrade head

# ─── 8. Configure Caddy ───
DOMAIN="${CORS_DOMAIN:-}"
if [ -z "$DOMAIN" ]; then
    DOMAIN=$(grep "^CORS_DOMAIN=" .env | cut -d= -f2 | tr -d '"' | tr -d "'")
fi

if [ -n "$DOMAIN" ] && [ "$DOMAIN" != "<YOUR_DOMAIN>" ]; then
    echo "==> Starting Caddy for domain: $DOMAIN"
    sudo DOMAIN="$DOMAIN" caddy stop 2>/dev/null || true
    sudo DOMAIN="$DOMAIN" caddy start --config "$PROJECT_DIR/infra/caddy/Caddyfile"
    echo "==> Caddy started with auto-HTTPS for $DOMAIN"
else
    echo "==> Skipping Caddy (no domain set). Access via http://<VM_IP>:3000 (frontend) and :8080 (API)"
fi

echo ""
echo "============================================"
echo "  COS-AA is running!"
echo "============================================"
echo "  Frontend:  http://localhost:3000"
echo "  API:       http://localhost:8080"
echo "  Health:    http://localhost:8080/health"
if [ -n "$DOMAIN" ] && [ "$DOMAIN" != "<YOUR_DOMAIN>" ]; then
    echo "  HTTPS:     https://$DOMAIN"
fi
echo ""
echo "  Logs:      docker compose -f docker-compose.free-tier.yml logs -f"
echo "  Status:    docker compose -f docker-compose.free-tier.yml ps"
echo "  Stop:      docker compose -f docker-compose.free-tier.yml down"
echo "============================================"
