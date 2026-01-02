# Railway Deployment Troubleshooting

## Common Issues and Solutions

### Issue 1: "Healthcheck failed - service unavailable"

**Symptoms:**
```
Attempt #1 failed with service unavailable
Attempt #2 failed with service unavailable
...
1/1 replicas never became healthy!
```

**Causes & Solutions:**

#### ❌ **Cause 1: DATABASE_URL Not Set**

The most common issue! Your app needs a database connection.

**Solution:**
```bash
# Check if PostgreSQL is added
railway service list

# If not, add PostgreSQL
railway add --database postgresql

# Verify DATABASE_URL is set
railway variables | grep DATABASE_URL
```

**Via Dashboard:**
1. Go to your project
2. Click "New" → "Database" → "PostgreSQL"
3. Railway automatically sets `DATABASE_URL`
4. Redeploy your service

---

#### ❌ **Cause 2: Wrong Port Configuration**

Railway assigns a dynamic `PORT` environment variable.

**Solution:**
The `start.sh` script now handles this automatically. Make sure you're using the latest code.

---

#### ❌ **Cause 3: Database Migrations Failing**

**Check logs:**
```bash
railway logs
```

Look for:
```
ERROR: Database migrations failed!
```

**Solutions:**
- Ensure PostgreSQL service is running
- Check DATABASE_URL is correct
- Try running migrations manually:
  ```bash
  railway run alembic upgrade head
  ```

---

### Issue 2: Build Succeeds but Deploy Fails

**Check Railway logs for specific errors:**

```bash
railway logs --deployment
```

**Common errors:**

#### "ModuleNotFoundError"
Missing dependencies in `requirements.txt`

**Solution:**
```bash
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Update dependencies"
git push
```

#### "Connection refused" or "Connection timeout"
Database not accessible

**Solution:**
- Ensure PostgreSQL service is in the same Railway project
- DATABASE_URL should be automatically linked

---

### Issue 3: App Starts but Crashes Immediately

**Check application logs:**
```bash
railway logs --tail 100
```

**Look for:**
- Python exceptions
- Database connection errors
- Missing environment variables

**Solution:**
Add try-catch blocks and better error messages (already done in `start.sh`)

---

### Issue 4: "alembic: command not found"

**Cause:** Dependencies not installed properly

**Solution:**
Rebuild with cache cleared:
```bash
railway up --detach
```

Or via dashboard: Settings → Clear build cache → Redeploy

---

## Debugging Steps

### 1. Check Service Status

```bash
railway status
```

Should show:
- ✓ Service is running
- ✓ Database is connected

### 2. View Real-time Logs

```bash
railway logs --follow
```

Look for:
```
Starting Prop Line Analysis API
✓ DATABASE_URL is set
✓ Using PORT: XXXX
Running database migrations...
✓ Migrations completed successfully
Starting uvicorn server...
```

### 3. Test Database Connection

```bash
railway run python -c "from src.models.database import get_engine; get_engine(); print('Database connected!')"
```

### 4. Check Environment Variables

```bash
railway variables
```

**Required variables:**
- `DATABASE_URL` (auto-set by Railway)

**Optional but recommended:**
- `ENVIRONMENT=production`
- `DEBUG=false`

### 5. Test Locally with Docker

```bash
# Build the image
docker build -t prop-analysis .

# Run with database URL
docker run -p 8000:8000 \
  -e DATABASE_URL="your_database_url" \
  prop-analysis
```

---

## Railway-Specific Fixes

### Fix 1: Redeploy After Adding Database

If you added PostgreSQL after deploying:

```bash
railway up --detach
```

Railway needs to restart to inject the DATABASE_URL.

### Fix 2: Check Service Logs

```bash
# View recent logs
railway logs --tail 50

# Follow live logs
railway logs --follow

# View only errors
railway logs | grep -i error
```

### Fix 3: Connect to Database Directly

```bash
railway connect postgres
```

Then check if tables exist:
```sql
\dt
```

Should show:
- prop_line_snapshots
- player_game_stats
- line_movements
- analysis_results

If tables don't exist, migrations didn't run. Check logs.

---

## Environment Variable Checklist

### Required ✅

- [ ] `DATABASE_URL` - Auto-set by Railway when PostgreSQL added
- [ ] `PORT` - Auto-set by Railway (used by app)

### Recommended ⚠️

- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] `SCRAPE_INTERVAL_MINUTES=5`

### Optional 💡

- [ ] `ODDS_API_KEY` - Only if using The Odds API
- [ ] `REDIS_URL` - Only if using Redis

---

## Still Having Issues?

### Get More Info

1. **Check build logs:**
   ```bash
   railway logs --deployment
   ```

2. **Check runtime logs:**
   ```bash
   railway logs --tail 200
   ```

3. **Test locally:**
   ```bash
   docker-compose up
   ```

### Common Solutions

1. **Redeploy:**
   ```bash
   railway up
   ```

2. **Clear cache and rebuild:**
   - Dashboard → Settings → Clear build cache → Redeploy

3. **Check Railway status page:**
   - https://status.railway.app/

### Get Help

1. **Railway Discord:** https://discord.gg/railway
2. **Railway Docs:** https://docs.railway.app
3. **Check this project's logs:** `railway logs`

---

## Success Checklist

When deployment is successful, you should see:

```bash
railway logs
```

Output:
```
==========================================
Starting Prop Line Analysis API
==========================================
✓ DATABASE_URL is set
✓ Using PORT: 7860
Running database migrations...
✓ Migrations completed successfully
Starting uvicorn server...
Listening on 0.0.0.0:7860
==========================================
============================================================
Starting application...
✓ Scheduler started
============================================================
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:7860
```

Then test the health endpoint:
```bash
curl https://your-app.railway.app/health
```

Should return:
```json
{"status": "healthy"}
```

✅ **You're live!**

---

## Prevention

To avoid these issues in the future:

1. ✅ Always add database **before** deploying app
2. ✅ Check environment variables **before** deploying
3. ✅ Test locally with Docker **before** pushing
4. ✅ Monitor logs during first deployment
5. ✅ Use `start.sh` script for better error messages

---

**Last Updated:** 2026-01-02

