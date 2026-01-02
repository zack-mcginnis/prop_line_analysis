# Frontend Dashboard Guide

## Overview

The frontend has been simplified to a single, focused **Line Movement Dashboard** that shows prop line changes across multiple time windows.

## What It Shows

### Main View: Line Movement Table

For every active prop (player + prop type), you can see:

1. **Player Name & Prop Type** (Rushing/Receiving Yards)
2. **Current Line** (latest consensus value)
3. **Line Changes** across time windows:
   - 5 minutes ago
   - 10 minutes ago
   - 15 minutes ago
   - 30 minutes ago
   - 45 minutes ago
   - 60 minutes ago
4. **Hours to Kickoff** (how long until the game starts)

## Key Features

### 📊 Real-Time Updates
- Automatically refreshes every 30 seconds
- Manual refresh button available
- Live tracking badge in header

### 🎨 Visual Indicators
- **Red** = Line drops (negative change)
- **Green** = Line increases (positive change)
- **Highlighted** = Significant movements (≥5% change)
- **Faded** = Minor movements (<5% change)

### 🔍 Sorting
Click any column header to sort:
- **Player** - Alphabetical
- **Current** - Current line value
- **5min, 10min, etc.** - Percentage change in that window
- **To Kickoff** - Hours until game starts

Click again to reverse sort direction.

### 🎯 Filtering
- **All** - Show all props
- **Rushing** - Only rushing yards
- **Receiving** - Only receiving yards

## How Line Changes Are Calculated

For each time window (e.g., 5 minutes):

1. Take the current snapshot time
2. Look back 5 minutes
3. Find the closest snapshot to that time
4. Calculate the difference:
   - **Absolute**: Current line - Old line (in yards)
   - **Percentage**: (Change / Old line) × 100%

## Example Usage

### Spot Sharp Drops
1. Sort by "5min" column (descending)
2. Look for **red highlighted** values
3. These are the sharpest recent drops
4. Perfect for thesis testing!

### Monitor Before Kickoff
1. Sort by "To Kickoff" column (ascending)
2. See which games are starting soon
3. Watch for late line movements
4. Catch significant drops within 3 hours

### Track Individual Players
1. Type player name in search (if implemented)
2. Or scroll to find them
3. See their line history across all time windows
4. Spot patterns in their movements

## Setup & Running

### 1. Install Dependencies

```bash
cd frontend
yarn install
```

### 2. Start Development Server

```bash
yarn dev
```

Runs on http://localhost:5173 (default Vite port)

### 3. Load Mock Data (For Testing)

From the project root:
```bash
uv run python scripts/load_mock_data.py
```

This loads 7 players with realistic line movements.

### 4. Start Backend

```bash
uv run uvicorn src.api.main:app --reload
```

The frontend expects the API at `/api/*` (proxy configured in vite.config.ts)

## Expected Output with Mock Data

After loading mock data, you should see:

| Player | Current | 5min | 10min | 15min | 30min | 45min | 60min | To Kickoff |
|--------|---------|------|-------|-------|-------|-------|-------|------------|
| Bucky Irving | 77.5 | — | — | — | — | -8.0<br>-9.4% | — | 2.0h |
| Christian McCaffrey | 91.5 | — | — | — | — | -7.0<br>-7.1% | — | 2.0h |
| Tyreek Hill | 79.5 | — | — | — | — | -8.0<br>-9.1% | — | 2.0h |
| CeeDee Lamb | 85.5 | — | — | -6.0<br>-6.6% | — | — | — | 2.0h |

*Note: Mock data has limited snapshots, so not all time windows will show changes*

## With Live Data

Once you start scraping real data every 5 minutes, you'll see:

- **All time windows populated** (5min through 60min)
- **Gradual line movements** showing trends
- **Sudden spikes** indicating sharp changes
- **Real-time updates** as new data comes in

## Color-Coded Examples

### Significant Drop (Tests Thesis! 🎯)
```
Player: Bucky Irving
Current: 77.5

30min: -8.0 yards
       -9.4%
🔴 (Red background, bold)
```

### Minor Change
```
Player: Derrick Henry  
Current: 91.5

30min: -1.0 yards
       -1.1%
(Muted red, no highlight)
```

### Significant Increase
```
Player: Jahmyr Gibbs
Current: 74.5

60min: +6.0 yards
       +8.8%
🟢 (Green background, bold)
```

## Benefits of This Design

✅ **Simple & Focused** - One view, all the info you need  
✅ **Sortable** - Quickly find the sharpest movements  
✅ **Real-Time** - Auto-refresh keeps data current  
✅ **Visual** - Color coding makes trends obvious  
✅ **Filterable** - Focus on rushing or receiving  
✅ **Responsive** - Works on desktop and tablets  
✅ **Fast** - Calculates changes client-side  

## Perfect For Your Thesis

This dashboard is designed to help you:

1. **Identify sharp drops** within your thesis window (3 hours)
2. **Track line movements** leading up to kickoff
3. **Spot patterns** across multiple time windows
4. **Monitor in real-time** on game days

Sort by any time window to find the sharpest changes, then verify if those players went under their line!

## Troubleshooting

### "No prop data available"
- Load mock data: `uv run python scripts/load_mock_data.py`
- Start scraping: `uv run python scripts/run_scraper.py`
- Check backend is running: http://localhost:8000/docs

### Time windows show "—"
- Not enough snapshots yet
- Mock data has limited time points
- Wait for 5+ minutes of live scraping

### Changes seem wrong
- Check snapshot times in database
- Verify scraper is running every 5 minutes
- Look at raw data: `curl http://localhost:8000/api/props/snapshots | jq`

### Slow to load
- Limit page_size in API call (currently 100)
- Add pagination if you have 100+ active props
- Consider filtering by upcoming games only

## Next Steps

### Future Enhancements

1. **Charts** - Add line graph showing movement over time
2. **Alerts** - Notification when drop exceeds threshold
3. **Player Details** - Click row to see full history
4. **Export** - Download data as CSV
5. **Filters** - By team, game time, drop threshold
6. **Compare** - Side-by-side player comparison

### For Production

1. Add authentication
2. Add error boundaries
3. Implement retry logic
4. Add loading skeletons
5. Handle API errors gracefully
6. Add unit tests

---

## Summary

**One dashboard. All the line movement data you need.**

- 7 time windows (5min to 60min)
- Color-coded changes
- Sortable columns
- Auto-refresh
- Perfect for spotting thesis scenarios

**Start using it:**
```bash
# Load mock data
uv run python scripts/load_mock_data.py

# Start backend
uv run uvicorn src.api.main:app --reload

# Start frontend
cd frontend && yarn dev

# Visit http://localhost:5173
```

🏈 Happy prop tracking!

