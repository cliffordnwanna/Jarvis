#!/bin/bash
set -e
APP_DIR="/home/deploy/apps/jarvis"
cd $APP_DIR

echo "=== Starting JARVIS v3 ==="

source venv/bin/activate

# Stop any existing instances cleanly
pm2 delete jarvis-backend 2>/dev/null || true
pm2 delete jarvis-frontend 2>/dev/null || true

# Backend — localhost only, 2 workers
pm2 start "uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 2" \
  --name jarvis-backend \
  --cwd $APP_DIR

# Frontend — localhost only
pm2 start "npm run start -- --port 3000 --hostname 127.0.0.1" \
  --name jarvis-frontend \
  --cwd $APP_DIR/frontend

pm2 save
pm2 startup systemd -u deploy --hp /home/deploy

echo ""
echo "=== JARVIS is running ==="
pm2 status
echo ""
echo "Backend: http://127.0.0.1:8000 (internal only)"
echo "Frontend: http://127.0.0.1:3000 (internal only)"
echo "Public: https://89.167.93.25.sslip.io (via Caddy)"
