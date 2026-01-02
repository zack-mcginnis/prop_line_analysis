# Railway Quick Start Guide

**Deploy your app in 10 minutes!** ⚡

## Step 1: Sign Up (30 seconds)

1. Go to [railway.app](https://railway.app)
2. Click "Start a New Project"
3. Sign in with GitHub

## Step 2: Create Project (1 minute)

```bash
# Option A: Via Web
# 1. Click "Deploy from GitHub repo"
# 2. Select "prop_line_analysis"
# 3. Click "Deploy Now"

# Option B: Via CLI (recommended)
npm install -g @railway/cli
railway login
cd /path/to/prop_line_analysis
railway init
```

## Step 3: Add Databases (2 minutes)

```bash
# Add PostgreSQL (required)
railway add --database postgresql

# Add Redis (optional, for caching)
railway add --database redis
```

**Via Web:** Click "New" → "Database" → Select PostgreSQL/Redis

## Step 4: Set Environment Variables (3 minutes)

**Required:**
```bash
railway variables set ENVIRONMENT=production
railway variables set DEBUG=false
```

**Optional (if using The Odds API):**
```bash
railway variables set ODDS_API_KEY=your_key_here
```

**Via Web:** Go to service → "Variables" tab → Add variables

## Step 5: Deploy! (3 minutes)

```bash
railway up
```

**Via Web:** Push to GitHub main branch → Auto-deploys

## Step 6: Run Migrations (1 minute)

```bash
railway run alembic upgrade head
```

**Or:** Migrations run automatically on deployment (configured in Dockerfile)

## Step 7: Get Your URL

```bash
railway domain
```

**Via Web:** Go to service → "Settings" → "Domains" → Generate domain

## Step 8: Test It! ✅

```bash
# Check health
curl https://your-app.railway.app/health

# Check API
curl https://your-app.railway.app/api/props/snapshots
```

---

## Environment Variables Cheat Sheet

Copy-paste these into Railway:

```bash
# Required
ENVIRONMENT=production
DEBUG=false

# Database (auto-set by Railway)
# DATABASE_URL=<auto-provided>

# Optional - The Odds API
ODDS_API_KEY=your_key_here
ODDS_API_BASE_URL=https://api.the-odds-api.com/v4

# Scraping Config
SCRAPE_INTERVAL_MINUTES=5
MAX_CONCURRENT_REQUESTS=5
REQUEST_DELAY_MIN=1.0
REQUEST_DELAY_MAX=2.0

# Analysis Config
LINE_MOVEMENT_THRESHOLD_PCT=10.0
LINE_MOVEMENT_THRESHOLD_ABS=5.0
HOURS_BEFORE_KICKOFF_THRESHOLD=3.0
```

---

## Deploy Frontend (Optional)

### Option 1: Railway (Separate Service)

```bash
cd frontend
railway init
railway up
```

**Settings:**
- Root Directory: `frontend`
- Build Command: `yarn install && yarn build`
- Start Command: `npx serve -s dist -p $PORT`

**Environment Variable:**
```bash
railway variables set VITE_API_URL=https://your-backend.railway.app
```

### Option 2: Vercel (Free)

```bash
cd frontend
yarn build
npx vercel --prod
```

---

## Monitoring

**View Logs:**
```bash
railway logs
```

**View Metrics:**
Go to service → "Metrics" tab

**Check Scheduler:**
```bash
railway logs | grep "scheduler"
```

---

## Costs

| Item | Cost |
|------|------|
| Backend | $1-3/mo |
| PostgreSQL | $5/mo |
| Redis | $1-2/mo |
| **Total** | **$7-11/mo** |

**Free trial:** $5 credit for new accounts

---

## Troubleshooting

### Build Fails
```bash
railway logs --deployment
```

### Can't Connect to Database
```bash
railway variables | grep DATABASE_URL
```

### Scheduler Not Running
```bash
railway logs | grep "Starting application"
```

### Need Help?
- [Railway Docs](https://docs.railway.app)
- [Railway Discord](https://discord.gg/railway)
- See full `DEPLOYMENT.md` for detailed guide

---

## Update Your App

```bash
git add .
git commit -m "Update"
git push origin main
```

Railway auto-deploys on push! 🚀

---

## Rollback

**Via CLI:**
```bash
railway rollback
```

**Via Web:**
Go to "Deployments" → Select previous deployment → "Redeploy"

---

**That's it!** Your app is now live at `https://your-app.railway.app` 🎉

