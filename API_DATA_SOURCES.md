# API Data Sources Guide

This document explains the different data sources available for collecting NFL player prop data and their requirements.

## Overview

There are two main ways to collect player prop data:

1. **BettingPros Scraper** (Free) - Real-time web scraping
2. **The Odds API** (Paid) - Professional API with historical data

## BettingPros Scraper (Recommended for Live Data)

### Pros
- ✅ **Free** - No subscription required
- ✅ **Consensus lines** - Averages from multiple sportsbooks
- ✅ **Real-time data** - Updated every few minutes
- ✅ **Works now** - No upgrade needed

### Cons
- ❌ No historical data
- ❌ Requires rate limiting/good citizenship
- ❌ Could break if website changes

### Usage

```bash
# Scrape current props for upcoming games
uv run python scripts/run_scraper.py --dry-run

# Scrape specific players
uv run python scripts/run_scraper.py --players "Saquon Barkley" "Derrick Henry"

# Scrape only rushing yards
uv run python scripts/run_scraper.py --prop-type rushing
```

### When to Use
- Collecting live/current prop data during the season
- Testing and development
- When API budget is limited
- Primary data source for real-time analysis

---

## The Odds API

### Subscription Tiers

The Odds API has different tiers with different capabilities:

#### Basic/Standard Plans (~$20-50/month)
- ✅ Live odds for basic markets (h2h, spreads, totals)
- ✅ 500-2000 requests/month
- ❌ **NO player props**
- ❌ **NO historical data**

#### Pro/Premium Plans (~$100+/month)
- ✅ Live odds for all markets
- ✅ **Player props included**
- ✅ More requests (5000+/month)
- ❌ **NO historical data** (unless specifically included)

#### Historical Data Plans (~$200+/month)
- ✅ All live odds features
- ✅ **Player props included**
- ✅ **Historical data access**
- ✅ Snapshots every 5 minutes
- ✅ Perfect for backtesting

### Current Subscription Status

Run this command to check what your plan includes:

```bash
uv run python scripts/check_available_markets.py
```

Your current plan appears to be **Basic/Standard**, which includes:
- ✅ 500 requests/month (498 remaining)
- ✅ Live odds for basic markets
- ❌ No live player props
- ❌ No historical data

### What Each Feature Enables

| Feature | Script | Status | Required Tier |
|---------|--------|--------|---------------|
| BettingPros scraping | `run_scraper.py` | ✅ Works | Free |
| Live player props | `fetch_live_odds.py` | ❌ Not available | Pro+ |
| Historical player props | `fetch_historical_data.py` | ❌ Not available | Historical |

---

## Recommended Setup

### For Current Season (Real-time Analysis)

**Use BettingPros Scraper** - It's free and works perfectly for live data:

```bash
# Run manually during games
uv run python scripts/run_scraper.py

# Or let the scheduler run automatically on game days
uv run uvicorn src.api.main:app --reload
```

The scheduler will automatically scrape props every 5 minutes on game days.

### For Historical Analysis (Backtesting)

You have two options:

#### Option A: Upgrade The Odds API (Recommended)
- Upgrade to a plan with historical data access
- Run: `uv run python scripts/fetch_historical_data.py --start 2024-12-01 --end 2024-12-31`
- Get comprehensive data from 30+ sportsbooks

#### Option B: Build Your Own Historical Data
- Use BettingPros scraper throughout the season
- Collect data every 5 minutes on game days
- After a few weeks, you'll have your own historical dataset

### Hybrid Approach (Best Value)

1. **During Season**: Use BettingPros scraper (free)
   - Collects live data automatically
   - Builds your own historical dataset over time

2. **Off-Season Analysis**: Consider upgrading for historical data
   - Fill in gaps from before you started collecting
   - Get data from previous seasons
   - Access professional-grade historical snapshots

---

## Cost Comparison

### BettingPros Only (Free)
- **Cost**: $0/month
- **Data**: Real-time consensus lines
- **History**: Only what you collect yourself
- **Best for**: Current season analysis, limited budget

### Basic API Plan (~$20/month)
- **Cost**: $20-50/month
- **Data**: Basic markets only (no player props)
- **Value**: ⚠️ Limited value for this project
- **Best for**: Not recommended for player prop analysis

### Pro API Plan (~$100/month)
- **Cost**: $100+/month
- **Data**: Live player props from 30+ books
- **History**: No historical data
- **Best for**: High-volume live data needs
- **Note**: BettingPros may be sufficient for most use cases

### Historical API Plan (~$200/month)
- **Cost**: $200+/month
- **Data**: Full historical + live player props
- **History**: Complete historical snapshots
- **Best for**: Serious backtesting, research, professional use

### Hybrid (Recommended)
- **Cost**: $0/month (current) → Optional upgrade later
- **Data**: Start with BettingPros, add API if needed
- **History**: Build your own dataset starting now
- **Best for**: Most users, especially when starting out

---

## Migration Path

### Phase 1: Now (Free)
```bash
# Start collecting with BettingPros
uv run python scripts/run_scraper.py
```
- Begin building your dataset
- Test your thesis with current games
- Learn the system

### Phase 2: Mid-Season (Optional)
If you need more data sources or want to validate BettingPros:
- Upgrade to Pro plan for live player props
- Compare data quality
- Decide if API is worth the cost

### Phase 3: Off-Season (Optional)
If you want comprehensive historical analysis:
- Upgrade to Historical plan
- Backfill previous seasons
- Run extensive backtests

---

## Scripts Reference

| Script | Purpose | Requirements | Cost |
|--------|---------|--------------|------|
| `check_available_markets.py` | Check API access | Any plan | Free |
| `run_scraper.py` | BettingPros scraper | None | Free |
| `fetch_live_odds.py` | Live API props | Pro+ plan | API credits |
| `fetch_historical_data.py` | Historical API | Historical plan | API credits |

---

## Frequently Asked Questions

### Can I use both BettingPros and The Odds API?
Yes! They complement each other:
- BettingPros: Real-time consensus
- The Odds API: Multi-book historical data

### Is BettingPros data accurate?
Yes, it provides consensus lines from major sportsbooks. For most analyses, it's perfectly sufficient.

### When should I upgrade to The Odds API?
Consider upgrading if:
- You need historical data for backtesting
- You want data from 30+ sportsbooks simultaneously
- You need professional-grade data for research/publication
- BettingPros rate limits become an issue

### Can I start with free and upgrade later?
Absolutely! That's the recommended approach. Build your dataset with BettingPros first, then upgrade only if you need more.

### How much historical data do I need?
For statistical significance:
- Minimum: 4-6 weeks (48+ games)
- Good: Full season (272 games)
- Excellent: Multiple seasons (500+ games)

Start collecting now and you'll have good data by mid-season.

---

## Support

- BettingPros: https://www.bettingpros.com/
- The Odds API: https://the-odds-api.com/
- The Odds API Docs: https://the-odds-api.com/liveapi/guides/v4/

## Next Steps

1. **Run the diagnostic**:
   ```bash
   uv run python scripts/check_available_markets.py
   ```

2. **Start collecting data today** (free):
   ```bash
   uv run python scripts/run_scraper.py --dry-run
   ```

3. **Review your needs** in 2-4 weeks
   - Do you have enough data?
   - Do you need historical data?
   - Is BettingPros sufficient?

4. **Upgrade only if needed**
   - Visit https://the-odds-api.com/
   - Choose appropriate tier
   - Update your `.env` with new API key

