# Historical Data Collection Guide

## Overview

This project includes a CLI tool to fetch historical NFL player prop data from The Odds API. This data is essential for backtesting your thesis about prop line movements and player performance.

## Prerequisites

### 1. The Odds API Account
- **Website**: https://the-odds-api.com/
- **Required Plan**: Historical data requires a **paid subscription**
- **Free tier**: Only provides live/upcoming odds, not historical data

### 2. API Key Setup
Add your API key to `.env`:
```bash
ODDS_API_KEY=your_api_key_here
```

## Usage

### Basic Commands

#### Fetch a Specific Week
```bash
uv run python scripts/fetch_historical_data.py --start 2024-12-17 --end 2024-12-23
```

#### Fetch a Single Day
```bash
uv run python scripts/fetch_historical_data.py --date 2024-12-20
```

#### Dry Run (Test Without Saving)
```bash
uv run python scripts/fetch_historical_data.py --date 2024-12-20 --dry-run
```

### Advanced Options

#### More Granular Snapshots (15-minute intervals)
By default, the script collects snapshots every 30 minutes. For more granular data:
```bash
uv run python scripts/fetch_historical_data.py \
  --start 2024-12-17 \
  --end 2024-12-23 \
  --interval 15
```

⚠️ **Warning**: More frequent snapshots = more API calls = higher cost

#### Extended Time Window (24 hours before kickoff)
By default, snapshots start 12 hours before kickoff. To capture earlier line movements:
```bash
uv run python scripts/fetch_historical_data.py \
  --start 2024-12-17 \
  --end 2024-12-23 \
  --hours-before 24
```

#### Verbose Logging
```bash
uv run python scripts/fetch_historical_data.py --date 2024-12-20 --verbose
```

## What Data Gets Collected

### Events
- All NFL games within the specified date range
- Game times, teams, event IDs

### Player Props
For each game, collects:
- **Rushing yards** props (`player_rush_yds`)
- **Receiving yards** props (`player_reception_yds`)

### Sportsbooks
Lines from multiple sportsbooks:
- DraftKings
- FanDuel
- BetMGM
- Caesars (William Hill)
- PointsBet

Plus a **consensus line** (average across all books)

### Snapshot Times
Multiple snapshots leading up to each game:
- **Default**: Every 30 minutes for 12 hours before kickoff
- **Configurable**: Adjust with `--interval` and `--hours-before`

## Example Output

```
======================================================================
Fetching Historical Player Prop Data from The Odds API
======================================================================

Date Range: 2024-12-17 to 2024-12-23
Snapshot Window: 12 hours before kickoff
Snapshot Interval: 30 minutes

======================================================================

1. Fetching events from The Odds API...
   ✓ Found 14 events from API
   ✓ 14 events within date range

2. Events to process:
   1. Minnesota Vikings @ Seattle Seahawks
      Game Time: 2024-12-22 21:25:00+00:00
      Event ID: abc123...
   2. Tampa Bay Buccaneers @ Dallas Cowboys
      Game Time: 2024-12-23 01:20:00+00:00
      Event ID: def456...
   ...

3. Collecting prop snapshots...

   Processing event 1/14
   Minnesota Vikings @ Seattle Seahawks
   → Fetching 24 snapshots...
   ✓ Collected 156 prop snapshots

   Processing event 2/14
   Tampa Bay Buccaneers @ Dallas Cowboys
   → Fetching 24 snapshots...
   ✓ Collected 142 prop snapshots

======================================================================
4. Collection Summary
======================================================================

Total snapshots collected: 2,184
Unique players: 168
Rushing yards props: 1,092
Receiving yards props: 1,092

Sample snapshots:
  - Christian McCaffrey: rushing_yards
    Consensus: 82.5, DK: 82.5, FD: 83.5
    Time: 2024-12-22 09:25:00+00:00 (12.0h before kickoff)
  - Justin Jefferson: receiving_yards
    Consensus: 75.5, DK: 75.5, FD: 76.5
    Time: 2024-12-22 09:25:00+00:00 (12.0h before kickoff)
  ... and 2,179 more

5. Saving to database...
   ✓ Saved 2,184 snapshots to database

======================================================================
✓ Done!
======================================================================
```

## Cost Considerations

### API Usage
The Odds API charges based on:
- Number of requests
- Amount of historical data accessed

### Calculating Costs

**Per Game:**
- Default (24 snapshots × 12 hours): ~24 API calls
- More granular (48 snapshots × 12 hours @ 15min): ~48 API calls
- Extended window (48 snapshots × 24 hours @ 30min): ~48 API calls

**Per Week:**
- Average 14-16 NFL games/week
- Default: ~336-384 API calls/week
- With all games in a season: ~5,000-6,000 API calls

**Recommendation**: Start with a single day (`--dry-run`) to estimate costs before fetching full weeks.

## Data Structure

Each snapshot saved to the database contains:

```python
PropLineSnapshot:
    event_id: str              # Unique game identifier
    game_commence_time: datetime  # When the game starts
    home_team: str             # Home team name
    away_team: str             # Away team name
    player_name: str           # Player full name
    prop_type: PropType        # rushing_yards or receiving_yards
    
    # Lines from different sportsbooks
    consensus_line: Decimal    # Average across all books
    draftkings_line: Decimal
    fanduel_line: Decimal
    betmgm_line: Decimal
    caesars_line: Decimal
    pointsbet_line: Decimal
    
    # Metadata
    snapshot_time: datetime    # When this snapshot was taken
    source_timestamp: datetime # Timestamp from API
    hours_before_kickoff: Decimal  # Time until game
    source: DataSource         # ODDS_API
    raw_data: JSON             # Full API response
```

## Troubleshooting

### "The Odds API key not configured!"
**Solution**: Add your API key to `.env`:
```bash
ODDS_API_KEY=your_actual_api_key_here
```

### "No events data returned from API"
**Causes**:
- Invalid API key
- Date is outside available historical range
- No games scheduled for that date

**Solution**:
- Verify API key is correct
- Check The Odds API dashboard for data availability
- Try a date during NFL regular season

### "No prop data collected"
**Causes**:
- Games are too old (outside The Odds API's retention)
- Player props weren't available for those games
- API plan doesn't include player props

**Solution**:
- Use more recent dates
- Verify your API plan includes player prop markets
- Check The Odds API documentation for market availability

### Rate Limiting
If you encounter rate limiting:
```bash
# The script includes built-in delays:
# - 0.5s between snapshots
# - 1.0s between events
```

For very large data pulls, consider:
- Breaking into smaller date ranges
- Using longer intervals
- Fetching fewer hours before kickoff

## Best Practices

### 1. Start Small
```bash
# Test with a single day first
uv run python scripts/fetch_historical_data.py --date 2024-12-20 --dry-run
```

### 2. Strategic Date Selection
Focus on key periods for your analysis:
- **Regular season weeks**: September - December
- **Playoff games**: January
- **Primetime games**: Thursday/Sunday/Monday nights

### 3. Incremental Collection
Fetch one week at a time:
```bash
# Week 1
uv run python scripts/fetch_historical_data.py --start 2024-09-05 --end 2024-09-11

# Week 2
uv run python scripts/fetch_historical_data.py --start 2024-09-12 --end 2024-09-18

# ... etc
```

### 4. Monitor Your Usage
Check The Odds API dashboard regularly to track:
- API calls made
- Remaining quota
- Costs incurred

## Automation

### Create a Collection Script
For systematic historical data collection:

```bash
#!/bin/bash
# collect_season.sh

# Define weeks (example for 2024 season)
WEEKS=(
  "2024-09-05:2024-09-11"  # Week 1
  "2024-09-12:2024-09-18"  # Week 2
  "2024-09-19:2024-09-25"  # Week 3
  # ... add more weeks
)

for week in "${WEEKS[@]}"; do
  START="${week%%:*}"
  END="${week##*:}"
  
  echo "Fetching week: $START to $END"
  uv run python scripts/fetch_historical_data.py --start "$START" --end "$END"
  
  # Optional: pause between weeks to avoid rate limits
  sleep 5
done
```

## Next Steps

After collecting historical data:

1. **Verify data quality**:
   ```sql
   SELECT COUNT(*), player_name, prop_type 
   FROM prop_line_snapshots 
   WHERE source = 'odds_api'
   GROUP BY player_name, prop_type
   LIMIT 10;
   ```

2. **Run analysis**:
   ```bash
   uv run python scripts/run_analysis.py
   ```

3. **Generate reports**:
   - Access the web dashboard at http://localhost:3000
   - View line movement patterns
   - Analyze correlations

## Related Documentation

- [README.md](README.md) - Project overview
- [SCRAPER_UPDATE_NOTES.md](SCRAPER_UPDATE_NOTES.md) - BettingPros API details
- [EVENT_ID_MAPPING_STATUS.md](EVENT_ID_MAPPING_STATUS.md) - Event mapping implementation

## Support

- **The Odds API Docs**: https://the-odds-api.com/liveapi/guides/
- **Historical Data Info**: https://the-odds-api.com/historical-odds-data/
- **API Support**: support@the-odds-api.com

