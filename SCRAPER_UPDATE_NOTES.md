# BettingPros Scraper API Update

## Summary

The BettingPros scraper has been updated to use their official API instead of HTML parsing. This is more reliable and provides structured data with all sportsbook lines including consensus.

## Changes Made

### 1. API Approach
- **Old**: Scraped HTML pages and parsed with BeautifulSoup
- **New**: Calls BettingPros API (`/v3/offers`) endpoint
- **Benefits**:
  - Structured JSON data
  - All sportsbook lines available (Consensus, DraftKings, FanDuel, BetMGM, Caesars, PointsBet)
  - Timestamps for each line
  - More reliable (no HTML structure changes to worry about)

### 2. API Details
- **Endpoint**: `https://api.bettingpros.com/v3/offers`
- **API Key**: `CHi8Hy5CEE4khd46XNYL23dCFX96oUdw6qOt1Dnh` (public key from site)
- **Market IDs**:
  - Receiving Yards: `105`
  - Rushing Yards: `107`
- **Required Parameters**: `market_id`, `event_id`

### 3. Code Changes
- Removed HTML parsing methods (`_parse_prop_page`, `_fetch_page`, etc.)
- Removed `beautifulsoup4` dependency from imports
- Added `_parse_api_offer()` method to parse API responses
- Updated `scrape_player_prop()` to use API endpoint
- Added sportsbook ID mappings

## Current Issue: Event ID Mapping

### Problem
The `PlayerDiscovery` module uses ESPN's API, which returns event IDs like `401772825`. However, BettingPros uses its own event ID system (e.g., `21583`). 

When we scrape with an ESPN event ID, the BettingPros API returns 0 offers because it doesn't recognize the event.

### Impact
- Manual scraping of specific players doesn't work currently
- Weekly scraping of all players won't work until event IDs are mapped

### Solution Options

#### Option 1: Update PlayerDiscovery to Fetch BettingPros Event IDs (Recommended)
Add a method to `PlayerDiscovery` to:
1. Get NFL games/events from BettingPros API (`/v3/events`)
2. Match them to ESPN games by team names and game time
3. Store both ESPN and BettingPros event IDs
4. Pass BettingPros event IDs to the scraper

```python
# Example API call to get BettingPros events:
GET https://api.bettingpros.com/v3/events?sport=NFL&season=2024-2025
```

#### Option 2: Create Event ID Mapping Table
- Store mappings between ESPN event IDs and BettingPros event IDs in the database
- Manually populate initially, auto-discover going forward

#### Option 3: Use BettingPros Events API Directly
- Replace ESPN as the source for discovering games/players
- Use BettingPros `/v3/events` and player lists directly

## Testing

### What Works
- ✅ API integration (correct endpoint, authentication, headers)
- ✅ Parsing API responses for prop lines
- ✅ Extracting consensus and sportsbook-specific lines
- ✅ Logging and error handling

### What Needs Event ID Fix
- ❌ Scraping specific players by name
- ❌ Weekly automated scraping

### Test Commands

Once event IDs are fixed:
```bash
# Scrape specific players
uv run python scripts/run_scraper.py --players "Drake London" "Saquon Barkley"

# Scrape all weekly players
uv run python scripts/run_scraper.py

# With verbose logging
uv run python scripts/run_scraper.py --verbose
```

## Next Steps

1. **Implement event ID mapping** (choose one of the options above)
2. **Test with live games** once NFL games are scheduled
3. **Consider adding retry logic** for API rate limiting
4. **Add database migration** if storing event ID mappings

## API Investigation Results

During investigation, we found:
- BettingPros embeds initial data in JavaScript (`playerPropAnalyzer` variable)
- The embedded data is for the page structure, not live prop lines
- Live prop lines are loaded via API after page render
- The API is public and doesn't require special authentication beyond the standard API key

## Files Modified

- `src/collectors/bettingpros.py` - Complete rewrite to use API
- `scripts/run_scraper.py` - Updated to use player discovery for event IDs
- `pyproject.toml` & `requirements.txt` - Added `httpx[http2]` for HTTP/2 support
- `scripts/debug_page_structure.py` - Created for investigation
- `scripts/test_api.py` - Created for API testing

