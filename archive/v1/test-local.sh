#!/bin/bash
# Quick local validation script
# Run this before deploying to Railway

set -e

echo "🔍 JARVIS Pre-Deployment Checks"
echo "================================"

# Check required files
echo "✓ Checking files..."
required_files=(".env" "docker-compose.yml" "litellm_config.yaml" "pipelines/merge_thinking.py")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing: $file"
        if [ "$file" == ".env" ]; then
            echo "   Run: cp .env.example .env (then add your API keys)"
        fi
        exit 1
    fi
done

# Check .env has keys
echo "✓ Checking .env..."
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo "⚠️  Warning: OPENAI_API_KEY not set in .env"
fi

# Start services
echo "✓ Starting services..."
docker compose up -d

# Wait for health checks
echo "✓ Waiting for services to be healthy..."
sleep 10

# Check LiteLLM
if curl -sf http://localhost:4000/health > /dev/null; then
    echo "✅ LiteLLM is healthy"
else
    echo "❌ LiteLLM health check failed"
    docker compose logs litellm
    exit 1
fi

# Check Open WebUI
if curl -sf http://localhost:8080/health > /dev/null; then
    echo "✅ Open WebUI is healthy"
else
    echo "❌ Open WebUI health check failed"
    docker compose logs open-webui
    exit 1
fi

echo ""
echo "🎉 All checks passed!"
echo "📱 Open: http://localhost:8080"
echo "🔑 Create your admin account and select 'jarvis-gpt'"
echo ""
echo "To stop: docker compose down"
