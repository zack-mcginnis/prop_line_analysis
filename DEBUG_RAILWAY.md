# Railway Deployment Debug Guide

## Your Current Issue: Build Succeeds, Healthcheck Fails

This means:
- ✅ Docker image built successfully
- ❌ Application won't start or crashes immediately

## Step 1: Check Runtime Logs (MOST IMPORTANT)

```bash
railway logs --tail 50
```

**Look for these error messages:**

### Error 1: "DATABASE_URL is not set"
```
ERROR: DATABASE_URL environment variable is not set!
Please set DATABASE_URL in Railway dashboard
```

**Solution:** Add PostgreSQL database (see Step 2 below)

### Error 2: "Database migrations failed"
```
ERROR: Database migrations failed!
```

**Solution:** Database exists but can't connect. Check DATABASE_URL is correct.

### Error 3: No logs at all
Container exits immediately before logging anything.

**Solution:** Check if start.sh has correct line endings (Unix vs Windows)

---

## Step 2: Verify PostgreSQL Database Exists

```bash
# List all services in your project
railway service list
```

**You should see:**
- Your backend service (prop-line-analysis or similar)
- PostgreSQL database service

**If PostgreSQL is missing:**

```bash
# Add PostgreSQL
railway add --database postgresql

# This will automatically set DATABASE_URL
```

**Or via Dashboard:**
1. Go to your Railway project
2. Click "New" button
3. Select "Database"
4. Choose "PostgreSQL"
5. Wait for it to provision (~30 seconds)

---

## Step 3: Verify Environment Variables

```bash
railway variables
```

**Required variables (should be automatically set):**
- `DATABASE_URL` - Should look like: `postgresql://postgres:xxx@xxx.railway.app:5432/railway`
- `PORT` - Should be set by Railway automatically

**If DATABASE_URL is missing:**
- PostgreSQL isn't added OR
- It's not linked to your service

**To link database to service:**
```bash
# In your service directory
railway link

# Then check variables again
railway variables
```

---

## Step 4: Test Start Script Locally

```bash
# Make sure start.sh has Unix line endings
dos2unix start.sh  # If you're on Windows
# Or
sed -i 's/\r$//' start.sh  # Convert CRLF to LF

# Make it executable
chmod +x start.sh

# Test it
./start.sh
```

**If this fails locally, fix it before pushing to Railway.**

---

## Step 5: Check Service Settings

Via Railway Dashboard:
1. Go to your service
2. Click "Settings" tab
3. Check "Start Command" is not overriding CMD

**Start Command should be:** EMPTY or `./start.sh`

If it's set to something else (like `uvicorn ...`), clear it and use the Dockerfile's CMD.

---

## Step 6: Manual Debugging on Railway

Run commands directly in Railway environment:

```bash
# Check if DATABASE_URL exists
railway run printenv | grep DATABASE_URL

# Test database connection
railway run python -c "import os; print('DB:', os.getenv('DATABASE_URL', 'NOT SET'))"

# Try to run migrations manually
railway run alembic upgrade head

# Try to start app manually
railway run uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

---

## Common Solutions

### Solution 1: PostgreSQL Not Added
**Symptom:** Logs show "DATABASE_URL is not set"

```bash
railway add --database postgresql
railway up  # Redeploy
```

### Solution 2: Wrong Line Endings in start.sh
**Symptom:** No logs, immediate crash

```bash
# Fix line endings
sed -i 's/\r$//' start.sh

# Commit and push
git add start.sh
git commit -m "Fix start.sh line endings"
git push
```

### Solution 3: Permission Issues
**Symptom:** "Permission denied" in logs

```bash
# Ensure start.sh is executable (should be in Dockerfile)
# Already done with: RUN chmod +x start.sh
```

### Solution 4: Port Binding Issues
**Symptom:** "Address already in use"

The start.sh script uses `${PORT:-8000}` which should work.
Railway sets PORT automatically.

---

## Quick Checklist

- [ ] PostgreSQL database added to Railway project
- [ ] `railway service list` shows both backend and PostgreSQL
- [ ] `railway variables` shows DATABASE_URL
- [ ] `railway logs` shows actual error messages
- [ ] start.sh has Unix line endings (LF, not CRLF)
- [ ] Local test: `./start.sh` works (with local DATABASE_URL)

---

## Next Steps for You

1. **Run this first:**
   ```bash
   railway logs --tail 50
   ```
   
2. **Copy the output and look for errors**

3. **Check if PostgreSQL exists:**
   ```bash
   railway service list
   ```

4. **If PostgreSQL is missing, add it:**
   ```bash
   railway add --database postgresql
   railway up
   ```

---

## Expected Successful Output

When working correctly, `railway logs` should show:

```
==========================================
Starting Prop Line Analysis API
==========================================
✓ DATABASE_URL is set
✓ Using PORT: 7860
Running database migrations...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> abc123, Initial migration
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
INFO:     Uvicorn running on http://0.0.0.0:7860 (Press CTRL+C to quit)
```

Then healthcheck will pass!

---

## Still Stuck?

Share the output of:
1. `railway logs --tail 50`
2. `railway service list`
3. `railway variables | grep DATABASE_URL`

This will tell us exactly what's wrong.

