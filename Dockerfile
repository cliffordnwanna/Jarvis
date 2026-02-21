# Use ollama tag (CUDA-free) to reduce image size for Railway free tier
# The :main image is 4.6GB, exceeding Railway's 4GB limit
# The :ollama tag is ~2GB and works with external APIs (OpenAI, etc.)
FROM ghcr.io/open-webui/open-webui:ollama

# Railway configuration
ENV PORT=8080
ENV HOST=0.0.0.0

# These will be set via Railway environment variables
ENV WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
ENV OPENAI_API_KEY=${OPENAI_API_KEY}

# Use OpenAI directly
ENV OPENAI_API_BASE_URL=${OPENAI_API_BASE_URL:-https://api.openai.com/v1}

# Enable signup for first user (becomes admin)
ENV ENABLE_SIGNUP=${ENABLE_SIGNUP:-true}

# Default models
ENV DEFAULT_MODELS=${DEFAULT_MODELS:-gpt-4o,gpt-4o-mini}

# CRITICAL: Disable ChromaDB to prevent disk space issues
# This is set via environment variables, but we provide defaults
ENV RAG_EMBEDDING_ENGINE=${RAG_EMBEDDING_ENGINE:-}
ENV ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION=${ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION:-false}

# Data persistence - Railway volume will be mounted via Railway dashboard
# No VOLUME keyword needed - Railway handles this automatically

EXPOSE 8080

CMD ["bash", "start.sh"]
