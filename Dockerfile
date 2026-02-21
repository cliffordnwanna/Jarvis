# Multi-stage build to create minimal Open WebUI without Ollama
# Target: <4GB for Railway free tier

# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app
RUN apk add --no-cache git
RUN git clone --depth 1 https://github.com/open-webui/open-webui.git .
WORKDIR /app
RUN npm ci
RUN npm run build

# Stage 2: Build backend (Python only, no Ollama)
FROM python:3.11-slim AS backend-builder
WORKDIR /app
COPY --from=frontend-builder /app/backend /app/backend
COPY --from=frontend-builder /app/build /app/build
WORKDIR /app/backend
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Final minimal runtime
FROM python:3.11-slim
WORKDIR /app

# Install only essential runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy built application
COPY --from=backend-builder /app /app
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Railway configuration
ENV PORT=8080
ENV HOST=0.0.0.0

# Disable Ollama completely
ENV ENABLE_OLLAMA_API=false
ENV OLLAMA_BASE_URL=""

# Environment variables (set via Railway)
ENV WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
ENV OPENAI_API_KEY=${OPENAI_API_KEY}
ENV OPENAI_API_BASE_URL=${OPENAI_API_BASE_URL:-https://api.openai.com/v1}
ENV ENABLE_SIGNUP=${ENABLE_SIGNUP:-true}
ENV DEFAULT_MODELS=${DEFAULT_MODELS:-gpt-4o,gpt-4o-mini}

# Disable unnecessary features
ENV ENABLE_RAG_WEB_SEARCH=false
ENV RAG_EMBEDDING_ENGINE=""
ENV ENABLE_IMAGE_GENERATION=false

EXPOSE 8080

WORKDIR /app/backend
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
