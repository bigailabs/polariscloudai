# Polaris Computer - Operations Runbook

## Current Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Cloudflare Pages (Frontend)                │
│  - polaris.computer (custom domain)                    │
│  - polariscomputer.pages.dev (default)                 │
│  - Auto-deploys on push to main                        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Cloudflare DNS Proxy                       │
│  - api.polaris.computer → Backend server               │
│  - Provides SSL termination                            │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Backend Server (Currently Hetzner)         │
│  - IP: 65.109.75.29                                   │
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

---

## Quick Reference - Key Locations

| What | Where |
|------|-------|
| Frontend URL | `https://polaris.computer` |
| API URL | `https://api.polaris.computer` |
| Backend Server IP | `65.109.75.29` |
| DNS Management | Cloudflare Dashboard → polaris.computer → DNS |
| Frontend Deployment | Cloudflare Dashboard → Workers & Pages → polariscomputer |
| API URL in code | `index.html` line ~1498: `API_BASE` variable |

---

## Disaster Recovery - Start from Zero

### Step 1: Get a New Server

Provision a server (Hetzner, DigitalOcean, AWS, etc.) with:
- Ubuntu 22.04+
- Docker installed
- Python 3.10+
- At least 4GB RAM, 2 CPU cores

Note the new server's **IP address**.

### Step 2: Deploy Backend to New Server

```bash
# SSH to new server
ssh root@NEW_IP_ADDRESS

# Install dependencies
apt update && apt install -y python3 python3-pip python3-venv docker.io git

# Clone repo
git clone https://github.com/bigailabs/polariscomputer.git
cd polariscomputer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Create .env file (copy from password manager or .env.example)
cp .env.example .env
nano .env  # Fill in all values

# Run database migrations
alembic upgrade head

# Start the server
nohup python3 app_server.py > server.log 2>&1 &

# Verify it's running
curl http://localhost:8081/health
```

### Step 3: Update DNS to Point to New Server

1. Go to **Cloudflare Dashboard** → **polaris.computer** → **DNS**
2. Find the `A` record for `api`
3. Click **Edit**
4. Change the IP address to your **new server IP**
5. Click **Save**
6. Wait 1-5 minutes for propagation

```
Type: A
Name: api
Content: NEW_IP_ADDRESS  ← Change this
Proxy: Proxied (orange cloud)
```

### Step 4: Verify Everything Works

```bash
# Test API directly
curl https://api.polaris.computer/health

# Test frontend
# Visit https://polaris.computer in browser
```

---

## Services & Credentials

| Service | Purpose | Where to Find Credentials |
|---------|---------|---------------------------|
| Cloudflare | DNS + Frontend hosting | Cloudflare dashboard (login: Fredesere@gmail.com) |
| Hetzner | Backend server | SSH key on local machine |
| Supabase | Auth + Database | Supabase dashboard → Settings → API |
| Verda | GPU compute | Verda dashboard |
| Backblaze B2 | Storage | Backblaze dashboard → App Keys |
| Stripe | Billing | Stripe dashboard → Developers → API keys |
| GitHub | Code repo | GitHub Settings → Developer settings → Tokens |

### Required Environment Variables (.env)

```bash
# Database (Supabase)
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@HOST:5432/postgres
SUPABASE_URL=https://PROJECT.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret

# GPU Provider
VERDA_CLIENT_ID=your-client-id
VERDA_CLIENT_SECRET=your-client-secret

# Storage
B2_KEY_ID=your-key-id
B2_APPLICATION_KEY=your-app-key
B2_BUCKET_NAME=your-bucket

# Payments
STRIPE_SECRET_KEY=sk_...
STRIPE_PUBLISHABLE_KEY=pk_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Auth
JWT_SECRET_KEY=random-secret-key
JWT_REFRESH_SECRET_KEY=another-random-secret
```

---

## Changing the Backend Server IP

When you move to a new server, you need to update **one place**:

### Cloudflare DNS

1. Go to: https://dash.cloudflare.com
2. Click **polaris.computer**
3. Click **DNS** in sidebar
4. Find: `A | api | OLD_IP`
5. Click **Edit**
6. Change IP to new server IP
7. **Save**

That's it. The frontend code (`index.html`) uses `https://api.polaris.computer` which Cloudflare routes to whatever IP you configure.

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
wrangler pages deploy public --project-name=polariscomputer
```

### Backend (Current Hetzner Server)

**SSH to server:**
```bash
ssh root@65.109.75.29
```

**Update and restart:**
```bash
cd /root/polariscomputer  # or wherever it's installed
source venv/bin/activate
git pull origin main
pip install -r requirements.txt
pkill -f app_server.py
nohup python3 app_server.py > server.log 2>&1 &
```

**Check status:**
```bash
curl http://localhost:8081/health
docker ps  # Check template containers
tail -50 server.log  # Check logs
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
5. Deploy and get Railway URL
6. Update Cloudflare DNS:
   - Delete the `A` record for `api`
   - Add `CNAME | api | your-app.railway.app`

**Cost:** ~$5-10/month

### Move Backend to Fly.io

1. Install flyctl: `brew install flyctl`
2. `fly launch` in project directory
3. Set secrets: `fly secrets set KEY=value`
4. Deploy: `fly deploy`
5. Update Cloudflare DNS to point `api` to Fly.io URL

**Cost:** ~$5-10/month

### Move Frontend to Vercel

1. Connect repo to Vercel
2. Set output directory to `/`
3. No build command needed (static)
4. Update domain in Vercel dashboard

**Cost:** Free tier available

### Move Database from Supabase

1. Export data: Supabase dashboard → Database → Backups
2. Set up new PostgreSQL (Railway, Neon, or self-hosted)
3. Import data
4. Update `DATABASE_URL` in `.env`
5. Run migrations: `alembic upgrade head`

---

## Troubleshooting

### "Failed to load applications" on frontend

**Cause:** Frontend can't reach backend API

**Check:**
```bash
# Is DNS resolving?
nslookup api.polaris.computer

# Is backend responding?
curl https://api.polaris.computer/health

# SSH to server and check locally
ssh root@65.109.75.29 "curl http://localhost:8081/health"
```

**Fix:**
- If DNS wrong → Update Cloudflare DNS A record
- If backend down → SSH and restart: `nohup python3 app_server.py > server.log 2>&1 &`
- If port blocked → Check firewall: `ufw allow 8081`

### Backend not responding

```bash
# Check if running
ssh root@65.109.75.29 "ps aux | grep app_server"

# Check logs
ssh root@65.109.75.29 "tail -100 server.log"

# Check port
ssh root@65.109.75.29 "netstat -tlnp | grep 8081"

# Restart
ssh root@65.109.75.29 "pkill -f app_server.py; cd /root/polariscomputer && nohup python3 app_server.py > server.log 2>&1 &"
```

### Template container issues

```bash
ssh root@65.109.75.29

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
curl https://xuxtkpixggpmzjjogkmt.supabase.co/rest/v1/ -H "apikey: YOUR_ANON_KEY"
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
curl https://api.polaris.computer/health

# Supabase health
curl https://xuxtkpixggpmzjjogkmt.supabase.co/rest/v1/

# Template server containers
ssh root@65.109.75.29 "docker ps"
```

### Logs

- Backend: `server.log` on server
- Cloudflare: Pages dashboard → Deployments
- Supabase: Dashboard → Logs

---

## Backup Procedures

### CRITICAL: Environment Variables (.env)

**If you lose the server, you lose `.env`. Back it up NOW.**

**Option 1: Password Manager (Recommended)**
- Copy entire `.env` file contents to 1Password/Bitwarden
- Create entry named "Polaris Computer - Production Env"

**Option 2: Local encrypted backup**
```bash
# Backup from server
scp root@65.109.75.29:/root/polariscomputer/.env ~/Documents/TOOLS/.credentials/polaris-env-backup

# Encrypt it
gpg -c ~/Documents/TOOLS/.credentials/polaris-env-backup
```

**What you CAN recover without .env:**
- Code: GitHub repo
- Database: Supabase (external service, has own login)
- DNS: Cloudflare (external service, has own login)

**What you CANNOT recover without .env:**
- `JWT_SECRET_KEY` / `JWT_REFRESH_SECRET_KEY` - All user sessions invalidated
- `VERDA_CLIENT_ID` / `VERDA_CLIENT_SECRET` - Get from Verda dashboard
- `STRIPE_*` keys - Get from Stripe dashboard
- `STORJ_*` keys - Get from Storj dashboard

**Recovery if .env is lost:**
1. Regenerate JWT secrets (all users must re-login)
2. Get API keys from respective dashboards (Verda, Stripe, Storj, Supabase)
3. Rebuild `.env` from `.env.example` template

### Database

Supabase handles backups automatically. For manual:
```bash
# Via Supabase CLI
supabase db dump -f backup.sql
```

### Template deployments state

```bash
# Backup deployment records (lost = users see empty dashboard, can redeploy)
scp root@65.109.75.29:/root/polariscomputer/template_deployments.json ./backup/
```

### Full server backup script

Run this periodically or before server changes:
```bash
#!/bin/bash
# backup-polaris.sh
BACKUP_DIR=~/Documents/PROJECTS/polariscomputer/backups/$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

# Backup .env (CRITICAL)
scp root@65.109.75.29:/root/polariscomputer/.env $BACKUP_DIR/

# Backup deployment state
scp root@65.109.75.29:/root/polariscomputer/template_deployments.json $BACKUP_DIR/

# Backup database
supabase db dump -f $BACKUP_DIR/database.sql

echo "Backup complete: $BACKUP_DIR"
```

---

## Scaling Considerations

| Component | Current | Scale Option |
|-----------|---------|--------------|
| Frontend | Cloudflare Pages | Already global CDN |
| Backend | Single Hetzner | Railway/Fly.io with auto-scale |
| Database | Supabase | Upgrade Supabase plan |
| Templates | Single server | Multiple servers with load balancer |
| GPU | Verda | Add Targon as backup provider |

---

## API Domain Configuration (api.polaris.computer)

### Current Setup (as of 2026-02-02)

The API is accessible via:
1. **Direct IP:** `http://65.109.75.29:8081` (no SSL)
2. **Quick Tunnel:** `https://accepting-fishing-testing-enough.trycloudflare.com` (temporary)
3. **Custom Domain:** `https://api.polaris.computer` (requires Cloudflare DNS fix)

### Fix api.polaris.computer (521 Error)

The 521 error means Cloudflare cannot reach the origin server. This happens when:
- The DNS A record points to the wrong IP
- The server firewall blocks Cloudflare IPs

**To fix:**

1. Login to Cloudflare Dashboard: https://dash.cloudflare.com
   - Account: Fredesere@gmail.com

2. Go to **polaris.computer** → **DNS**

3. Find the `api` A record and update it:
   ```
   Type: A
   Name: api
   Content: 65.109.75.29
   Proxy status: Proxied (orange cloud)
   TTL: Auto
   ```

4. Wait 1-2 minutes for propagation

5. Test: `curl https://api.polaris.computer/health`

### Server-Side Nginx Configuration

The server has nginx configured to route `api.polaris.computer` traffic:

```
Location: /etc/nginx/sites-enabled/polaris-api
Proxies to: http://127.0.0.1:8081
```

To verify/update nginx:
```bash
ssh root@65.109.75.29
cat /etc/nginx/sites-enabled/polaris-api
nginx -t && systemctl reload nginx
```

### Cloudflare Quick Tunnel (Temporary Fallback)

When the custom domain is not working, use a quick tunnel:

```bash
# SSH to server
ssh root@65.109.75.29

# Start quick tunnel (runs in foreground)
cloudflared tunnel --url http://localhost:8081

# Or run in background with nohup
nohup cloudflared tunnel --url http://localhost:8081 > /root/tunnel.log 2>&1 &
```

The tunnel will output a URL like: `https://something-random.trycloudflare.com`

**Important:** Update `app.html` API_BASE with the new tunnel URL:
```javascript
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? ''
    : 'https://NEW-TUNNEL-URL.trycloudflare.com';
```

### Named Tunnel Setup (Production - Not Yet Configured)

For a permanent tunnel that survives reboots:

1. **Authenticate cloudflared:**
   ```bash
   ssh root@65.109.75.29
   cloudflared tunnel login
   # Opens browser URL - login with Cloudflare account
   ```

2. **Create named tunnel:**
   ```bash
   cloudflared tunnel create polaris-api
   # Note the tunnel ID (UUID)
   ```

3. **Create config file:**
   ```bash
   cat > ~/.cloudflared/config.yml << EOF
   tunnel: <TUNNEL-ID>
   credentials-file: /root/.cloudflared/<TUNNEL-ID>.json
   
   ingress:
     - hostname: api.polaris.computer
       service: http://localhost:8081
     - service: http_status:404
   EOF
   ```

4. **Create DNS record:**
   ```bash
   cloudflared tunnel route dns polaris-api api.polaris.computer
   ```

5. **Install as service:**
   ```bash
   cloudflared service install
   systemctl enable cloudflared
   systemctl start cloudflared
   ```

---

## Emergency Recovery - SSH Locked Out

### Problem: WARP Broke SSH Access

If Cloudflare WARP was installed on the server and enabled in tunnel mode, it routes ALL traffic (including SSH) through Cloudflare, breaking SSH access.

**Symptoms:**
- `ssh root@65.109.75.29` times out
- Server is technically "running" but unreachable
- This happened on 2026-02-02 when attempting to fix IPv6 connectivity

### Solution: Use Hetzner Cloud Console

1. **Login to Hetzner Cloud Console:**
   - Go to: https://console.hetzner.cloud
   - Login with your Hetzner credentials

2. **Access the server via VNC Console:**
   - Click on your server (65.109.75.29)
   - Click **"Console"** button (top right) or **Actions → Console**
   - This opens a VNC session directly to the server (bypasses network)

3. **Disable WARP:**
   ```bash
   # Disconnect WARP tunnel
   warp-cli disconnect

   # Set WARP to proxy mode (only proxies browser traffic, not SSH)
   warp-cli mode proxy

   # Or completely disable WARP
   systemctl stop warp-svc
   systemctl disable warp-svc
   ```

4. **Verify SSH works again:**
   - From your local machine: `ssh root@65.109.75.29`

5. **If WARP is needed for IPv6:**
   - Use proxy mode instead of tunnel mode
   - Or configure WARP to exclude SSH port: `warp-cli add-excluded-route 0.0.0.0/0`

### Prevention

**Never enable WARP tunnel mode on a server you need SSH access to!**

If you need IPv6 connectivity for Supabase:
- Use Supabase connection pooler instead (pgbouncer - supports IPv4)
- Or enable native IPv6 on the server through Hetzner settings

---

## Current Server (as of 2026-02-03)

**API Server:** 135.181.8.213 (Hetzner)
- Ubuntu 24.04, 16GB RAM, 4 vCPU
- Cloudflare tunnel: `vendor-athletic-helpful-latitude.trycloudflare.com`
- Database: Using Supavisor session pooler (IPv4 compatible)

**Old Server:** 65.109.75.29 (ABANDONED - WARP locked out SSH)

### Quick Reference

```bash
# SSH to API server
ssh root@135.181.8.213

# Check API server status
ssh root@135.181.8.213 "curl localhost:8081/health"

# Restart API server
ssh root@135.181.8.213 "cd /root/polariscomputer && source venv/bin/activate && pkill -f app_server.py && nohup python3 app_server.py > server.log 2>&1 &"

# Check tunnel
ssh root@135.181.8.213 "grep trycloudflare /root/tunnel.log"

# Restart tunnel
ssh root@135.181.8.213 "pkill cloudflared && nohup cloudflared tunnel --url http://localhost:8081 > /root/tunnel.log 2>&1 &"
```
