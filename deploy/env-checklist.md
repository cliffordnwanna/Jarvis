# Environment Variables Checklist

## Backend .env (repo root)
- [ ] OPENAI_API_KEY — from platform.openai.com
- [ ] SUPABASE_URL — from Supabase project settings
- [ ] SUPABASE_SERVICE_ROLE_KEY — from Supabase API settings (secret, backend only)
- [ ] SUPABASE_ANON_KEY — from Supabase API settings (public)
- [ ] DEFAULT_TIMEZONE — Africa/Lagos
- [ ] FRONTEND_URL — https://89.167.93.25.sslip.io

## Frontend frontend/.env.local
- [ ] NEXT_PUBLIC_SUPABASE_URL — same as above
- [ ] NEXT_PUBLIC_SUPABASE_ANON_KEY — same as above
- [ ] NEXT_PUBLIC_JARVIS_URL — https://89.167.93.25.sslip.io/api

## Critical notes:
- NEVER commit .env or .env.local to git (.gitignore already covers both)
- SUPABASE_SERVICE_ROLE_KEY bypasses RLS — backend only, never in frontend
- OPENAI_API_KEY covers both GPT-4o chat AND Realtime API voice
- scp both files to the VPS before running deploy/start.sh
