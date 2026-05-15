@echo off
REM Quick local validation script for Windows
REM Run this before deploying to Railway

echo.
echo 🔍 JARVIS Pre-Deployment Checks
echo ================================
echo.

REM Check required files
echo ✓ Checking files...
if not exist ".env" (
    echo ❌ Missing: .env
    echo    Run: copy .env.example .env ^(then add your API keys^)
    exit /b 1
)
if not exist "docker-compose.yml" (
    echo ❌ Missing: docker-compose.yml
    exit /b 1
)
if not exist "litellm_config.yaml" (
    echo ❌ Missing: litellm_config.yaml
    exit /b 1
)
if not exist "pipelines\merge_thinking.py" (
    echo ❌ Missing: pipelines\merge_thinking.py
    exit /b 1
)

REM Check .env has keys
echo ✓ Checking .env...
findstr /C:"OPENAI_API_KEY=sk-" .env >nul
if errorlevel 1 (
    echo ⚠️  Warning: OPENAI_API_KEY not set in .env
)

REM Start services
echo ✓ Starting services...
docker compose up -d

REM Wait for health checks
echo ✓ Waiting for services to be healthy...
timeout /t 10 /nobreak >nul

REM Check LiteLLM
curl -sf http://localhost:4000/health >nul 2>&1
if errorlevel 1 (
    echo ❌ LiteLLM health check failed
    docker compose logs litellm
    exit /b 1
) else (
    echo ✅ LiteLLM is healthy
)

REM Check Open WebUI
curl -sf http://localhost:8080/health >nul 2>&1
if errorlevel 1 (
    echo ❌ Open WebUI health check failed
    docker compose logs open-webui
    exit /b 1
) else (
    echo ✅ Open WebUI is healthy
)

echo.
echo 🎉 All checks passed!
echo 📱 Open: http://localhost:8080
echo 🔑 Create your admin account and select 'jarvis-gpt'
echo.
echo To stop: docker compose down
