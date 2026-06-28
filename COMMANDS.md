# JARVIS v3 — Command Reference

## URLs

```
JARVIS live:     https://89.167.93.25.sslip.io
PM2 dashboard:   https://app.pm2.io
Backend health:  https://89.167.93.25.sslip.io/api/health
Backend docs:    https://89.167.93.25.sslip.io/api/docs
```

---

## Daily deploy (most common)

```bash
# From local PowerShell — push changes
cd "c:\Ecotronics Enterprise\Jarvis"
git add -A && git commit -m "your message" && git push origin main

# On VPS — pull and restart backend
cd /home/deploy/apps/jarvis && git pull && pm2 restart jarvis-backend

# If frontend changed too
cd /home/deploy/apps/jarvis/frontend && npm run build && pm2 restart jarvis-frontend
```

One-liner from local machine (backend only):
```bash
ssh deploy@89.167.93.25 "cd /home/deploy/apps/jarvis && git pull && pm2 restart jarvis-backend"
```

---

## SSH access

```powershell
ssh deploy@89.167.93.25
```

## Upload env files

```powershell
scp "c:\Ecotronics Enterprise\Jarvis\.env" deploy@89.167.93.25:/home/deploy/apps/jarvis/.env
scp "c:\Ecotronics Enterprise\Jarvis\frontend\.env" deploy@89.167.93.25:/home/deploy/apps/jarvis/frontend/.env.local
```

---

## Status & logs

```bash
# Check all processes
pm2 status

# Live log stream
pm2 logs

# Last N lines (no stream)
pm2 logs jarvis-backend --lines 50 --nostream
pm2 logs jarvis-frontend --lines 50 --nostream

# Filter for errors
pm2 logs jarvis-backend --lines 100 --nostream | grep -i "error\|exception\|failed"

# Filter for specific feature
pm2 logs jarvis-backend --lines 100 --nostream | grep -i "add_person\|agent\|nudge\|scheduler"

# Check ports
sudo ss -tlnp | grep -E ':80|:443|:3001|:8000'

# Test services directly
curl -s http://127.0.0.1:8000/health
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3001
```

---

## Process management

```bash
pm2 restart jarvis-backend
pm2 restart jarvis-frontend
pm2 restart all

pm2 stop jarvis-backend
pm2 stop jarvis-frontend

pm2 delete jarvis-backend
pm2 delete jarvis-frontend

pm2 save          # persist process list across reboots
pm2 monit         # terminal dashboard
pm2 reset jarvis-backend   # reset restart counter

pm2 flush jarvis-backend   # clear logs
pm2 flush jarvis-frontend
```

---

## Caddy

```bash
sudo systemctl restart caddy
sudo systemctl status caddy --no-pager | tail -5
sudo caddy reload --config /etc/caddy/Caddyfile
sudo cat /etc/caddy/Caddyfile
sudo journalctl -u caddy --no-pager | tail -20
sudo tail -f /var/log/caddy/jarvis-access.log

# If Caddyfile is immutable
sudo lsattr /etc/caddy/Caddyfile
sudo chattr -i /etc/caddy/Caddyfile
```

---

## Full restart from scratch

```bash
cd /home/deploy/apps/jarvis
source venv/bin/activate
pm2 delete jarvis-backend jarvis-frontend

pm2 start "uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 2" \
  --name jarvis-backend --cwd /home/deploy/apps/jarvis

pm2 start "npm run start -- --port 3001 --hostname 127.0.0.1" \
  --name jarvis-frontend --cwd /home/deploy/apps/jarvis/frontend

pm2 save
sudo systemctl restart caddy
```

---

## If VPS reboots

```bash
# PM2 auto-starts via systemd (already configured)
# If it doesn't, run:
ssh deploy@89.167.93.25
cd /home/deploy/apps/jarvis
bash deploy/start.sh
sudo systemctl restart caddy
```

---

## Environment files

```bash
# Check they exist
ls -la /home/deploy/apps/jarvis/.env
ls -la /home/deploy/apps/jarvis/frontend/.env.local

# Safe preview (hides secrets)
cat /home/deploy/apps/jarvis/.env | grep -v "KEY\|SECRET\|PASSWORD\|TOKEN"
```

---

## Supabase SQL (run in Supabase SQL Editor)

```sql
-- Allow reminders without a linked person
ALTER TABLE public.relationship_events ALTER COLUMN person_id DROP NOT NULL;

-- Add "agent" as allowed note source (if constraint blocks inserts)
ALTER TABLE public.relationship_notes
  DROP CONSTRAINT relationship_notes_source_check,
  ADD CONSTRAINT relationship_notes_source_check
    CHECK (source IN ('voice','text','chat_extraction','import','agent'));
```
