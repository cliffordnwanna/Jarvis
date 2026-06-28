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

echo ""
echo "=== Update complete ==="
pm2 status
