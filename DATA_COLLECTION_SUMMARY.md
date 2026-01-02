# Data Collection Summary

## Current Setup (Recommended)

### Primary Data Source: **BettingPros Scraper** ✅

This is your main tool for collecting live player prop odds data.

**Why BettingPros:**
- ✅ **Free** - No subscription costs
- ✅ **Works now** - Already implemented and tested
- ✅ **Consensus lines** - Averages from multiple sportsbooks
- ✅ **Sufficient for thesis** - Provides the data needed to test your hypothesis

**Usage:**
```bash
# Manual scraping during games
uv run python scripts/run_scraper.py --dry-run

# Scrape specific prop types
uv run python scripts/run_scraper.py --prop-type rushing
uv run python scripts/run_scraper.py --prop-type receiving

# Scrape specific players
uv run python scripts/run_scraper.py --players "Saquon Barkley" "Derrick Henry"
```

**Automated Collection:**
The scheduler automatically runs on game days when you start the backend:
```bash
uv run uvicorn src.api.main:app --reload
```

---

## Available Scripts

### ✅ Ready to Use

| Script | Purpose | Cost | Status |
|--------|---------|------|--------|
| `run_scraper.py` | BettingPros live scraper | Free | ✅ Working |
| `check_available_markets.py` | Check API access | Free | ✅ Working |

### ⏳ Future Use (Requires API Upgrade)

| Script | Purpose | Required Plan | Status |
|--------|---------|---------------|--------|
| `fetch_live_odds.py` | Live API props | Pro+ (~$100/mo) | ⚠️ Not available |
| `fetch_historical_data.py` | Historical API | Historical (~$200/mo) | ⚠️ Not available |

---

## Data Collection Strategy

### Phase 1: Current Season (Now)

**Use BettingPros exclusively** to build your dataset:

1. **Start the backend with scheduler:**
   ```bash
   uv run uvicorn src.api.main:app --reload
   ```

2. **Verify scraping is working:**
   ```bash
   uv run python scripts/run_scraper.py --dry-run --limit 3
   ```

3. **Let it collect data automatically** every 5 minutes on:
   - Sundays: 6am-midnight (all games)
   - Mondays: 4pm-midnight (MNF)
   - Thursdays: 4pm-midnight (TNF)
   - Saturdays: 12pm-midnight (late season)

4. **After 4-6 weeks**, you'll have enough data to:
   - Test your thesis
   - Calculate statistical significance
   - Generate meaningful insights

### Phase 2: Analysis (Mid-Season)

Once you have data:

1. **View movements via API:**
   ```bash
   curl http://localhost:8000/api/movements/?min_drop_yards=5
   ```

2. **Run statistical analysis:**
   ```bash
   curl http://localhost:8000/api/analysis/thesis-summary
   ```

3. **View dashboard:**
   - Open http://localhost:3000
   - See line movements, over/under rates, etc.

### Phase 3: Optional Upgrade (Future)

Only upgrade The Odds API if you need:
- Historical data from previous seasons
- More sportsbooks (30+ vs consensus)
- Professional-grade data quality
- Research/publication requirements

---

## Current API Status

Your The Odds API subscription:
- Plan: Basic/Standard
- Credits: 498/500 remaining
- Player Props: ❌ Not included
- Historical Data: ❌ Not included

**Recommendation:** Keep your current plan for emergencies, use BettingPros as primary source.

---

## Testing Your Setup

### 1. Check Database Connection
```bash
docker-compose ps
# Should show postgres running on port 5432
```

### 2. Test BettingPros Scraper
```bash
uv run python scripts/run_scraper.py --dry-run --limit 2
# Should show upcoming games and players
```

### 3. Verify Database Tables
```bash
uv run alembic upgrade head
# Should show all migrations applied
```

### 4. Start Backend
```bash
uv run uvicorn src.api.main:app --reload
# Visit http://localhost:8000/docs for API docs
```

### 5. Check Scheduler
The scheduler will log when it starts/stops scraping jobs. Look for:
```
INFO: Scheduler started
INFO: Game day job scheduled for Sunday at 06:00
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Collection Flow                     │
└─────────────────────────────────────────────────────────────┘

1. Game Day Detection
   └─> Scheduler activates on Sun/Mon/Thu/Sat

2. Player Discovery (ESPN API)
   └─> Find all RB/WR in upcoming games
   └─> Get BettingPros event IDs

3. BettingPros Scraping (Every 5 min)
   └─> Fetch prop lines for each player
   └─> Collect consensus + individual books
   └─> Store in PostgreSQL

4. Line Movement Detection
   └─> Compare snapshots over time
   └─> Flag significant drops (>10% or >5 yards)
   └─> Calculate hours before kickoff

5. Game Results (Post-game)
   └─> Fetch actual stats from ESPN
   └─> Determine over/under outcomes
   └─> Update database

6. Statistical Analysis
   └─> Calculate under rate by drop size
   └─> Run chi-square tests
   └─> Generate confidence intervals
```

---

## Success Metrics

### Week 1
- ✅ Scraper runs without errors
- ✅ Data populates in database
- ✅ Can view snapshots via API

### Week 4
- ✅ 30+ games worth of data
- ✅ Line movements detected
- ✅ Can analyze patterns

### Week 8
- ✅ Statistical significance achieved
- ✅ Thesis validated or disproved
- ✅ Dashboard shows meaningful insights

---

## Troubleshooting

### Scraper Returns No Data
```bash
# Check if games are upcoming
uv run python scripts/run_scraper.py --hours-before-kickoff 24

# Check BettingPros is accessible
curl https://www.bettingpros.com/nfl/props/
```

### Database Connection Failed
```bash
# Restart containers
docker-compose down
docker-compose up -d

# Verify connection
docker-compose logs postgres | tail -20
```

### Scheduler Not Running
```bash
# Check logs when starting backend
uv run uvicorn src.api.main:app --reload

# Should see "Scheduler started" message
```

---

## Next Steps

1. **✅ Done**: Environment set up
2. **✅ Done**: Database configured  
3. **✅ Done**: BettingPros scraper implemented
4. **✅ Done**: Documentation created

5. **➡️ Next**: Start collecting data
   ```bash
   # Start backend (includes scheduler)
   uv run uvicorn src.api.main:app --reload
   ```

6. **Then**: Monitor collection
   - Check database for new snapshots
   - Verify scraping logs
   - Test API endpoints

7. **After 4-6 weeks**: Analyze results
   - Run statistical analysis
   - Generate reports
   - Validate thesis

---

## Questions?

- **Setup issues**: Check `README.md`
- **API questions**: Check `API_DATA_SOURCES.md`
- **BettingPros**: Check `SCRAPER_UPDATE_NOTES.md`
- **Event mapping**: Check `EVENT_ID_MAPPING_STATUS.md`

**You're ready to start collecting data! 🚀**

