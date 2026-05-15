# Deploy JARVIS to Oracle Cloud Always Free - Complete Guide

**$0 Forever | 24GB RAM | Always-On | Best Free Tier in 2026**

## Why Oracle Cloud Always Free?

- ✅ **100% FREE forever** (no credit card charges, ever)
- ✅ **24GB RAM + 4 ARM CPUs** (more than any other free tier)
- ✅ **Always-on** (no sleep, no cold starts)
- ✅ **200GB storage** included
- ✅ **No Docker image size limits**
- ✅ **Best performance** of all free options

**This is the most powerful free cloud tier available in 2026.**

---

## Quick Deploy (30 minutes)

### 1. Create Oracle Cloud Account (5 min)

1. Go to [oracle.com/cloud/free](https://www.oracle.com/cloud/free/)
2. Click **Start for Free**
3. Sign up with email
4. Verify email + phone number
5. Choose **home region:**
   - US: **Ashburn (us-ashburn-1)**
   - Europe: **Frankfurt (eu-frankfurt-1)**
   - Asia: **Tokyo (ap-tokyo-1)**
6. Complete survey → Land in Oracle Console

**No credit card required for Always Free tier!**

### 2. Create ARM VM Instance (8 min)

1. **Oracle Console** → **Compute** → **Instances** → **Create Instance**

2. **Name:** `jarvis-vm`

3. **Image and Shape:**
   - Click **Edit** next to Shape
   - **Shape:** VM.Standard.A1.Flex (Ampere ARM)
   - **OCPUs:** 4 (max for free tier)
   - **Memory:** 24 GB (max for free tier)
   - Look for **Always Free Eligible** badge ✅

4. **Image:**
   - Click **Change Image**
   - Select **Ubuntu 22.04** or **Ubuntu 24.04**
   - Click **Select Image**

5. **Networking:**
   - **VCN:** Create new VCN (default is fine)
   - **Subnet:** Public subnet
   - **Assign public IPv4 address:** YES ✅

6. **Add SSH Keys:**
   - Select **Generate a key pair for me**
   - Click **Save Private Key** → Download `jarvis-vm.key`
   - Click **Save Public Key** → Download (optional)

7. Click **Create**

**Wait 2-3 minutes** until status shows **Running** (green)

**Copy the Public IP address** (e.g., `129.213.XX.XX`)

### 3. Open Firewall Ports (5 min)

**In Oracle Console:**

1. **Compute** → **Instances** → Click `jarvis-vm`
2. **Subnet** → Click the subnet name
3. **Security Lists** → Click **Default Security List**
4. **Add Ingress Rules:**

**Rule 1: HTTP (port 80)**
- Source CIDR: `0.0.0.0/0`
- IP Protocol: TCP
- Destination Port Range: `80`
- Click **Add Ingress Rules**

**Rule 2: HTTPS (port 443)**
- Source CIDR: `0.0.0.0/0`
- IP Protocol: TCP
- Destination Port Range: `443`
- Click **Add Ingress Rules**

**Rule 3: Open WebUI (port 8080)**
- Source CIDR: `0.0.0.0/0`
- IP Protocol: TCP
- Destination Port Range: `8080`
- Click **Add Ingress Rules**

### 4. Connect to VM via SSH (3 min)

**On your Windows machine:**

Open PowerShell and run:

```powershell
# Move the key to a safe location
Move-Item "$env:USERPROFILE\Downloads\jarvis-vm.key" "$env:USERPROFILE\.ssh\jarvis-vm.key"

# Set proper permissions (Windows)
icacls "$env:USERPROFILE\.ssh\jarvis-vm.key" /inheritance:r
icacls "$env:USERPROFILE\.ssh\jarvis-vm.key" /grant:r "$env:USERNAME:R"

# Connect to VM (replace with your public IP)
ssh -i "$env:USERPROFILE\.ssh\jarvis-vm.key" ubuntu@YOUR_PUBLIC_IP
```

**Replace `YOUR_PUBLIC_IP`** with the IP from step 2.

**First time:** Type `yes` when asked about host authenticity.

You should now be connected to your Oracle VM!

### 5. Install Docker and Dependencies (5 min)

**On the VM (via SSH), run these commands:**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose git curl

# Add user to docker group
sudo usermod -aG docker $USER

# Apply group changes
newgrp docker

# Verify Docker works
docker --version
docker compose version
```

### 6. Clone Your Repo and Setup Environment (3 min)

```bash
# Clone your JARVIS repo
git clone https://github.com/YOUR_USERNAME/Jarvis.git
cd Jarvis

# Copy environment template
cp .env.example .env

# Edit .env file
nano .env
```

**In nano editor:**
1. Add your `OPENAI_API_KEY=sk-proj-...`
2. Add your `WEBUI_SECRET_KEY=random-32-chars`
3. Press `Ctrl+O` → Enter (save)
4. Press `Ctrl+X` (exit)

### 7. Deploy JARVIS (4 min)

```bash
# Start all services
docker compose up -d

# Wait 60-90 seconds for startup

# Check status
docker compose ps

# View logs
docker compose logs -f open-webui
```

Press `Ctrl+C` to stop viewing logs.

### 8. Open Ubuntu Firewall (2 min)

**Still on the VM:**

```bash
# Allow port 8080
sudo ufw allow 8080/tcp

# Allow HTTP/HTTPS (for future Caddy setup)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Verify
sudo ufw status
```

Type `y` when asked to enable firewall.

### 9. Access JARVIS (1 min)

**On your laptop, open browser:**

```
http://YOUR_PUBLIC_IP:8080
```

You should see the Open WebUI login screen!

---

## Complete Setup (10 minutes)

### 10. Create Admin Account

1. Click **Sign Up**
2. Enter name, email, password
3. Click **Create Account**
4. You're now admin!

### 11. Enable Features

#### Web Search
1. **Admin Panel** → **Settings** → **Web Search**
2. **Enable Web Search:** Toggle ON
3. **Search Engine:** Select **DDGS** (DuckDuckGo)
4. Click **Save**

#### Memories
1. **Settings** → **Features**
2. Find **Memories (Beta)**
3. Toggle **ON**
4. Click **Save**

#### Audio (Voice)
1. **Settings** → **Audio**
2. **Speech-to-Text:**
   - Engine: OpenAI
   - Model: whisper-1
3. **Text-to-Speech:**
   - Engine: OpenAI
   - Model: tts-1
   - Voice: nova
4. Click **Save**

### 12. Upload v3 Pipeline

1. **Settings** → **Pipelines**
2. Click **+ Add Pipeline**
3. **On your laptop**, open `c:\Jarvis\pipelines\merge_thinking_orchestrator.py`
4. Copy ALL contents (Ctrl+A, Ctrl+C)
5. Paste into pipeline editor
6. Click **Save**
7. Enable pipeline (toggle ON)
8. Configure valves:
   ```
   monthly_budget_usd: 50
   max_context_tokens: 8000
   enable_orchestrator: true
   enable_cost_tracking: true
   enable_pattern_learning: true
   ask_user_first: true
   ```
9. Click **Save**

---

## Test End-to-End (5 minutes)

### Test 1: Basic Chat
1. New chat → Select `gpt-4o`
2. Send: "Hello! What can you help me with?"
3. ✅ Should get response

### Test 2: Merge Thinking
1. New chat
2. Send: "How should I structure my week for maximum focus?"
3. ✅ Expected: "How would YOU handle this?"
4. Answer with your approach
5. ✅ JARVIS researches and merges perspectives

### Test 3: Web Search
1. New chat
2. Send: "What are the latest AI trends in 2026?"
3. ✅ Should see web search tool being used
4. ✅ Should get current information

### Test 4: Memory
1. Tell JARVIS: "Remember I'm working on upjobs.co"
2. New chat
3. Ask: "What project am I working on?"
4. ✅ Should recall upjobs.co

---

## Bonus: Add HTTPS with Caddy (Optional, 10 min)

### Get a Free Domain

**Option 1: Use DuckDNS (Free)**
1. Go to [duckdns.org](https://duckdns.org)
2. Sign in with GitHub
3. Create subdomain: `jarvis-yourname.duckdns.org`
4. Set IP to your Oracle VM public IP
5. Copy your token

**On VM:**
```bash
# Install DuckDNS updater
echo "echo url=\"https://www.duckdns.org/update?domains=jarvis-yourname&token=YOUR_TOKEN&ip=\" | curl -k -o ~/duckdns.log -K -" > ~/duckdns.sh
chmod +x ~/duckdns.sh
./duckdns.sh

# Add to crontab (update every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * ~/duckdns.sh >/dev/null 2>&1") | crontab -
```

### Add Caddy to docker-compose.yml

**On your laptop**, edit `c:\Jarvis\docker-compose.yml`:

Add this service:
```yaml
  caddy:
    image: caddy:2-alpine
    container_name: jarvis-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - open-webui
```

Add to volumes section:
```yaml
volumes:
  open-webui-data:
  caddy_data:
  caddy_config:
```

### Create Caddyfile

**On your laptop**, create `c:\Jarvis\Caddyfile`:

```
jarvis-yourname.duckdns.org {
    reverse_proxy open-webui:8080
}
```

### Deploy with HTTPS

```bash
# On your laptop - push changes
git add docker-compose.yml Caddyfile
git commit -m "Add Caddy for HTTPS"
git push origin main

# On VM - pull and restart
cd ~/Jarvis
git pull
docker compose down
docker compose up -d

# Wait 30 seconds for Caddy to get SSL cert
```

**Access via HTTPS:**
```
https://jarvis-yourname.duckdns.org
```

---

## Manage Your Deployment

### View Logs
```bash
# All services
docker compose logs -f

# Just Open WebUI
docker compose logs -f open-webui

# Just LiteLLM
docker compose logs -f litellm
```

### Restart Services
```bash
docker compose restart
```

### Update JARVIS
```bash
cd ~/Jarvis
git pull
docker compose down
docker compose up -d
```

### Check Resource Usage
```bash
# CPU and memory
docker stats

# Disk usage
df -h

# Docker disk usage
docker system df
```

### Backup Data
```bash
# Backup Open WebUI data
docker run --rm -v jarvis_open-webui-data:/data -v $(pwd):/backup ubuntu tar czf /backup/openwebui-backup.tar.gz /data

# Download to your laptop
scp -i ~/.ssh/jarvis-vm.key ubuntu@YOUR_PUBLIC_IP:~/Jarvis/openwebui-backup.tar.gz .
```

---

## Troubleshooting

### Can't Connect via SSH

**Check security list:**
- Oracle Console → Compute → Instances → Subnet → Security Lists
- Verify port 22 is open (should be by default)

**Check VM status:**
- Should show **Running** (green)
- Try rebooting: Actions → Reboot

### Can't Access Port 8080

**Check Oracle firewall:**
- Security Lists → Verify port 8080 ingress rule exists

**Check Ubuntu firewall:**
```bash
sudo ufw status
sudo ufw allow 8080/tcp
```

**Check Docker:**
```bash
docker compose ps
# Should show open-webui as "running"

docker compose logs open-webui
# Check for errors
```

### Services Won't Start

**Check logs:**
```bash
docker compose logs
```

**Restart everything:**
```bash
docker compose down
docker compose up -d
```

**Check disk space:**
```bash
df -h
# Should have plenty free (200GB total)
```

### Out of Memory

**Check usage:**
```bash
free -h
docker stats
```

**You have 24GB RAM** - this shouldn't happen unless you have many other services running.

---

## Cost Breakdown

### Oracle Cloud Always Free

**What you get forever (no charges):**
- ✅ 4 ARM CPUs (Ampere A1)
- ✅ 24 GB RAM
- ✅ 200 GB storage
- ✅ 10 TB outbound data transfer/month
- ✅ Always-on (no sleep)

**Cost:** **$0/month forever**

### OpenAI API (Separate)

- GPT-4o: ~$3-5/month with v3 orchestrator
- Whisper STT: ~$2-3/month
- TTS: ~$1-2/month
- **Total AI costs:** ~$6-10/month

**Grand total:** **~$6-10/month** (just OpenAI API, Oracle is free)

---

## Why Oracle Cloud is Best

| Feature | Oracle Free | GCP Free | Railway Free | Render Free |
|---------|-------------|----------|--------------|-------------|
| **RAM** | ✅ 24GB | 2GB | 512MB | 512MB |
| **CPUs** | ✅ 4 ARM | 1 | 0.5 | 0.5 |
| **Storage** | ✅ 200GB | 10GB | 1GB | 1GB |
| **Always-on** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Image limit** | ✅ None | ✅ None | ❌ 4GB | ✅ None |
| **Duration** | ✅ Forever | 90 days | N/A | Forever |
| **Setup time** | 30 min | 15 min | Failed | 10 min |

**Oracle wins for:**
- Most RAM (24GB vs 2GB max elsewhere)
- Most CPUs (4 ARM cores)
- Always-on (no cold starts)
- Forever free (not just trial)
- Best performance

---

## Mobile Access

### Add to Home Screen

**iPhone:**
1. Open `http://YOUR_PUBLIC_IP:8080` in Safari
2. Tap Share → Add to Home Screen
3. Name it "JARVIS"

**Android:**
1. Open `http://YOUR_PUBLIC_IP:8080` in Chrome
2. Menu → Add to Home Screen
3. Name it "JARVIS"

### Use with AirPods

1. Connect AirPods to phone
2. Open JARVIS app
3. Tap 🎤 to speak
4. Enable auto-play in Settings → Audio
5. Responses play through AirPods

---

## Next Steps

### Add More Models

Edit `.env` on VM to add Anthropic, OpenRouter, etc.:
```bash
nano ~/Jarvis/.env
```

Add:
```
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...
```

Restart:
```bash
docker compose restart litellm
```

### Add Local Ollama Models

You have 24GB RAM - you can run local models!

Add to `docker-compose.yml`:
```yaml
  ollama:
    image: ollama/ollama
    container_name: jarvis-ollama
    restart: unless-stopped
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
```

Pull models:
```bash
docker exec -it jarvis-ollama ollama pull llama3.1
docker exec -it jarvis-ollama ollama pull mistral
```

### Monitor Costs

Check OpenAI usage:
- Admin Panel → Analytics
- Track token consumption
- Validate 85% savings from v3 orchestrator

---

## Deployment Complete! 🎉

You now have:
- ✅ JARVIS on Oracle Cloud (24GB RAM, 4 CPUs)
- ✅ 100% free forever (no charges)
- ✅ Always-on (no cold starts)
- ✅ v3 Orchestrator with merge thinking
- ✅ Web search, memory, voice features
- ✅ Mobile access
- ✅ Best free cloud tier available

**Your JARVIS URL:** `http://YOUR_PUBLIC_IP:8080`

**Or with HTTPS:** `https://jarvis-yourname.duckdns.org`

**Start testing merge thinking now!**
