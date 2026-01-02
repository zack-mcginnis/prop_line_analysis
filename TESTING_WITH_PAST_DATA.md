# Testing the Scraper with Past Week Data

## The Challenge

You want to test the scraper with Week 17 data, but BettingPros has a key limitation:

**BettingPros only keeps prop data for upcoming games.** Once games finish, the prop data is removed from their API.

## What We Found

### Week 17 (Just Finished)
```bash
uv run python scripts/run_scraper.py --week 17 --hours-before-kickoff 168
```

**Result:** 
- ✅ ESPN found 16 games (all STATUS_FINAL)
- ❌ BettingPros has 0 events (data removed after games finished)
- ❌ No players to scrape

### Week 18 (Current Week, Early)
```bash
uv run python scripts/run_scraper.py --week 18 --hours-before-kickoff 200
```

**Result:**
- ✅ ESPN found games
- ✅ BettingPros events matched
- ✅ Players discovered
- ❌ No prop data posted yet (too early in the week)

## BettingPros Data Availability Window

```
Game Schedule Timeline:
├─ Monday-Wednesday: No prop data available
├─ Thursday: Props start appearing (sometimes)
├─ Friday-Saturday: Most props available (24-48h before game)
├─ Sunday morning: All props available
├─ During game: Props may update
└─ After game: Props removed within hours
```

**Key Finding:** BettingPros typically posts props **24-48 hours before kickoff**.

---

## Alternative Testing Approaches

Since you can't test with historical data from BettingPros, here are your options:

### Option 1: Wait for Props to Post (Recommended)

**Best for:** Realistic testing with actual data

Wait until Thursday/Friday of Week 18, then run:
```bash
uv run python scripts/run_scraper.py --dry-run
```

**Why this works:**
- Props will be available
- You'll see real consensus lines
- Can verify scraper works correctly
- Can test database storage

### Option 2: Mock Data Testing

**Best for:** Development without waiting

Create a test script with mock data:

```python
# scripts/test_with_mock_data.py
from decimal import Decimal
from datetime import datetime, timezone
from src.models.database import PropLineSnapshot, PropType, DataSource, get_session

# Create mock snapshots
snapshots = [
    PropLineSnapshot(
        event_id="test_401772825",
        game_commence_time=datetime(2025, 1, 5, 18, 0, tzinfo=timezone.utc),
        home_team="Tampa Bay Buccaneers",
        away_team="Carolina Panthers",
        player_name="Bucky Irving",
        player_slug="bucky-irving",
        prop_type=PropType.RUSHING_YARDS,
        consensus_line=Decimal("85.5"),
        draftkings_line=Decimal("85.0"),
        fanduel_line=Decimal("86.0"),
        betmgm_line=Decimal("85.5"),
        snapshot_time=datetime.now(timezone.utc),
        source_timestamp=datetime.now(timezone.utc),
        hours_before_kickoff=Decimal("48.5"),
        source=DataSource.BETTINGPROS,
    ),
    PropLineSnapshot(
        event_id="test_401772825",
        game_commence_time=datetime(2025, 1, 5, 18, 0, tzinfo=timezone.utc),
        home_team="Tampa Bay Buccaneers",
        away_team="Carolina Panthers",
        player_name="Bucky Irving",
        player_slug="bucky-irving",
        prop_type=PropType.RUSHING_YARDS,
        consensus_line=Decimal("78.5"),  # Dropped 7 yards
        draftkings_line=Decimal("78.0"),
        fanduel_line=Decimal("79.0"),
        betmgm_line=Decimal("78.5"),
        snapshot_time=datetime.now(timezone.utc),
        source_timestamp=datetime.now(timezone.utc),
        hours_before_kickoff=Decimal("2.5"),  # Within 3 hours of kickoff
        source=DataSource.BETTINGPROS,
    ),
]

# Save to database
session = get_session()
session.add_all(snapshots)
session.commit()
session.close()

print(f"✓ Created {len(snapshots)} mock snapshots for testing")
```

Then test your API endpoints and analysis:
```bash
uv run python scripts/test_with_mock_data.py
curl http://localhost:8000/api/movements/?min_drop_yards=5
```

### Option 3: Use Week 18 on Saturday Morning

**Best for:** Testing close to game time

On Saturday, January 4th (day before Week 18 games):
```bash
# Props should be available by now
uv run python scripts/run_scraper.py

# Run every hour to capture line movements
watch -n 3600 'uv run python scripts/run_scraper.py'
```

### Option 4: Manual URL Testing

**Best for:** Verifying BettingPros pages exist

Check if specific player pages have data:
```bash
# Check a star player's page
curl "https://api.bettingpros.com/v3/offers?market_id=107&event_id=BETTING_PROS_EVENT_ID"
```

Or visit directly:
```
https://www.bettingpros.com/nfl/props/saquon-barkley/rushing-yards/
```

If you see prop lines on the website, the scraper should work.

---

## Recommended Testing Timeline

### Now (Early Week)
- ✅ Test script runs without errors: `--dry-run`
- ✅ Test database connection
- ✅ Test with mock data (Option 2)
- ✅ Verify API endpoints work

### Thursday/Friday (Props Posted)
- ✅ Run real scraper: `uv run python scripts/run_scraper.py`
- ✅ Verify data saves to database
- ✅ Check API returns real data
- ✅ Test dashboard displays correctly

### Saturday (Day Before Games)
- ✅ Run scraper every hour
- ✅ Observe line movements in real-time
- ✅ Verify movement detection works

### Sunday (Game Day)
- ✅ Let scheduler run automatically
- ✅ Monitor collection every 5 minutes
- ✅ Collect comprehensive dataset

### Monday (After Games)
- ✅ Fetch game results from ESPN
- ✅ Calculate over/under outcomes
- ✅ Run initial analysis

---

## Why This Matters

**For your thesis**, you need:
1. **Line snapshots** leading up to kickoff (multiple per player)
2. **Line movements** detected (drops >10% or >5 yards)
3. **Timing data** (when drops occurred - hours before kickoff)
4. **Game results** (actual rushing/receiving yards)

**You can only get #1-3 from live data** because:
- BettingPros removes old data
- The Odds API historical data requires expensive plan
- No free historical player prop sources exist

**Best strategy:** Start collecting NOW (even if Week 18 props aren't up yet), and you'll have your own historical dataset going forward.

---

## Testing Checklist

### Without Live Props (Now)

- [ ] Run `--dry-run` successfully
- [ ] Verify database connection
- [ ] Check API documentation (/docs)
- [ ] Create mock data
- [ ] Test movement detection with mocks
- [ ] Test analysis endpoints with mocks
- [ ] Review frontend (even with no real data)

### With Live Props (Thursday+)

- [ ] Scrape real players
- [ ] Verify data in database
- [ ] See snapshots via API
- [ ] Observe line changes
- [ ] Detect movements
- [ ] Calculate hours_before_kickoff correctly

### Full Integration (Sunday)

- [ ] Scheduler runs automatically
- [ ] Collects every 5 minutes
- [ ] Multiple snapshots per player
- [ ] Line movements detected
- [ ] Results fetched post-game
- [ ] Over/under calculated
- [ ] Analysis statistically valid

---

## Current Status

**The `--week` parameter works!** But BettingPros data availability is the limiting factor:

- Week 17: ❌ Games finished, data removed
- Week 18: ⚠️ Games exist, props not posted yet (too early)
- Future weeks: ❌ Not scheduled yet

**Your options:**
1. Wait 2-3 days for Week 18 props to post
2. Use mock data for immediate testing
3. Build your own historical dataset starting this weekend

---

## Updated Script Usage

```bash
# Test script works (no data expected early in week)
uv run python scripts/run_scraper.py --week 18 --dry-run

# When props are available (Thu/Fri)
uv run python scripts/run_scraper.py

# Test with past week (won't find data, but tests discovery)
uv run python scripts/run_scraper.py --week 17 --hours-before-kickoff 168

# Verbose mode to see what's happening
uv run python scripts/run_scraper.py --week 18 --verbose
```

---

## Next Steps

**Immediate (Today):**
1. Create mock data script
2. Test API endpoints with mock data
3. Verify dashboard works with mock data

**Thursday/Friday:**
1. Check if Week 18 props are posted: https://www.bettingpros.com/nfl/props/
2. Run scraper with real data
3. Verify everything works end-to-end

**Saturday/Sunday:**
1. Start collecting real data
2. Begin building your historical dataset
3. Monitor for line movements

**Next Monday:**
1. Analyze first week of data
2. Refine system based on learnings
3. Prepare for rest of season

**You're set up correctly - just need to wait for props to be posted! 🏈**

