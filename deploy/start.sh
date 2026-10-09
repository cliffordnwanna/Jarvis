#!/bin/bash
set -e
APP_DIR="/home/deploy/apps/jarvis"
cd $APP_DIR

echo "=== Starting JARVIS v3 ==="

source venv/bin/activate

# Stop any existing instances cleanly
pm2 delete jarvis-backend 2>/dev/null || true
pm2 delete jarvis-frontend 2>/dev/null || true
pm2 delete jarvis-voice 2>/dev/null || true

# Backend — localhost only, 2 workers
pm2 start "uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 2" \
  --name jarvis-backend \
  --cwd $APP_DIR

# Frontend — localhost only, port 3001 (3000 reserved for upjobs on this VPS)
pm2 start "npm run start -- --port 3001 --hostname 127.0.0.1" \
  --name jarvis-frontend \
  --cwd $APP_DIR/frontend

# Voice worker — LiveKit Agents SDK worker process. No HTTP port of its own;
# it registers with LiveKit Cloud over an outbound connection and receives
# dispatched jobs (one per voice session). Requires LIVEKIT_URL/API_KEY/
# API_SECRET/DEEPGRAM_API_KEY in .env -- if any are missing this process
# will fail to register and pm2 will show it as errored/restarting, which
# is the correct, visible failure mode (voice simply won't work, text still
# will). "start" (not "dev") is the non-interactive, no-hot-reload mode
# appropriate for a long-running production worker.
pm2 start "venv/bin/python -m backend.livekit_agent start" \
  --name jarvis-voice \
  --cwd $APP_DIR

pm2 save
pm2 startup systemd -u deploy --hp /home/deploy

echo ""
echo "=== JARVIS is running ==="
pm2 status
echo ""
echo "Backend: http://127.0.0.1:8000 (internal only)"
echo "Frontend: http://127.0.0.1:3001 (internal only)"
echo "Voice worker: jarvis-voice (registers outbound with LiveKit Cloud, no local port)"
echo "Public: https://89.167.93.25.sslip.io (via Caddy)"
echo ""
echo "Check voice worker registered successfully: pm2 logs jarvis-voice --lines 20 --nostream"
