#!/bin/bash
set -e
APP_DIR="/home/deploy/apps/jarvis"
cd $APP_DIR

echo "=== Updating JARVIS v3 ==="
echo "Time: $(date)"

git pull origin main

source venv/bin/activate
pip install -r backend/requirements.txt --quiet

cd frontend
npm install --quiet
npm run build
cd ..

pm2 restart jarvis-backend
pm2 restart jarvis-frontend
pm2 restart jarvis-voice 2>/dev/null || echo "jarvis-voice not running yet -- run deploy/start.sh once to add it"

echo ""
echo "=== Update complete ==="
pm2 status
echo ""
echo "Check voice worker: pm2 logs jarvis-voice --lines 20 --nostream"
