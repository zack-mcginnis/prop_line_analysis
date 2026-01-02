# Getting Started - Quick Guide

## You're Ready to Collect Data! 🚀

Everything is set up. Here's how to start collecting player prop data using BettingPros (free).

---

## Step 1: Verify Everything Works

### Check Database
```bash
docker-compose ps
```
✅ Should show `prop_analysis_db` running on port 5432

---

## Step 2: Load Mock Data (Start Testing Immediately!)

Since BettingPros only posts props 24-48h before games, **load mock data** to test everything now:

```bash
uv run python scripts/load_mock_data.py
```

✅ This loads 18 realistic prop snapshots for 7 players  
✅ Includes 5 significant late line drops (tests your thesis)  
✅ Ready for immediate API testing and dashboard development  

**What's included:**
- Bucky Irving: Late 8-yard drop → went UNDER
- Christian McCaffrey: Late 7-yard drop → went UNDER  
- Tyreek Hill: Late 8-yard drop → went UNDER
- Plus control scenarios (stable lines, early drops, line increases)

See `MOCK_DATA_GUIDE.md` for full details.

---

## Step 3: Test Your System

### Start Backend

```bash
uv run uvicorn src.api.main:app --reload
```

### Test API Endpoints

```bash
# View mock snapshots
curl http://localhost:8000/api/props/snapshots | jq

# View line movements (should show 5 significant drops)
curl "http://localhost:8000/api/movements/?min_drop_yards=5" | jq

# Check specific player
curl "http://localhost:8000/api/props/snapshots?player_name=Bucky Irving" | jq
```

### Start Dashboard

```bash
cd frontend
yarn install
yarn dev
```

Visit http://localhost:3000 to see your data visualized!

---

## Step 4: Start Collecting Live Data (When Available)

**BettingPros posts props 24-48 hours before games.** Once Week 18 props are available (likely Thursday/Friday):

### Option A: Manual Collection (Testing)

Run the scraper once to test:
```bash
uv run python scripts/run_scraper.py
```

This will:
- Discover all RB/WR in games starting within 12 hours
- Scrape their rushing/receiving prop lines from BettingPros
- Save to your PostgreSQL database

### Option B: Automated Collection (Recommended)

Start the backend with the scheduler:
```bash
uv run uvicorn src.api.main:app --reload
```

This will:
- Run the scraper automatically every 5 minutes on game days
- Collect data throughout the day leading up to kickoff
- Build your dataset over time

**Game Day Schedule:**
- Sunday: 6am - midnight (all games)
- Monday: 4pm - midnight (Monday Night Football)
- Thursday: 4pm - midnight (Thursday Night Football)
- Saturday: 12pm - midnight (late season games)

---

## Step 5: Monitor Collection (Once Live Data Starts)

### View API Docs
Visit http://localhost:8000/docs

### Check Collected Snapshots
```bash
curl http://localhost:8000/api/props/snapshots?limit=10
```

### View Line Movements
```bash
curl http://localhost:8000/api/movements/?min_drop_yards=5
```

---

## Working with Mock vs Real Data

### Current Status (Mock Data)
- ✅ 18 snapshots loaded
- ✅ 5 line movements to test thesis  
- ✅ API endpoints working
- ✅ Dashboard displays mock data

### Switching to Real Data

When BettingPros posts props (Thursday/Friday):

1. **Optional: Clear mock data**
   ```bash
   # Only removes mock data, keeps any real data you've collected
   uv run python scripts/load_mock_data.py --clear
   ```

2. **Start scraping**
   ```bash
   uv run python scripts/run_scraper.py
   ```

3. **Mix both** (if you want)
   - Mock data has event_id starting with "mock_"
   - Real data has normal event_ids
   - You can keep both in the database

---

## What Happens Next (With Mock Data)

In a new terminal:
```bash
cd frontend
yarn install
yarn dev
```

Visit http://localhost:3000 to see the dashboard.

---

## What Happens Next?

### Week 1-2: Data Collection
- Scraper runs automatically on game days
- Data accumulates in your database
- You can monitor via API endpoints

### Week 3-4: Initial Analysis
- Enough data to detect patterns
- Run statistical tests
- View preliminary results

### Week 6-8: Thesis Validation
- Statistical significance achieved
- Clear answer to your hypothesis
- Generate comprehensive reports

---

## Key Commands Reference

```bash
# Check if scraper would find games
uv run python scripts/run_scraper.py --dry-run

# Run scraper once (manual)
uv run python scripts/run_scraper.py

# Start backend with scheduler (automatic)
uv run uvicorn src.api.main:app --reload

# Check database
docker-compose ps

# View logs
docker-compose logs postgres -f

# Stop everything
docker-compose down
```

---

## Expected Results

### After First Run
- PropLineSnapshot records in database
- One snapshot per player per prop type
- Timestamp showing when data was collected

### After One Game Day
- 12-20 snapshots per player (every 5 min for 1-2 hours)
- Data for ~100-150 players (RB/WR across all games)
- Line movement trends visible

### After One Week (14 games)
- 2000+ snapshots
- Data for ~200 unique players
- Enough to start seeing patterns

---

## Troubleshooting

### "No players in scraping window"
- Games might be too far away (>12 hours)
- Try: `--hours-before-kickoff 24` to expand window
- Check ESPN for upcoming game times

### "No snapshots collected"
- BettingPros pages might not exist yet
- Props usually appear 24-48 hours before games
- Try again closer to game time

### Database connection error
```bash
docker-compose down
docker-compose up -d
# Wait 10 seconds for startup
uv run alembic upgrade head
```

### Scheduler not running
- Check that uvicorn started successfully
- Look for "Scheduler started" in logs
- Verify it's a game day (Sun/Mon/Thu/Sat)

---

## Success Indicators

✅ Scraper runs without errors  
✅ Database shows new PropLineSnapshot records  
✅ API returns data when queried  
✅ Timestamps are recent (within last 5-10 minutes)  
✅ Multiple snapshots per player (showing line movement)  

---

## What's Your Thesis Again?

> **Large drops in yardage prop lines close to kickoff (within 3 hours) correlate with players going UNDER their prop line.**

### How This System Tests It

1. **Collect**: Scrape prop lines every 5 minutes before games
2. **Detect**: Identify significant line drops (>10% or >5 yards)
3. **Track**: Record when drops occur (hours before kickoff)
4. **Compare**: Get actual game results (rushing/receiving yards)
5. **Analyze**: Calculate under rate for players with line drops
6. **Conclude**: Statistical test shows if correlation is significant

---

## Ready? Let's Go!

```bash
# Start collecting data now
uv run uvicorn src.api.main:app --reload
```

Then wait for game day (or test with upcoming games if within 12 hours).

**Good luck with your analysis! 🏈📊**

---

## Need Help?

- **Setup**: See `README.md`
- **Data sources**: See `API_DATA_SOURCES.md`  
- **Collection status**: See `DATA_COLLECTION_SUMMARY.md`
- **BettingPros details**: See `SCRAPER_UPDATE_NOTES.md`

