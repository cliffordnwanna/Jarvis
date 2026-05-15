# Deploy JARVIS to Render (Easier Alternative)

Render is simpler than Railway and has better free tier limits.

## Why Render is Easier

- ✅ 512MB RAM (same as Railway)
- ✅ **1GB disk** (vs Railway's 500MB)
- ✅ Auto-detects Dockerfiles
- ✅ No volume configuration needed
- ✅ Simpler environment variable setup

## Quick Deploy (10 minutes)

### 1. Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Authorize Render to access your repos

### 2. Deploy LiteLLM Service

1. **Dashboard → New → Web Service**
2. **Connect repository:** Select `Jarvis`
3. **Settings:**
   - **Name:** `jarvis-litellm`
   - **Region:** Oregon (US West)
   - **Branch:** `main`
   - **Root Directory:** (leave empty)
   - **Runtime:** Docker
   - **Dockerfile Path:** `Dockerfile.litellm`
   - **Instance Type:** Free
4. **Environment Variables:**
   - Click **Add Environment Variable**
   - `OPENAI_API_KEY` = `sk-proj-...`
   - `PORT` = `4000`
5. **Create Web Service**
6. **Wait 3-5 minutes** for deployment
7. **Copy the internal URL** (e.g., `jarvis-litellm.onrender.com`)

### 3. Deploy Open WebUI Service

1. **Dashboard → New → Web Service**
2. **Connect repository:** Select `Jarvis` again
3. **Settings:**
   - **Name:** `jarvis-openwebui`
   - **Region:** Oregon (US West)
   - **Branch:** `main`
   - **Root Directory:** (leave empty)
   - **Runtime:** Docker
   - **Dockerfile Path:** `Dockerfile.openwebui`
   - **Instance Type:** Free
4. **Environment Variables:**
   - `OPENAI_API_BASE_URL` = `https://jarvis-litellm.onrender.com/v1`
   - `OPENAI_API_KEY` = `sk-anything`
   - `WEBUI_SECRET_KEY` = `[generate 32-char random string]`
   - `ENABLE_SIGNUP` = `true`
   - `DEFAULT_MODELS` = `jarvis-gpt`
   - `PORT` = `8080`
5. **Create Web Service**
6. **Wait 5-7 minutes** for deployment

### 4. Access JARVIS

1. Render will give you a public URL: `https://jarvis-openwebui.onrender.com`
2. Open it in browser
3. Create your admin account
4. Start chatting!

## Limitations of Free Tier

- **Spins down after 15 minutes of inactivity** (cold start = 30-60 seconds)
- **750 hours/month** (enough for personal use)
- **1GB disk** (enough for basic usage, no large document uploads)

## Upgrade to Paid ($7/month per service)

- Always on (no cold starts)
- 2GB RAM
- 10GB disk
- Custom domains

---

## Next Steps

Follow the same pipeline upload and configuration steps from `DEPLOY_V3.md` starting at **Step 6**.
