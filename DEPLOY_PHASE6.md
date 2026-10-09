# Deploying Phase 6 (Voice) to the VPS

This is a one-time runbook for pushing everything built this session to
production. Follow it in order, top to bottom, on the exact machine each
step says (your machine vs the VPS). Each step says what to run and what
success looks like — stop and check back with Claude if a step's output
doesn't match.

**What's new since the last deploy:**
- LiveKit voice agent (full Phase 6 voice pipeline)
- Tavily web search, TomTom maps (now fully working, both were broken/
  missing keys before)
- Unified tool list (text and voice now share one `ALL_TOOLS` list) and
  an auto-generated system-prompt tool inventory
- Server-side UUID/user-isolation enforcement on every tool (previously
  only voice had this; text trusted the LLM's own `user_id` argument)
- A first-time-user onboarding conversation flow
- PWA install fixes (real icons, registered service worker)
- `TOOLS.md` — reference doc for adding new tools correctly

**Important — shared database warning:** your local `.env` and the VPS's
`.env` point at the SAME Supabase project (`bvvqgcqeruefbykytrtx`). This is
not a separate dev database — anything done locally (including the memory
wipe already run this session, clearing `memory_files`/`relationship_notes`/
`people` for your account) already affects what the deployed app sees too,
immediately, with no extra step. Keep this in mind before running any
destructive command against this database from either side in the future.

---

## 0. Before you start

Confirm from your own machine (not the VPS) that these all still work
locally — if anything's broken locally, fix it before pushing to
production:
- Backend starts cleanly (`python -m backend.run_dev`)
- Voice worker registers (`python -m backend.livekit_agent dev`, look for
  "registered worker" in the log)
- Frontend builds (`cd frontend && npm run build`)

## 1. Commit and push your local changes

```bash
cd "C:\Users\Clifford.nwanna\Dev\Jarvis"
git status
git add backend/ TOOLS.md deploy/
git commit -m "Add Phase 6 voice (LiveKit Agents SDK), unify tool list across text/voice, fix tool bugs found in audit"
git push origin main
```

Review `git status` output before committing — confirm nothing unexpected
(stray test files, credentials) is staged.

## 2. SSH into the VPS

```bash
ssh deploy@89.167.93.25
```

From here on, every command runs **on the VPS**, not your machine.

## 3. Pull the latest code

```bash
cd /home/deploy/apps/jarvis
git pull origin main
```

## 4. Update the backend `.env` on the VPS

The VPS's `.env` needs the same new values your local one has:
`TAVILY_API_KEY`, `TOMTOM_API_KEY`, `LIVEKIT_URL`, `LIVEKIT_API_KEY`,
`LIVEKIT_API_SECRET`, `DEEPGRAM_API_KEY`.

```bash
nano /home/deploy/apps/jarvis/.env
```

Add/update those 6 lines with the real values (same ones in your local
`.env` — copy them over, don't regenerate new keys unless you want
separate dev/prod credentials). Save and exit (Ctrl+O, Enter, Ctrl+X in
nano).

**Do not commit this file or paste it anywhere public** — it has your
Supabase service role key and OpenAI key in it already.

## 5. Create the frontend's production env file

This file is gitignored on purpose (per-environment) and doesn't exist on
the VPS yet for a fresh value. Unlike the backend's `.env` which is read at
runtime, Next.js bakes `NEXT_PUBLIC_*` values in at **build time** — so this
must exist before step 7's `npm run build`.

```bash
nano /home/deploy/apps/jarvis/frontend/.env.local
```

Paste exactly this (production URL, not localhost):

```
NEXT_PUBLIC_SUPABASE_URL=https://bvvqgcqeruefbykytrtx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<same anon key as your local frontend/.env.local>
NEXT_PUBLIC_JARVIS_URL=https://89.167.93.25.sslip.io/api
```

Note the `/api` suffix — that's what Caddy strips before forwarding to the
backend (see `deploy/Caddyfile`). Using `localhost:8000` here (like local
dev does) would make the deployed frontend try to call itself instead of
the backend, which doesn't exist from the browser's perspective.

## 6. Install updated dependencies

```bash
cd /home/deploy/apps/jarvis
source venv/bin/activate
pip install -r backend/requirements.txt
cd frontend
npm install
cd ..
```

Watch for errors — `livekit-agents`, `livekit-plugins-*`, `tavily-python`
are new since the last deploy and need to install cleanly.

## 7. One-time VPS hardening update (log rotation)

Only needed once, not on every future deploy:

```bash
sudo bash deploy/setup-vps.sh
```

This is idempotent (safe to re-run) — it'll re-apply firewall rules,
fail2ban, etc. without breaking anything already configured, and this run
adds `pm2-logrotate` which didn't exist before.

## 8. Build the frontend

```bash
cd /home/deploy/apps/jarvis/frontend
npm run build
cd ..
```

If this fails, check that `frontend/.env.local` (step 5) was saved
correctly — a missing `NEXT_PUBLIC_SUPABASE_URL` will usually surface here
as a build-time error (same error you saw locally: "supabaseUrl is
required").

## 9. Start all three processes

```bash
bash deploy/start.sh
```

This now starts **three** PM2 processes (previously two):
- `jarvis-backend` — FastAPI, port 8000 internal
- `jarvis-frontend` — Next.js, port 3001 internal
- `jarvis-voice` — LiveKit worker, no local port (registers outbound)

## 10. Verify each process is actually healthy

```bash
pm2 status
```

All three should show `online`, not `errored` or stuck in a restart loop.

```bash
pm2 logs jarvis-voice --lines 30 --nostream
```

Look for a line like:
```
registered worker {"url": "wss://jarvis-atee52sm.livekit.cloud", ...}
```
If you instead see connection errors or "LIVEKIT_API_KEY not set," the
`.env` values from step 4 didn't load — double check them.

```bash
curl https://89.167.93.25.sslip.io/api/health
```
Expected: `{"status":"ok","version":"3.0.0"}`

```bash
curl -I https://89.167.93.25.sslip.io
```
Expected: `HTTP/2 200` (the frontend is being served).

## 11. Real browser smoke test

From your phone or laptop (not the VPS):
1. Open `https://89.167.93.25.sslip.io`, log in.
2. Send a text message, confirm a reply.
3. Enter Voice Mode, confirm it connects and JARVIS greets you.
4. Say something, confirm it responds correctly.

If voice fails here but `pm2 logs jarvis-voice` showed a clean
registration, the issue is almost always CORS or the frontend's
`NEXT_PUBLIC_JARVIS_URL` — re-check step 5.

## 12. Ongoing monitoring commands (keep these handy)

```bash
pm2 status                                   # all three processes, at a glance
pm2 logs --lines 50 --nostream                # all three logs combined
pm2 logs jarvis-voice --lines 50 --nostream   # voice worker only
pm2 monit                                     # live CPU/memory dashboard
```

PM2 auto-restarts any of the three processes if they crash. `pm2-logrotate`
(installed in step 7) keeps logs from growing unbounded — 10MB per file,
7 rotations kept, compressed.

## 13. Future updates (after this first deploy)

Once this initial setup is done, routine updates are simpler:

```bash
ssh deploy@89.167.93.25
cd /home/deploy/apps/jarvis
bash deploy/update.sh
```

`update.sh` now restarts `jarvis-voice` too, not just backend/frontend.

---

## If something goes wrong

- **A process won't stay `online`**: `pm2 logs <name> --lines 100 --nostream`
  — the actual error is almost always in there.
- **Voice worker won't register**: check `.env` has all 4 LiveKit/Deepgram
  values, no typos, no stray quotes.
- **Frontend built but shows old behavior**: `npm run build` must be
  re-run after any `frontend/.env.local` change — Next.js bakes
  `NEXT_PUBLIC_*` vars in at build time, a server restart alone won't pick
  up a changed value.
- **Nothing reachable at all**: `sudo systemctl status caddy` — confirm
  Caddy itself is running and didn't fail to reload.

Bring the actual command output back if any step doesn't match what's
described — don't guess past an error.
