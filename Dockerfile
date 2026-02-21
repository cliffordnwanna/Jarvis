# Open WebUI for Railway
# NOTE: Railway free tier has 4GB image limit - this will exceed it
# You need to either:
# 1. Upgrade Railway to Hobby plan ($5/month) - removes limit
# 2. Use Render instead (no image limit on free tier)

FROM ghcr.io/open-webui/open-webui:main

ENV PORT=8080
ENV HOST=0.0.0.0

# Disable Ollama (using OpenAI only)
ENV ENABLE_OLLAMA_API=false
ENV OLLAMA_BASE_URL=""

# Environment variables (set via Railway dashboard)
ENV WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
ENV OPENAI_API_KEY=${OPENAI_API_KEY}
ENV OPENAI_API_BASE_URL=${OPENAI_API_BASE_URL:-https://api.openai.com/v1}
ENV ENABLE_SIGNUP=${ENABLE_SIGNUP:-true}
ENV DEFAULT_MODELS=${DEFAULT_MODELS:-gpt-4o,gpt-4o-mini}

# Disable unnecessary features to save resources
ENV RAG_EMBEDDING_ENGINE=""
ENV ENABLE_IMAGE_GENERATION=false

EXPOSE 8080

CMD ["bash", "start.sh"]
