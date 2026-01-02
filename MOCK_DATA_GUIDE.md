# Mock Data Testing Guide

## Overview

Since BettingPros only keeps prop data for upcoming games (24-48h before kickoff), we've created a comprehensive mock data system for testing and development.

## What's Included

### Mock Data File: `mock_data/prop_snapshots.json`

**7 realistic player scenarios** across different situations:

| Player | Scenario | Thesis Test |
|--------|----------|-------------|
| **Bucky Irving** | Large drop (8 yards, 9.4%) at 2h before kickoff → Goes under | ✅ Positive |
| **Saquon Barkley** | Early drop (7 yards) at 36h, stable within 3h → Goes over | ⚠️ Control |
| **Derrick Henry** | Stable line (-1 yard) throughout → Goes over | ⚠️ Control |
| **Jahmyr Gibbs** | Line increases (+6 yards) late → Goes over | ❌ Inverse |
| **Christian McCaffrey** | Late drop (7 yards, 7.1%) at 2h → Goes under | ✅ Positive |
| **Tyreek Hill** | Late drop (8 yards, 9.1%) receiving → Goes under | ✅ Positive |
| **CeeDee Lamb** | Late drop (7 yards, 7.6%) receiving → Goes under | ✅ Positive |

**18 total snapshots** showing line movements over time

**5 significant late drops** within 3 hours of kickoff (your thesis window)

---

## Quick Start

### 1. Load Mock Data

```bash
# Load into database
uv run python scripts/load_mock_data.py
```

**Output:**
```
📊 Mock Data Scenarios:
   • Bucky Irving - Large line drop 2h before kickoff, player goes under
   • Saquon Barkley - Early line drop (48h before), stabilizes later
   • Derrick Henry - Line stays stable throughout
   • Jahmyr Gibbs - Line increases close to kickoff

📈 Mock Data Summary:
   Total snapshots: 18
   Unique players: 7
   Unique games: 7
   Rushing props: 13
   Receiving props: 5

🔽 Line Movements to Test Thesis:
   Found 5 significant late drops (tests thesis)

✅ Mock data loaded successfully!
```

### 2. Start Backend

```bash
uv run uvicorn src.api.main:app --reload
```

### 3. Test API Endpoints

```bash
# View all snapshots
curl http://localhost:8000/api/props/snapshots | jq

# View line movements (should show 5 movements)
curl "http://localhost:8000/api/movements/?min_drop_yards=5" | jq

# View specific player
curl "http://localhost:8000/api/props/snapshots?player_name=Bucky Irving" | jq

# Get analysis summary (once implemented)
curl http://localhost:8000/api/analysis/thesis-summary | jq
```

### 4. Start Dashboard

```bash
cd frontend
yarn dev
```

Visit http://localhost:3000 to see visualizations

---

## Understanding the Mock Data

### Scenario 1: Bucky Irving (Thesis Positive ✅)

**Timeline:**
- 48h before: 85.5 yards
- 24h before: 84.0 yards (small drop)
- 2h before: **77.5 yards** (dropped 8 yards = 9.4%)

**Result:** 62 rushing yards (UNDER by 15.5 yards)

**This tests your thesis:** Large late drop → Player goes under

### Scenario 2: Saquon Barkley (Control ⚠️)

**Timeline:**
- 48h before: 95.5 yards
- 36h before: 88.5 yards (early drop of 7 yards)
- 2h before: 88.5 yards (stable within 3h window)

**Result:** 102 rushing yards (OVER by 13.5 yards)

**This is a control:** Early drop but stable late → Player goes over

### Scenario 3: Derrick Henry (Control ⚠️)

**Timeline:**
- 48h before: 92.5 yards
- 24h before: 92.0 yards
- 2h before: 91.5 yards (minimal movement)

**Result:** 98 rushing yards (OVER by 6.5 yards)

**This is a control:** No significant movement → Player goes over

### Scenario 4: Jahmyr Gibbs (Inverse ❌)

**Timeline:**
- 48h before: 68.5 yards
- 2h before: **74.5 yards** (increased 6 yards)

**Result:** 89 rushing yards (OVER by 14.5 yards)

**This is the inverse:** Line increase → Player goes way over

---

## Command Options

### Basic Usage

```bash
# Load mock data
uv run python scripts/load_mock_data.py
```

### Clear Existing Data

```bash
# Remove old mock data and reload
uv run python scripts/load_mock_data.py --clear
```

This only removes mock data (event_id starting with "mock_"). Real scraped data is preserved.

### Dry Run

```bash
# Preview without saving to database
uv run python scripts/load_mock_data.py --dry-run
```

Shows what would be loaded and calculates statistics without touching the database.

---

## Customizing Mock Data

### Edit `mock_data/prop_snapshots.json`

The JSON structure is straightforward:

```json
{
  "snapshots": [
    {
      "event_id": "mock_game_001",
      "game_commence_time": "2025-01-05T18:00:00Z",
      "home_team": "Tampa Bay Buccaneers",
      "away_team": "Carolina Panthers",
      "player_name": "Bucky Irving",
      "player_slug": "bucky-irving",
      "prop_type": "rushing_yards",
      "snapshots_timeline": [
        {
          "snapshot_time": "2025-01-03T18:00:00Z",
          "hours_before_kickoff": 48.0,
          "consensus_line": 85.5,
          "draftkings_line": 85.0,
          "fanduel_line": 86.0,
          "betmgm_line": 85.5,
          "caesars_line": 86.0,
          "pointsbet_line": 85.0
        },
        {
          "snapshot_time": "2025-01-05T16:00:00Z",
          "hours_before_kickoff": 2.0,
          "consensus_line": 77.5,
          "draftkings_line": 77.0,
          "fanduel_line": 78.0,
          "betmgm_line": 77.5,
          "_note": "SIGNIFICANT DROP: -8 yards"
        }
      ],
      "actual_result": {
        "rushing_yards": 62,
        "went_under": true,
        "final_line": 77.5
      }
    }
  ]
}
```

### Add Your Own Scenarios

1. Copy an existing player block
2. Change the player name, slug, and event_id
3. Adjust the timeline snapshots
4. Set the actual_result
5. Reload: `uv run python scripts/load_mock_data.py --clear`

### Tips for Realistic Mock Data

- **Consensus lines** should be close to the average of individual books
- **Individual book lines** typically vary by 0.5-2.0 yards
- **Line movements** usually happen in 0.5-1.0 yard increments
- **Significant drops** are typically 5-10 yards (5-12%)
- **Game times** should be realistic (Sunday 1pm, 4pm, 8:20pm ET, etc.)

---

## What You Can Test

### ✅ Fully Testable with Mock Data

- **API Endpoints**
  - Get snapshots
  - Filter by player, team, prop type
  - Pagination
  - Sorting

- **Line Movement Detection**
  - Identify drops >5 yards or >10%
  - Calculate hours before kickoff
  - Track multiple snapshots per player

- **Statistical Analysis**
  - Under rate for players with late drops
  - Control group (stable lines)
  - Chi-square significance testing

- **Dashboard Visualizations**
  - Line movement charts
  - Player cards
  - Summary statistics
  - Under/over indicators

### ⏳ Need Real Data For

- **Actual scraping logic** (wait for live props)
- **Real sportsbook variations** (mock uses simplified data)
- **Rate limiting behavior** (no API calls with mock data)
- **BettingPros API changes** (mock is based on current format)

---

## Verification Steps

### 1. Check Data Loaded

```bash
# Should show 18 snapshots
curl http://localhost:8000/api/props/snapshots | jq 'length'

# Should show 7 unique players
curl http://localhost:8000/api/props/snapshots | jq '[.[].player_name] | unique | length'
```

### 2. Verify Line Movements

```bash
# Should show 5 significant movements
curl "http://localhost:8000/api/movements/?min_drop_yards=5" | jq 'length'

# Check Bucky Irving specifically (should show 8-yard drop)
curl "http://localhost:8000/api/movements/" | jq '.[] | select(.player_name == "Bucky Irving")'
```

### 3. Test Thesis

According to your thesis, the 5 players with late significant drops should have a high under rate:

- Bucky Irving: UNDER ✅
- Saquon Barkley: UNDER ✅ (but drop was early, so control)
- Christian McCaffrey: UNDER ✅
- Tyreek Hill: UNDER ✅
- CeeDee Lamb: UNDER ✅

**Expected result:** 4 out of 4 late drops went under (100% - small sample)

Control group (Derrick Henry, Jahmyr Gibbs) went OVER.

---

## Troubleshooting

### "No such file or directory: mock_data/prop_snapshots.json"

Make sure you're running from the project root:
```bash
cd /Users/zackimous/code/prop_line_analysis
uv run python scripts/load_mock_data.py
```

### "Database connection failed"

Start Docker containers:
```bash
docker-compose up -d
```

### Mock data not appearing in API

1. Check database:
   ```bash
   docker exec -it prop_analysis_db psql -U postgres -d prop_analysis
   ```
   
2. Query:
   ```sql
   SELECT COUNT(*) FROM prop_line_snapshots WHERE event_id LIKE 'mock_%';
   ```

3. Should show 18 rows

### Clear all data (including real data)

```bash
# WARNING: This deletes ALL snapshots, not just mock data
docker-compose down -v
docker-compose up -d
uv run alembic upgrade head
uv run python scripts/load_mock_data.py
```

---

## Next Steps After Loading Mock Data

### 1. Test API (5 minutes)

```bash
# Terminal 1: Start backend
uv run uvicorn src.api.main:app --reload

# Terminal 2: Test endpoints
curl http://localhost:8000/api/props/snapshots | jq
curl http://localhost:8000/api/movements/ | jq
```

### 2. Test Dashboard (10 minutes)

```bash
cd frontend
yarn dev
# Visit http://localhost:3000
```

Verify you can see:
- Player cards
- Line movement charts
- Under/over indicators
- Summary statistics

### 3. Implement Analysis (30 minutes)

If not already implemented, create analysis endpoints that:
- Calculate under rate for players with late drops
- Compare to control group
- Run statistical significance tests
- Generate thesis validation report

### 4. Wait for Real Data (Thursday/Friday)

Once BettingPros posts Week 18 props:
```bash
# Remove mock data
uv run python scripts/load_mock_data.py --clear
# (This only removes mock data)

# Start scraping real data
uv run python scripts/run_scraper.py
```

---

## Benefits of Mock Data

✅ **Immediate testing** - Don't wait for game day  
✅ **Controlled scenarios** - Test edge cases  
✅ **Thesis validation** - Verify analysis logic  
✅ **Frontend development** - Build UI with real-looking data  
✅ **API testing** - Ensure endpoints work correctly  
✅ **Documentation** - Screenshots and examples  
✅ **Demo ready** - Show the system working  

---

## Summary

**Mock data is perfect for:**
- Development and testing (Now)
- Verifying your system works (Now)
- Building the frontend (Now)
- Testing analysis logic (Now)

**Real data is needed for:**
- Actual thesis validation (Game day)
- Production use (Season)
- Real-world edge cases (Over time)

**You can use both:**
- Mock data: Development and testing
- Real data: Production and thesis validation

Start with mock data today, switch to real data on game day! 🏈📊

