# Deployment Guide

This guide covers deploying your Prop Line Analysis application to Railway.app, the recommended platform for this project.

## Why Railway?

✅ **Simple deployment** - Connect GitHub and deploy in minutes  
✅ **Always-on** - Critical for scheduled scraping jobs  
✅ **Affordable** - $7-11/month for low traffic  
✅ **Built-in databases** - PostgreSQL and Redis included  
✅ **No Chromium** - Lightweight since we removed Playwright  

## Cost Estimate

| Service | Cost | Notes |
|---------|------|-------|
| Backend (FastAPI) | $1-3/month | Low traffic, small container |
| PostgreSQL | $5/month | 500MB database (plenty for this app) |
| Redis (optional) | $1-2/month | Small instance for caching |
| Frontend (static) | $0-1/month | Vite build, minimal traffic |
| **Total** | **$7-11/month** | For low-traffic production use |

## Prerequisites

1. **GitHub account** with your code pushed
2. **Railway account** - Sign up at [railway.app](https://railway.app)
3. **The Odds API key** (optional) - Only needed if using historical data

## Deployment Steps

### 1. Install Railway CLI (Optional but Recommended)

```bash
# macOS/Linux
curl -fsSL https://railway.app/install.sh | sh

# Or with npm
npm install -g @railway/cli

# Login
railway login
```

### 2. Create a New Railway Project

**Option A: Via CLI**
```bash
cd /path/to/prop_line_analysis
railway init
```

**Option B: Via Web Dashboard**
1. Go to [railway.app/new](https://railway.app/new)
2. Click "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect the Dockerfile

### 3. Add PostgreSQL Database

**Via CLI:**
```bash
railway add --database postgresql
```

**Via Dashboard:**
1. Click "New" → "Database" → "Add PostgreSQL"
2. Railway automatically creates `DATABASE_URL` environment variable
3. No manual configuration needed!

### 4. Add Redis (Optional)

**Via CLI:**
```bash
railway add --database redis
```

**Via Dashboard:**
1. Click "New" → "Database" → "Add Redis"
2. Railway automatically creates `REDIS_URL` environment variable

### 5. Configure Environment Variables

**Via CLI:**
```bash
# Set your API key (if using The Odds API)
railway variables set ODDS_API_KEY=your_actual_api_key_here

# Set environment to production
railway variables set ENVIRONMENT=production
railway variables set DEBUG=false

# Set scraping configuration
railway variables set SCRAPE_INTERVAL_MINUTES=5
railway variables set MAX_CONCURRENT_REQUESTS=5
railway variables set REQUEST_DELAY_MIN=1.0
railway variables set REQUEST_DELAY_MAX=2.0

# Set analysis thresholds
railway variables set LINE_MOVEMENT_THRESHOLD_PCT=10.0
railway variables set LINE_MOVEMENT_THRESHOLD_ABS=5.0
railway variables set HOURS_BEFORE_KICKOFF_THRESHOLD=3.0
```

**Via Dashboard:**
1. Go to your service → "Variables" tab
2. Click "New Variable"
3. Add the variables listed above
4. **Note:** `DATABASE_URL` is automatically set by Railway when you add PostgreSQL

### 6. Deploy Backend

**Via CLI:**
```bash
railway up
```

**Via GitHub (Recommended):**
1. Push your code to GitHub
2. Railway auto-deploys on every push to `main`
3. Check deployment logs in the Railway dashboard

### 7. Run Database Migrations

After first deployment, run migrations:

**Via CLI:**
```bash
railway run alembic upgrade head
```

**Via Dashboard:**
1. Go to your service → "Settings" → "Deploy"
2. The Dockerfile already includes migration in the startup command
3. Migrations run automatically on each deployment

### 8. Deploy Frontend

Railway can host your React frontend as a static site:

**Option A: Separate Service (Recommended)**

1. In Railway dashboard, click "New" → "Empty Service"
2. Connect to your GitHub repo
3. Set build settings:
   - **Root Directory:** `frontend`
   - **Build Command:** `yarn install && yarn build`
   - **Start Command:** `npx serve -s dist -p $PORT`
4. Add environment variable:
   ```
   VITE_API_URL=https://your-backend-service.railway.app
   ```

**Option B: External Hosting (Cheaper)**

Deploy frontend to Vercel/Netlify (free tier):
```bash
cd frontend
yarn build
# Deploy dist/ folder to Vercel or Netlify
```

### 9. Update CORS Settings

Update your backend to allow frontend domain:

In `src/api/main.py`, update the CORS middleware:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://your-frontend-app.railway.app",  # Add your Railway frontend URL
        # Or if using Vercel:
        "https://your-app.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Or use environment variable:
```bash
railway variables set CORS_ORIGINS="https://your-frontend-app.railway.app,http://localhost:5173"
```

### 10. Verify Deployment

Check that everything is working:

```bash
# Check health endpoint
curl https://your-app.railway.app/health

# Check API
curl https://your-app.railway.app/api/props/snapshots

# Check scheduler logs
railway logs
```

## Monitoring & Maintenance

### View Logs

**Via CLI:**
```bash
railway logs
```

**Via Dashboard:**
1. Go to your service
2. Click "Deployments" tab
3. View real-time logs

### Check Resource Usage

1. Go to your service → "Metrics" tab
2. Monitor:
   - CPU usage
   - Memory usage
   - Network traffic
   - Database size

### Database Backups

Railway automatically backs up PostgreSQL databases. To create manual backup:

```bash
# Connect to database
railway connect postgres

# Export database
pg_dump $DATABASE_URL > backup.sql
```

### Scaling

If you need more resources:

1. Go to service → "Settings" → "Resources"
2. Upgrade to a larger plan
3. Typical needs:
   - **Starter:** 512MB RAM, 1 vCPU ($5/month)
   - **Pro:** 1GB RAM, 2 vCPU ($10/month)

## Troubleshooting

### Deployment Fails

**Check build logs:**
```bash
railway logs --deployment
```

**Common issues:**
- Missing environment variables → Add them in Railway dashboard
- Database not connected → Ensure PostgreSQL service is added
- Port binding error → Railway sets `$PORT` automatically, make sure your app uses it

### Scheduler Not Running

**Check logs for scheduler startup:**
```bash
railway logs | grep "scheduler"
```

**Verify APScheduler is starting:**
- Look for "Starting application..." in logs
- Check that jobs are being added to scheduler

### Database Connection Issues

**Verify DATABASE_URL:**
```bash
railway variables
```

**Test connection:**
```bash
railway run python -c "from src.models.database import init_db; init_db(); print('✓ Database connected')"
```

### High Costs

**Optimize resource usage:**
1. Reduce scraping frequency (increase `SCRAPE_INTERVAL_MINUTES`)
2. Lower concurrent requests (`MAX_CONCURRENT_REQUESTS`)
3. Use smaller database plan if not storing much data
4. Consider removing Redis if not using caching

## Alternative: Fly.io Deployment

If you prefer Fly.io (potentially cheaper):

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Launch app
fly launch

# Add PostgreSQL
fly postgres create

# Attach database
fly postgres attach <postgres-app-name>

# Deploy
fly deploy
```

See [Fly.io docs](https://fly.io/docs/) for detailed instructions.

## Alternative: Docker Compose (Self-Hosted)

For self-hosting on your own VPS:

```bash
# On your server
git clone <your-repo>
cd prop_line_analysis

# Copy environment file
cp .env.example .env
# Edit .env with your values

# Start all services
docker-compose up -d

# Run migrations
docker-compose exec app alembic upgrade head
```

## Security Best Practices

1. ✅ **Never commit `.env` files** - Already in `.gitignore`
2. ✅ **Use Railway's secret variables** - For API keys
3. ✅ **Enable HTTPS** - Railway provides this automatically
4. ✅ **Restrict CORS origins** - Only allow your frontend domain
5. ✅ **Use non-root user** - Already configured in Dockerfile
6. ✅ **Keep dependencies updated** - Run `pip list --outdated` regularly

## Updating Your Deployment

### Push Updates

```bash
git add .
git commit -m "Your changes"
git push origin main
```

Railway automatically deploys on push to `main` branch.

### Manual Deploy

```bash
railway up
```

### Rollback

If something breaks:

**Via Dashboard:**
1. Go to "Deployments" tab
2. Find the last working deployment
3. Click "Redeploy"

**Via CLI:**
```bash
railway rollback
```

## Cost Optimization Tips

1. **Start small** - Begin with minimal resources, scale up if needed
2. **Monitor usage** - Check Railway metrics weekly
3. **Optimize scraping** - Only scrape during game days
4. **Database cleanup** - Archive old snapshots after analysis
5. **Frontend on Vercel** - Use free tier for static frontend
6. **Redis optional** - Only add if you need caching

## Support

- **Railway Docs:** https://docs.railway.app
- **Railway Discord:** https://discord.gg/railway
- **This Project Issues:** [GitHub Issues](https://github.com/your-username/prop_line_analysis/issues)

## Next Steps

After deployment:

1. ✅ Test all API endpoints
2. ✅ Verify scheduler is running (check logs)
3. ✅ Load initial data (run scraper manually first time)
4. ✅ Set up monitoring/alerts
5. ✅ Document your production URL
6. ✅ Share with users!

---

**Deployed successfully?** 🎉 Your prop line analysis app is now live and collecting data 24/7!

