# VPS deployment (backend via Docker Compose)

This repo’s backend deployment is **manual** by default:

- You update code with `git pull`
- You redeploy by rebuilding/restarting containers

To make this repeatable, use the included deploy script:

- `scripts/deploy.sh`

## 1) One-time VPS setup

### Install prerequisites

- Docker + Docker Compose plugin installed
- Your user can run docker without sudo (recommended):

```bash
sudo usermod -aG docker "$USER"
newgrp docker
docker ps
```

### Clone the repo

Example:

```bash
sudo mkdir -p /var/www
sudo chown -R "$USER":"$USER" /var/www
cd /var/www
git clone <YOUR_REPO_URL> jarvis
cd jarvis
```

### Create production environment file

Create `.env` in the repo root on the VPS (do **not** commit it).

Minimum:

```bash
OPENAI_API_KEY=...
GROQ_API_KEY=...
REDIS_URL=redis://redis:6379
DATABASE_URL=postgresql://jarvis:jarvis@postgres:5432/jarvis
```

If you’re using Supabase RAG, also set:

```bash
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
RAG_ENABLED=true
```

## 2) Deploy / update (every time)

From the repo root on the VPS:
cd /var/www/jarvis
nano deploy.sh

```bash
chmod +x scripts/deploy.sh

./deploy.sh


Edit your deploy script:

nano /var/www/jarvis/deploy.sh
✅ REPLACE WITH THIS (CLEAN VERSION)
#!/bin/bash

set -e

REPO="/var/www/jarvis"

echo "==> Repo: $REPO"
cd $REPO

echo "==> Current branch:"
git branch --show-current

echo "==> Pulling latest code..."
git pull origin main

echo "==> Rebuilding Docker stack..."
docker compose -p jarvis -f docker-compose.prod.yml up -d --build

echo "==> Deployment complete"
docker compose -p jarvis -f docker-compose.prod.yml ps
🔥 STEP 2 — MAKE IT EXECUTABLE
chmod +x /var/www/jarvis/deploy.sh
🚀 STEP 3 — RUN AGAIN
./deploy.sh


What it does:
- `git pull --ff-only origin main`
- `docker compose -f docker-compose.prod.yml up -d --build --remove-orphans`
- hits `http://127.0.0.1:8000/health` until it returns 200

## 3) Optional: override defaults

All of these are optional environment variables:

```bash
PROJECT_NAME=jarvis \
COMPOSE_FILE=docker-compose.prod.yml \
GIT_REMOTE=origin \
GIT_BRANCH=main \
HEALTH_URL=http://127.0.0.1:8000/health \
./scripts/deploy.sh
```

## 4) Troubleshooting

### View logs

```bash
docker compose -p jarvis -f docker-compose.prod.yml logs -n 200 --no-color backend
```

### Health endpoint fails

- Confirm the backend container is running:

```bash
docker compose -p jarvis -f docker-compose.prod.yml ps
```

- If it restarts/crashes, check logs and missing env vars.

