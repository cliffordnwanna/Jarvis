# Deploy JARVIS to Google Cloud Run - FREE for 90 Days

**$300 free credit + Always Free tier | No image size limit | Most reliable**

## Why Cloud Run?

- ✅ **$300 free credit** (lasts 90 days of heavy use)
- ✅ **No Docker image size limit** (Railway's main problem)
- ✅ **Always Free tier** after credits (2M requests/month)
- ✅ Auto-scales to zero (pay only when used)
- ✅ Most reliable of all free options
- ✅ After 90 days: ~$5-7/month for light use

---

## Quick Deploy (15 minutes)

### 1. Create Google Cloud Account (3 min)

1. Go to [cloud.google.com](https://cloud.google.com)
2. Click **Get started for free**
3. Sign in with Google account
4. Add credit card (required but **won't charge** without permission)
5. Get **$300 free credit** (90 days)

### 2. Install Google Cloud CLI (3 min)

**Windows (PowerShell as Admin):**
```powershell
(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")
& $env:Temp\GoogleCloudSDKInstaller.exe
```

**Verify:**
```powershell
gcloud --version
```

### 3. Login and Setup Project (2 min)

```powershell
# Login
gcloud auth login

# Create project
gcloud projects create jarvis-ai-PROJECT_ID --name="JARVIS AI"

# Set project
gcloud config set project jarvis-ai-PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

Replace `PROJECT_ID` with something unique (e.g., your name + random numbers).

### 4. Deploy Open WebUI (5 min)

```powershell
# Navigate to your repo
cd c:\Jarvis

# Deploy to Cloud Run
gcloud run deploy jarvis-openwebui \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 1 \
  --set-env-vars "OPENAI_API_KEY=YOUR_KEY_HERE,WEBUI_SECRET_KEY=YOUR_SECRET_HERE,ENABLE_SIGNUP=true,DEFAULT_MODELS=gpt-4o,gpt-4o-mini,ENABLE_OLLAMA_API=false"
```

**Replace:**
- `YOUR_KEY_HERE` with your OpenAI API key
- `YOUR_SECRET_HERE` with a random 32-char string

**Build takes 5-10 minutes** (Cloud Build handles the large image automatically)

### 5. Get Your URL (1 min)

After deployment completes:
```powershell
gcloud run services describe jarvis-openwebui --region us-central1 --format 'value(status.url)'
```

Your URL: `https://jarvis-openwebui-XXXXX-uc.a.run.app`

---

## Access JARVIS (5 minutes)

### 6. Open Your App

1. Open the URL from step 5
2. Click **Sign Up**
3. Create admin account
4. You're in!

### 7. Enable Features

#### Web Search
1. **Admin Panel** → **Settings** → **Web Search**
2. Toggle **ON**
3. Select **DDGS** (DuckDuckGo)
4. Click **Save**

#### Memories
1. **Settings** → **Features**
2. Find **Memories (Beta)**
3. Toggle **ON**
4. Click **Save**

#### Audio (Voice)
1. **Settings** → **Audio**
2. **STT Engine:** OpenAI
3. **STT Model:** whisper-1
4. **TTS Engine:** OpenAI
5. **TTS Model:** tts-1
6. **Voice:** nova
7. Click **Save**

### 8. Upload v3 Pipeline

1. **Settings** → **Pipelines**
2. Click **+ Add Pipeline**
3. Copy contents from `c:\Jarvis\pipelines\merge_thinking_orchestrator.py`
4. Paste into editor
5. Click **Save**
6. Enable pipeline (toggle ON)
7. Configure valves:
   ```
   monthly_budget_usd: 50
   max_context_tokens: 8000
   enable_orchestrator: true
   enable_cost_tracking: true
   ```
8. Click **Save**

---

## Cost Breakdown

### First 90 Days (FREE)
- $300 credit covers everything
- Estimated usage: ~$10-20/month
- **You'll use ~$30-60 of your $300 credit**

### After 90 Days

**Always Free Tier Includes:**
- 2M requests/month
- 360k vCPU-seconds/month
- 180k GiB-seconds/month

**If you exceed Always Free:**
- ~$0.00002400 per request
- ~$0.00001800 per vCPU-second
- ~$0.00000250 per GiB-second

**Estimated monthly cost for light use:**
- 10k requests/month: ~$0.24
- 50k vCPU-seconds: ~$0.90
- 100k GiB-seconds: ~$0.25
- **Total: ~$1-2/month**

**For moderate use:**
- 100k requests/month: ~$2.40
- 200k vCPU-seconds: ~$3.60
- 400k GiB-seconds: ~$1.00
- **Total: ~$5-7/month**

---

## Manage Your Deployment

### View Logs
```powershell
gcloud run services logs read jarvis-openwebui --region us-central1
```

### Update Environment Variables
```powershell
gcloud run services update jarvis-openwebui \
  --region us-central1 \
  --set-env-vars "NEW_VAR=value"
```

### Redeploy After Code Changes
```powershell
cd c:\Jarvis
git pull
gcloud run deploy jarvis-openwebui --source . --region us-central1
```

### Check Usage and Costs
```powershell
# View current costs
gcloud billing accounts list
gcloud billing projects describe jarvis-ai-PROJECT_ID

# Or visit: https://console.cloud.google.com/billing
```

### Scale Resources
```powershell
# Increase memory/CPU if needed
gcloud run services update jarvis-openwebui \
  --region us-central1 \
  --memory 4Gi \
  --cpu 4
```

### Delete Service (Stop Charges)
```powershell
gcloud run services delete jarvis-openwebui --region us-central1
```

---

## Troubleshooting

### Build Failed

**Check build logs:**
```powershell
gcloud builds list --limit 5
gcloud builds log BUILD_ID
```

**Common issues:**
- API not enabled: Run `gcloud services enable cloudbuild.googleapis.com`
- Insufficient permissions: Make sure you're project owner

### Service Not Responding

**Check service status:**
```powershell
gcloud run services describe jarvis-openwebui --region us-central1
```

**Check logs:**
```powershell
gcloud run services logs read jarvis-openwebui --region us-central1 --limit 50
```

### Out of Memory

**Increase memory:**
```powershell
gcloud run services update jarvis-openwebui \
  --region us-central1 \
  --memory 4Gi
```

### Cold Start Too Slow

**Keep 1 instance always running:**
```powershell
gcloud run services update jarvis-openwebui \
  --region us-central1 \
  --min-instances 1
```

**Note:** This increases costs (~$30-40/month) but eliminates cold starts.

---

## Mobile Access

### Add to Home Screen

**iPhone:**
1. Open Cloud Run URL in Safari
2. Tap Share → Add to Home Screen
3. Name it "JARVIS"

**Android:**
1. Open Cloud Run URL in Chrome
2. Menu → Add to Home Screen
3. Name it "JARVIS"

### Use with AirPods

1. Connect AirPods
2. Open JARVIS app
3. Tap 🎤 to speak
4. Enable auto-play in Settings → Audio
5. Responses play through AirPods

---

## Why Cloud Run is Best

| Feature | Cloud Run | Railway Free | Render Free | HF Spaces |
|---------|-----------|--------------|-------------|-----------|
| **Image size limit** | ✅ None | ❌ 4GB | ✅ None | ✅ None |
| **Free credit** | ✅ $300 | ❌ $5 | ❌ None | ✅ Forever |
| **RAM** | ✅ 2-4GB | 512MB | 512MB | 16GB |
| **Reliability** | ✅ Excellent | ⚠️ Good | ⚠️ Fair | ❌ Poor |
| **Cold start** | ~5s | N/A | ~30s | ~60s |
| **After free tier** | $5-7/mo | $5/mo | $7/mo | FREE |

**Cloud Run wins for:**
- No image size limit (Railway's killer)
- Generous free credit ($300)
- Production reliability
- Auto-scaling
- Always Free tier after credits

---

## Next Steps

1. **Create GCP account** → Get $300 credit
2. **Install gcloud CLI**
3. **Run deploy command** (one command!)
4. **Wait 5-10 minutes** for build
5. **Access your JARVIS** at the provided URL
6. **Test everything** (merge thinking, voice, web search)

**Total time: 15 minutes to fully working JARVIS**

---

## Alternative: AWS App Runner (Also FREE)

If you prefer AWS:

```bash
# Install AWS CLI
# Deploy to App Runner (similar to Cloud Run)
aws apprunner create-service \
  --service-name jarvis-openwebui \
  --source-configuration '{
    "CodeRepository": {
      "RepositoryUrl": "https://github.com/YOUR_USERNAME/Jarvis",
      "SourceCodeVersion": {"Type": "BRANCH", "Value": "main"}
    }
  }'
```

**AWS Free Tier:**
- 12 months free
- 2M requests/month
- Similar pricing to GCP after free tier

---

## Deployment Complete! 🎉

You now have:
- ✅ JARVIS on Google Cloud Run (reliable, fast)
- ✅ $300 free credit (90 days)
- ✅ No Docker image size issues
- ✅ Auto-scaling
- ✅ ~$5-7/month after credits (or stay on Always Free)

**Your JARVIS URL:** `https://jarvis-openwebui-XXXXX-uc.a.run.app`

Start deploying now!
