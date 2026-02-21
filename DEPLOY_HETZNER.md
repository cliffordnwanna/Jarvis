# Quick Deploy to Hetzner

## On Server

```bash
cd /root/projects/Jarvis
git pull
docker compose -f docker-compose.cloud.yml down
docker compose -f docker-compose.cloud.yml up -d
docker compose -f docker-compose.cloud.yml ps
```

## Access

```
http://YOUR_SERVER_IP:8080
```

## Notes

- Uses `docker-compose.cloud.yml` for cloud deployment (direct OpenAI, no LiteLLM)
- Uses `docker-compose.yml` for local development (with LiteLLM proxy)
