# Deploy Frontend to Railway

Your backend is already deployed and working. Now you need to deploy the frontend as a separate service.

## Changes Made

✅ Updated frontend to use environment variable for backend API URL
✅ Updated backend CORS to allow Railway frontend domains
✅ Created `frontend/railway.toml` configuration

## Quick Deploy Steps

### 1. Commit and Push Changes

```bash
git add .
git commit -m "Configure frontend for Railway deployment with CORS"
git push
```

### 2. Create Frontend Service in Railway

1. Go to your Railway project dashboard
2. Click **"+ New"** → **"Empty Service"**
3. Click **"Add Source"** → **"GitHub Repo"**
4. Select your repository
5. **IMPORTANT**: In **Settings** → **Source**:
   - Find **"Root Directory"** field
   - Set it to: `frontend` (just the word "frontend", no slashes)
   - Save the setting
   - Railway will auto-detect `frontend/Dockerfile`

**This step is critical!** Without setting Root Directory, Railway will use the wrong Dockerfile and fail to build.

### 3. Set Environment Variable

In the Frontend service settings:
1. Go to **Variables** tab
2. Add a new variable:
   - **Name**: `VITE_API_URL`
   - **Value**: `https://proplineanalysis-production.up.railway.app`
   
   *(Use your actual backend URL)*

### 4. Generate Domain for Frontend

1. In Frontend service, go to **Settings** → **Networking**
2. Click **"Generate Domain"**
3. You'll get a URL like: `https://your-frontend.up.railway.app`

### 5. (Optional) Update Backend Variable

If you want to be explicit about CORS:
1. Go to Backend service settings
2. Add variable:
   - **Name**: `FRONTEND_URL`
   - **Value**: `https://your-frontend.up.railway.app`

(Not required - backend already allows all `.railway.app` domains)

## Verify Deployment

1. **Frontend loads**: Visit `https://your-frontend.up.railway.app`
2. **API connects**: Check browser console for successful API calls
3. **WebSocket works**: Dashboard should show real-time updates

## Architecture

```
┌─────────────────────────────────────────┐
│  Frontend (React + Vite)                │
│  https://your-frontend.railway.app      │
│  Port: 3000 (or Railway's PORT)         │
└─────────────┬───────────────────────────┘
              │
              │ HTTP/HTTPS + WebSocket
              │ (CORS enabled)
              │
┌─────────────▼───────────────────────────┐
│  Backend (FastAPI)                      │
│  https://proplineanalysis-production... │
│  Port: 8000 (or Railway's PORT)         │
│                                         │
│  Routes:                                │
│  - /health                              │
│  - /api/props/*                         │
│  - /api/movements/*                     │
│  - /api/analysis/*                      │
│  - /ws/dashboard (WebSocket)            │
└─────────────┬───────────────────────────┘
              │
              │
┌─────────────▼───────────────────────────┐
│  PostgreSQL Database                    │
│  (Railway's PostgreSQL service)         │
└─────────────────────────────────────────┘
```

## How It Works

### Development (Local)
- Frontend runs on `localhost:3000` with Vite
- Vite proxy forwards `/api` → `http://localhost:8000`
- Backend runs on `localhost:8000`

### Production (Railway)
- Frontend serves static files from `dist/` folder
- Frontend uses `VITE_API_URL` to point to backend
- API calls: `axios.get('/api/props')` → `https://backend.railway.app/api/props`
- WebSocket: `wss://backend.railway.app/ws/dashboard`
- Backend allows CORS from `*.railway.app` domains

## Troubleshooting

### Build Fails with "failed to compute cache key: /run.py not found"
**Problem**: Railway is using the wrong Dockerfile (root Python Dockerfile instead of frontend Node Dockerfile)

**Solution**: 
1. Go to Railway service → **Settings** → **Source**
2. Set **Root Directory** to `frontend`
3. Save and wait for automatic redeploy
4. Build should now show `FROM node:18-alpine` instead of `FROM python:3.11-slim`

### Build Fails with Python Errors (when expecting Node)
Same as above - Railway is using wrong Dockerfile. Set Root Directory to `frontend`.

### 404 on Frontend
- Check that Root Directory is set to `frontend` in Railway
- Verify the frontend build succeeded (check logs)
- Make sure Dockerfile is in `frontend/` directory

### API Calls Failing
- Check `VITE_API_URL` environment variable is set
- Verify backend URL is correct (include `https://`)
- Check browser console for CORS errors
- Verify backend is running and accessible

### CORS Errors
- Backend should auto-allow all `.railway.app` domains
- Check backend logs for CORS rejections
- Verify your frontend URL matches Railway domain pattern

### WebSocket Not Connecting
- Check browser console for WebSocket errors
- Verify backend WebSocket endpoint is accessible: `/ws/dashboard`
- Make sure backend URL uses correct protocol (https → wss)

## Cost Note

Railway charges per-service, so running frontend + backend = 2 services.

### Alternative: Single Service Deployment
If you want to save cost, you could serve the frontend from FastAPI:
1. Build frontend: `cd frontend && yarn build`
2. Add static file serving to FastAPI
3. Deploy only the backend
4. Frontend served from backend at root `/`

Let me know if you want help with the single-service approach!

## Next Steps After Frontend Deploys

1. ✅ Test all pages (Dashboard, Analysis, Movements, Players)
2. ✅ Verify real-time updates work
3. ✅ Add custom domains (if desired)
4. ✅ Set up monitoring/alerts
5. ✅ Configure auto-deploys on push

