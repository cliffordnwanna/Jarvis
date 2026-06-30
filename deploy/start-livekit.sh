#!/bin/bash
APP_DIR="/home/deploy/apps/jarvis"
cd $APP_DIR
source venv/bin/activate

pm2 start "python -m backend.livekit_agent start" \
  --name jarvis-voice \
  --cwd $APP_DIR

pm2 save
echo "JARVIS voice agent started"
