#!/bin/bash
set -e
APP_DIR="/home/deploy/apps/jarvis"
cd $APP_DIR

echo "=== Installing JARVIS v3 ==="

# Backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
echo "Backend installed."

# Frontend
cd frontend
npm install
npm run build
cd ..
echo "Frontend built."

echo ""
echo "=== Install complete ==="
echo "Now: copy your .env and frontend/.env.local to the server, then run deploy/start.sh"
