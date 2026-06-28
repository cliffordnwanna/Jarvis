# JARVIS v3 — Command Reference

## URLs

```
JARVIS live:        https://89.167.93.25.sslip.io
Vercel (frontend):  https://jarvis-eta-self.vercel.app
PM2 dashboard:      https://app.pm2.io
Backend health:     https://89.167.93.25.sslip.io/api/health
Backend API docs:   https://89.167.93.25.sslip.io/api/docs
GitHub repo:        https://github.com/cliffordnwanna/Jarvis
```

---

## Most common deploy sequence

### Backend-only change (Python files)
```powershell
# Local
cd "c:\Ecotronics Enterprise\Jarvis"
git add -A
git commit -m "your message"
git push origin main
```
```bash
# VPS
cd /home/deploy/apps/jarvis && git pull && pm2 restart jarvis-backend
```

### Frontend-only change (TypeScript/CSS/components)
```powershell
# Local
cd "c:\Ecotronics Enterprise\Jarvis"
git add -A
git commit -m "your message"
git push origin main
```
```bash
# VPS
cd /home/deploy/apps/jarvis && git pull
cd /home/deploy/apps/jarvis/frontend && npm run build && pm2 restart jarvis-frontend
```

### Both changed
```powershell
# Local
cd "c:\Ecotronics Enterprise\Jarvis"
git add -A
git commit -m "your message"
git push origin main
```
```bash
# VPS
cd /home/deploy/apps/jarvis && git pull && pm2 restart jarvis-backend
cd /home/deploy/apps/jarvis/frontend && npm run build && pm2 restart jarvis-frontend
```

### One-liner (backend only, from local machine)
```bash
ssh deploy@89.167.93.25 "cd /home/deploy/apps/jarvis && git pull && pm2 restart jarvis-backend"
```

---

## SSH access

```powershell
ssh deploy@89.167.93.25
```

---

## Upload env files (after fresh clone or if secrets change)

```powershell
scp "c:\Ecotronics Enterprise\Jarvis\.env" deploy@89.167.93.25:/home/deploy/apps/jarvis/.env
scp "c:\Ecotronics Enterprise\Jarvis\frontend\.env.local" deploy@89.167.93.25:/home/deploy/apps/jarvis/frontend/.env.local
```

---

## Status & logs

```bash
# Check all running processes
pm2 status

# Live log stream (Ctrl+C to exit)
pm2 logs

# Last N lines without streaming
pm2 logs jarvis-backend --lines 50 --nostream
pm2 logs jarvis-frontend --lines 50 --nostream

# Filter for errors only
pm2 logs jarvis-backend --lines 100 --nostream | grep -i "error\|exception\|traceback\|failed"

# Filter for specific features
pm2 logs jarvis-backend --lines 100 --nostream | grep -i "agent\|add_person\|nudge\|scheduler\|reminder\|context"

# Check which ports are listening
sudo ss -tlnp | grep -E ':80|:443|:3001|:8000'

# Test services directly (bypass Caddy)
curl -s http://127.0.0.1:8000/health
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3001
```

---

## Process management

```bash
# Restart
pm2 restart jarvis-backend
pm2 restart jarvis-frontend
pm2 restart all

# Stop
pm2 stop jarvis-backend
pm2 stop jarvis-frontend

# Delete (then re-start with full command below)
pm2 delete jarvis-backend
pm2 delete jarvis-frontend

# Persist process list across reboots
pm2 save

# Terminal dashboard
pm2 monit

# Reset restart counter
pm2 reset jarvis-backend
pm2 reset jarvis-frontend

# Clear log files
pm2 flush jarvis-backend
pm2 flush jarvis-frontend
```

---

## Full restart from scratch (after reboot or process death)

```bash
cd /home/deploy/apps/jarvis
source venv/bin/activate

pm2 delete jarvis-backend jarvis-frontend

pm2 start "uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 2" \
  --name jarvis-backend \
  --cwd /home/deploy/apps/jarvis

pm2 start "npm run start -- --port 3001 --hostname 127.0.0.1" \
  --name jarvis-frontend \
  --cwd /home/deploy/apps/jarvis/frontend

pm2 save
sudo systemctl restart caddy
```

---

## If VPS reboots

```bash
# PM2 auto-starts via systemd (pm2 save was run at setup)
# If it doesn't recover automatically:
ssh deploy@89.167.93.25
cd /home/deploy/apps/jarvis
source venv/bin/activate
bash deploy/start.sh
sudo systemctl restart caddy
```

---

## Python / pip (backend dependencies)

```bash
# Activate venv first
source /home/deploy/apps/jarvis/venv/bin/activate

# Install/update a package
pip install <package>

# Install all requirements
pip install -r /home/deploy/apps/jarvis/requirements.txt

# Check installed packages
pip list
```

---

## Node / npm (frontend dependencies)

```bash
cd /home/deploy/apps/jarvis/frontend

# Install dependencies
npm install

# Build for production
npm run build

# Run dev server (not for production)
npm run dev
```

---

## Caddy (reverse proxy)

```bash
# Restart / reload
sudo systemctl restart caddy
sudo caddy reload --config /etc/caddy/Caddyfile

# Check status
sudo systemctl status caddy --no-pager | tail -10

# View config
sudo cat /etc/caddy/Caddyfile

# View logs
sudo journalctl -u caddy --no-pager | tail -20
sudo tail -f /var/log/caddy/jarvis-access.log

# If Caddyfile is immutable (chattr locked)
sudo lsattr /etc/caddy/Caddyfile
sudo chattr -i /etc/caddy/Caddyfile
```

---

## Caddy config (for reference)

```
# /etc/caddy/Caddyfile
89.167.93.25.sslip.io {
    handle /api/* {
        uri strip_prefix /api
        reverse_proxy 127.0.0.1:8000
    }
    handle {
        reverse_proxy 127.0.0.1:3001
    }
}
```

Frontend runs on port **3001** (port 3000 is taken by upjobs).
Backend runs on port **8000**.

---

## Environment files

```bash
# Check they exist on VPS
ls -la /home/deploy/apps/jarvis/.env
ls -la /home/deploy/apps/jarvis/frontend/.env.local

# Safe preview (hides secret values)
grep -v "KEY\|SECRET\|PASSWORD\|TOKEN" /home/deploy/apps/jarvis/.env
```

Required backend `.env` keys:
```
OPENAI_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
DEFAULT_TIMEZONE=Africa/Lagos
```

Required frontend `.env.local` keys:
```
NEXT_PUBLIC_JARVIS_URL=https://89.167.93.25.sslip.io/api
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

---

## Fresh clone on new VPS (emergency)

```bash
git clone https://github.com/cliffordnwanna/Jarvis /home/deploy/apps/jarvis
cd /home/deploy/apps/jarvis

# Backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Upload env files from local machine first (see "Upload env files" above)

# Frontend
cd frontend
npm install
npm run build

# Start
cd ..
pm2 start "uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 2" \
  --name jarvis-backend --cwd /home/deploy/apps/jarvis
pm2 start "npm run start -- --port 3001 --hostname 127.0.0.1" \
  --name jarvis-frontend --cwd /home/deploy/apps/jarvis/frontend
pm2 save
sudo systemctl restart caddy
```

---

## Supabase SQL (run in Supabase SQL Editor)

```sql
-- Allow reminders without a linked person
ALTER TABLE public.relationship_events
  ALTER COLUMN person_id DROP NOT NULL;

-- Fix note source constraint if "chat_extraction" is blocked
ALTER TABLE public.relationship_notes
  DROP CONSTRAINT relationship_notes_source_check,
  ADD CONSTRAINT relationship_notes_source_check
    CHECK (source IN ('voice','text','chat_extraction','import','agent'));

-- Check world state cache
SELECT user_id, created_at, updated_at
FROM world_state
ORDER BY updated_at DESC
LIMIT 5;

-- Check recent nudges
SELECT nudge_type, message, priority, delivered_at
FROM nudge_history
ORDER BY delivered_at DESC
LIMIT 10;

-- Check upcoming reminders
SELECT title, scheduled_at, event_type, nudge_sent
FROM relationship_events
WHERE completed_at IS NULL
ORDER BY scheduled_at ASC
LIMIT 10;
```

---

## Debug common problems

### "502 Bad Gateway"
```bash
pm2 status                          # is jarvis-backend running?
curl -s http://127.0.0.1:8000/health  # does backend respond?
pm2 logs jarvis-backend --lines 30 --nostream  # check for crash
pm2 restart jarvis-backend
```

### Frontend shows blank / old version
```bash
cd /home/deploy/apps/jarvis/frontend && npm run build && pm2 restart jarvis-frontend
pm2 logs jarvis-frontend --lines 20 --nostream
```

### Time showing wrong (1 hour off)
The browser must send `timezone` in the sensor payload.
Check `frontend/lib/sensors.ts` — it must use:
```ts
timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
```
Then POST to `/context/update` to refresh world state.

### Agent says wrong date or calculates dates itself
World state cache may be stale. Open the app, tap ⌖ Sync in the header.
Or POST directly:
```bash
# From browser console on the live site:
# The sync button calls /context/update automatically
```

### Caddy not serving JARVIS (shows upjobs instead)
```bash
sudo cat /etc/caddy/Caddyfile   # verify it points to 3001 not 3000
sudo systemctl restart caddy
```

### PM2 not starting after reboot
```bash
pm2 startup    # re-register systemd hook
pm2 save       # save current process list
```
