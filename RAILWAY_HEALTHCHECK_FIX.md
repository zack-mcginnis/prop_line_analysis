# Railway Healthcheck Fix

## The Problem

Your Railway deployment was failing healthchecks with "service unavailable" errors. This is one of the most common Railway deployment issues.

## Root Causes Identified

1. **Conflicting startup commands**: The `Dockerfile` CMD and `railway.toml` startCommand were different
2. **Scheduler blocking startup**: The scheduler was starting immediately during app lifespan, potentially blocking the healthcheck
3. **Missing database wait**: The app didn't wait for the database to be ready before running migrations
4. **Short healthcheck timeout**: 100 seconds wasn't enough time for migrations + scheduler startup

## Changes Made

### 1. Updated `railway.toml`
- Changed `startCommand` to use `./start.sh` for consistency
- Increased `healthcheckTimeout` from 100 to 300 seconds (5 minutes)
- This gives migrations and startup more time to complete

### 2. Updated `src/api/main.py`
- **Delayed scheduler startup**: Scheduler now starts 5 seconds after the app, allowing healthchecks to succeed first
- Added `flush=True` to all print statements for better Railway log visibility
- Scheduler runs in background task, doesn't block app startup

### 3. Updated `start.sh`
- Added database readiness check using `pg_isready`
- Waits up to 60 seconds for database to be ready before running migrations
- Better error messages

### 4. Updated `Dockerfile`
- Added `postgresql-client` to runtime dependencies for `pg_isready` command
- This allows the startup script to verify database connectivity

## How to Deploy

1. **Commit and push these changes:**
   ```bash
   git add .
   git commit -m "Fix Railway healthcheck issues"
   git push
   ```

2. **Redeploy on Railway:**
   - Railway will automatically detect the push and redeploy
   - OR manually trigger a redeploy from the Railway dashboard

3. **Check the logs:**
   - Watch the deployment logs in Railway
   - You should see:
     - "Database is ready"
     - "Migrations completed successfully"
     - "Application ready (scheduler will start in 5s)"
     - "Scheduler started (delayed)"

## Troubleshooting

If healthcheck still fails, check:

### 1. Database URL is set
```bash
# In Railway dashboard, verify:
# - PostgreSQL service is running
# - DATABASE_URL variable is set in your app service
# - DATABASE_URL points to the PostgreSQL service
```

### 2. Check deployment logs
Look for these error patterns:
- `DATABASE_URL is not set` → Add PostgreSQL service and link it
- `Connection refused` → Database isn't ready yet (should auto-retry now)
- `Migration failed` → Check if manual database setup is needed

### 3. Test healthcheck locally
```bash
# Run with Docker
docker build -t prop-app .
docker run -p 8000:8000 -e DATABASE_URL="postgresql://..." prop-app

# In another terminal:
curl http://localhost:8000/health
# Should return: {"status":"healthy","timestamp":"..."}
```

### 4. Increase timeout further if needed
If your database migrations take longer than 5 minutes:
```toml
# In railway.toml
healthcheckTimeout = 600  # 10 minutes
```

## Common Railway Issues

1. **PORT binding**: Always use `0.0.0.0` not `localhost` (✓ Already correct)
2. **PORT environment variable**: Use `$PORT` not hardcoded `8000` (✓ Already correct)
3. **Database connection string**: Railway uses `postgresql://` format (✓ Already correct)
4. **Build time**: Railway has 30 minute build timeout (✓ Your build is fast)
5. **Startup time**: Railway healthcheck waits 100s by default (✓ Now 300s)

## Why This Happens

Railway's healthcheck system:
- Starts immediately after container starts
- Retries every few seconds for the timeout period
- Expects HTTP 200 response from healthcheck path
- Fails deployment if no successful response within timeout

If your app:
- Takes time to start (migrations, scheduler, etc.)
- Crashes during startup
- Doesn't bind to 0.0.0.0:$PORT
- Has blocking operations in startup

Then healthchecks will fail!

## Next Steps

After this deploys successfully:

1. **Monitor the dashboard**: Your app should now start within 1-2 minutes
2. **Check scheduler**: Look for "Scheduler started (delayed)" in logs after ~5 seconds
3. **Test the API**: Try accessing your `/health` and `/api/props/dashboard` endpoints
4. **Frontend deployment**: Once backend works, deploy your frontend

## Support

If you still have issues:
1. Check Railway dashboard logs
2. Look for error messages in the startup sequence
3. Verify all environment variables are set
4. Test database connection manually

Common Railway commands:
```bash
# View logs
railway logs

# Check environment variables
railway variables

# SSH into container (for debugging)
railway run bash
```

