# Polaris Computer - Operations Runbook

## Current Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Cloudflare Pages (Frontend)                │
│  - index.html, landing.html                            │
│  - Free tier, global CDN                               │
│  - Auto-deploys on push to main                        │
│  - URL: polariscomputer-d6j.pages.dev                  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Hetzner Server (Backend)                   │
│  - IP: 65.108.32.148                                   │
│  - FastAPI app (app_server.py) on port 8081            │
│  - Template containers (Docker)                        │
│  - SSH user: root                                      │
└─────────────────────────────────────────────────────────┘
         │              │
         ▼              ▼
┌─────────────┐  ┌─────────────┐
│  Supabase   │  │   Verda    │
│  PostgreSQL │  │  GPU Cloud │
│  (Auth/DB)  │  │  (Compute) │
└─────────────┘  └─────────────┘
```

## Services & Credentials

| Service | Purpose | Credentials Location |
|---------|---------|---------------------|
| Cloudflare Pages | Frontend hosting | GitHub Secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` |
| Hetzner | Backend + templates | SSH key, `.env` on server |
| Supabase | Auth + Database | `.env`: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET` |
| Verda | GPU compute | `.env`: `VERDA_CLIENT_ID`, `VERDA_CLIENT_SECRET` |
| Backblaze B2 | Storage | `.env`: `B2_*` variables |
| Stripe | Billing | `.env`: `STRIPE_*` variables |

---

## Deployment Procedures

### Frontend (Cloudflare Pages)

**Automatic:** Push to `main` branch triggers `.github/workflows/deploy-frontend.yml`

**Manual:**
```bash
# Install wrangler
npm i -g wrangler

# Login to Cloudflare
wrangler login

# Deploy
mkdir -p public
cp index.html landing.html public/
cp index.html public/app.html
wrangler pages deploy public --project-name=polaris-computer
```

### Backend (Hetzner)

**SSH to server:**
```bash
ssh root@65.108.32.148
```

**Update and restart:**
```bash
cd /path/to/polariscomputer
git pull origin main
pip install -r requirements.txt
# Restart service (depends on how it's running)
systemctl restart polaris  # if using systemd
# OR
pkill -f app_server.py && nohup python3 app_server.py > server.log 2>&1 &
```

**Check status:**
```bash
curl http://localhost:8081/health
docker ps  # Check template containers
```

---

## Migration Procedures

### Move Backend to Railway

1. Create Railway project at railway.app
2. Connect GitHub repo
3. Add environment variables from `.env`
4. Create `Dockerfile.api`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY *.py ./
COPY alembic/ ./alembic/
COPY alembic.ini .
EXPOSE 8081
CMD ["python3", "app_server.py"]
```
5. Create `railway.json`:
```json
{
  "build": {"builder": "DOCKERFILE", "dockerfilePath": "Dockerfile.api"},
  "deploy": {"startCommand": "python3 app_server.py"}
}
```
6. Add GitHub secret: `RAILWAY_TOKEN`
7. Update frontend `API_BASE` to Railway URL

**Cost:** ~$5-10/month

### Move Backend to Fly.io

1. Install flyctl: `brew install flyctl`
2. `fly launch` in project directory
3. Set secrets: `fly secrets set KEY=value`
4. Deploy: `fly deploy`

**Cost:** ~$5-10/month (similar to Railway)

### Move Frontend to Vercel

1. Connect repo to Vercel
2. Set output directory to `/`
3. No build command needed (static)

**Cost:** Free tier available

### Move Database from Supabase

1. Export data: Supabase dashboard → Database → Backups
2. Set up new PostgreSQL (Railway, Neon, or self-hosted)
3. Import data
4. Update `DATABASE_URL` in `.env`
5. Run migrations: `alembic upgrade head`

---

## Troubleshooting

### Backend not responding

```bash
# Check if running
ssh root@65.108.32.148 "ps aux | grep app_server"

# Check logs
ssh root@65.108.32.148 "tail -100 /path/to/server.log"

# Check port
ssh root@65.108.32.148 "netstat -tlnp | grep 8081"
```

### Template container issues

```bash
ssh root@65.108.32.148

# List containers
docker ps -a

# Check specific container logs
docker logs jupyter-notebook
docker logs ollama

# Restart container
docker restart container-name
```

### Database connection issues

```bash
# Test connection
python3 -c "from database import check_db_connection; import asyncio; print(asyncio.run(check_db_connection()))"

# Check Supabase status
curl https://your-project.supabase.co/rest/v1/ -H "apikey: YOUR_ANON_KEY"
```

### Auth issues

- Check JWT secrets match between `.env` and Supabase dashboard
- Verify `SUPABASE_JWT_SECRET` is the JWT secret (not anon key)
- Check token expiry (access: 30min, refresh: 30 days)

---

## Monitoring

### Health checks

```bash
# Backend health
curl https://your-api-domain/health

# Supabase health
curl https://your-project.supabase.co/rest/v1/

# Template server containers
ssh root@65.108.32.148 "docker ps"
```

### Logs

- Backend: `server.log` on Hetzner
- Cloudflare: Pages dashboard → Deployments
- Supabase: Dashboard → Logs

---

## Backup Procedures

### Database

Supabase handles backups automatically. For manual:
```bash
# Via Supabase CLI
supabase db dump -f backup.sql
```

### Template deployments state

```bash
# Backup deployment records
scp root@65.108.32.148:/path/to/template_deployments.json ./backup/
```

### Environment variables

Keep a secure copy of `.env` in a password manager or encrypted storage.

---

## Scaling Considerations

| Component | Current | Scale Option |
|-----------|---------|--------------|
| Frontend | Cloudflare Pages | Already global CDN |
| Backend | Single Hetzner | Railway/Fly.io with auto-scale |
| Database | Supabase | Upgrade Supabase plan |
| Templates | Single server | Multiple Hetzner servers with load balancer |
| GPU | Verda | Add Targon as backup provider |
