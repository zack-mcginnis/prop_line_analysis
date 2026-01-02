# Prop Line Movement Analysis

A full-stack application for analyzing NFL player prop line movements and their correlation with game performance.

## Thesis

> Large drops in yardage prop lines close to kickoff (within 3 hours) correlate with players going UNDER their prop line.

This project collects and analyzes prop line data to validate or disprove this hypothesis.

## Features

- **Historical Data Collection**: Fetches historical player prop odds from The Odds API
- **Real-Time Scraping**: Scrapes live prop lines from BettingPros with rate limiting
- **Player Stats Collection**: Gathers actual player performance from ESPN
- **Line Movement Detection**: Identifies significant prop line drops before kickoff
- **Statistical Analysis**: Calculates over/under rates with statistical significance testing
- **Web Dashboard**: Visualizes results with interactive charts

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  The Odds API   │     │   BettingPros   │     │    ESPN API     │
│  (Historical)   │     │   (Real-time)   │     │   (Results)     │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     FastAPI Backend     │
                    │   ┌─────────────────┐   │
                    │   │    Collectors   │   │
                    │   │    Scheduler    │   │
                    │   │    Analysis     │   │
                    │   └─────────────────┘   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      PostgreSQL         │
                    │   (Docker Container)    │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    React Dashboard      │
                    │   (Vite + Tailwind)     │
                    └─────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Docker and Docker Compose
- Node.js 18+
- [Yarn](https://yarnpkg.com/) (JavaScript package manager)
- The Odds API key (paid plan for historical data)

### 1. Clone and Setup

```bash
cd prop_line_analysis

# Install dependencies with uv (creates .venv automatically)
uv sync
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
# - ODDS_API_KEY: Your The Odds API key
# - DATABASE_URL: PostgreSQL connection string
```

### 3. Start Database

```bash
docker-compose up -d
```

### 4. Initialize Database

```bash
# Run migrations
uv run alembic upgrade head
```

### 5. Start Backend

```bash
uv run uvicorn src.api.main:app --reload
```

### 6. Start Frontend

```bash
cd frontend
yarn install
yarn dev
```

Visit http://localhost:5173 to view the line movement dashboard.

The dashboard shows:
- Current prop lines for all active players
- Line changes over 6 time windows (5, 10, 15, 30, 45, 60 minutes)
- Color-coded drops (red) and increases (green)
- Sortable columns to find sharpest movements
- Auto-refresh every 30 seconds

See `FRONTEND_DASHBOARD_GUIDE.md` for detailed usage.

## Usage

### Collecting Live Player Props (Recommended)

**Use the BettingPros scraper** to collect live player prop data. This is free and works with your current setup:

```bash
# Test the scraper (dry run)
uv run python scripts/run_scraper.py --dry-run

# Scrape all players in upcoming games
uv run python scripts/run_scraper.py

# Scrape specific players
uv run python scripts/run_scraper.py --players "Saquon Barkley" "Derrick Henry"

# Scrape only rushing yards
uv run python scripts/run_scraper.py --prop-type rushing

# Scrape only receiving yards
uv run python scripts/run_scraper.py --prop-type receiving

# Increase time window to 24 hours before kickoff
uv run python scripts/run_scraper.py --hours-before-kickoff 24
```

**⚠️ Important:** BettingPros only posts prop data 24-48 hours before games. For testing before props are available, use mock data (see below).

**Automated Collection:** The scheduler automatically runs the scraper every 5 minutes on game days when you start the backend:

```bash
uv run uvicorn src.api.main:app --reload
```

### Testing with Mock Data

For testing and development before live props are available, load realistic mock data:

```bash
# Load mock data into database
uv run python scripts/load_mock_data.py

# Clear and reload
uv run python scripts/load_mock_data.py --clear

# Preview without saving
uv run python scripts/load_mock_data.py --dry-run
```

**Mock data includes:**
- 7 players across 7 games
- 18 prop line snapshots with realistic values
- 5 significant late line drops (tests your thesis)
- Various scenarios: stable lines, early drops, late drops, line increases
- Both rushing and receiving yards props

After loading mock data, you can:
- Test API endpoints: `curl http://localhost:8000/api/props/snapshots`
- View line movements: `curl http://localhost:8000/api/movements/`
- Test the dashboard
- Verify analysis logic

### Alternative: The Odds API (Optional)

If you upgrade to a higher-tier subscription with player props access:

<details>
<summary>Click to expand The Odds API usage</summary>

#### Check API Access

```bash
# Verify what your API subscription includes
uv run python scripts/check_available_markets.py
```

#### Live Odds (Requires Pro+ plan)

```bash
uv run python scripts/fetch_live_odds.py --limit 3 --dry-run
```

#### Historical Data (Requires Historical plan)

```bash
# Fetch data for a specific week
uv run python scripts/fetch_historical_data.py --start 2024-12-17 --end 2024-12-23

# Fetch data for a single day
uv run python scripts/fetch_historical_data.py --date 2024-12-20

# Dry run (don't save to database)
uv run python scripts/fetch_historical_data.py --date 2024-12-20 --dry-run
```

See `API_DATA_SOURCES.md` for detailed information about subscription tiers and costs.

</details>

### Running Analysis

```python
from src.analysis.correlation import run_full_analysis

# Run complete thesis analysis
report = run_full_analysis()
print(report)
```

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/props/snapshots` | Get prop line snapshots |
| `GET /api/movements/` | Get detected line movements |
| `GET /api/analysis/thesis-summary` | Get thesis validation summary |
| `POST /api/analysis/run` | Trigger new analysis |

## Project Structure

```
prop_line_movement_analysis/
├── docker-compose.yml      # PostgreSQL + Redis
├── pyproject.toml          # Python dependencies (uv)
├── requirements.txt        # Python dependencies (pip fallback)
├── alembic/               # Database migrations
├── src/
│   ├── collectors/
│   │   ├── odds_api.py     # Historical data from The Odds API
│   │   ├── bettingpros.py  # Real-time scraping
│   │   ├── espn.py         # Player stats
│   │   └── player_discovery.py
│   ├── models/
│   │   └── database.py     # SQLAlchemy models
│   ├── analysis/
│   │   ├── line_movement.py    # Movement detection
│   │   └── correlation.py      # Statistical analysis
│   ├── scheduler/
│   │   └── jobs.py         # Automated scraping
│   └── api/
│       ├── main.py         # FastAPI app
│       └── routes/         # API endpoints
└── frontend/              # React dashboard
    ├── src/
    │   ├── pages/         # Dashboard pages
    │   ├── components/    # Reusable components
    │   └── api/           # API client
    └── package.json
```

## Configuration

### Line Movement Detection

Adjust thresholds in `.env` or via API:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `LINE_MOVEMENT_THRESHOLD_PCT` | 10.0 | Minimum % drop to flag as significant |
| `LINE_MOVEMENT_THRESHOLD_ABS` | 5.0 | Minimum yards drop to flag as significant |
| `HOURS_BEFORE_KICKOFF_THRESHOLD` | 3.0 | Time window for "late" movements |

### Scraping Schedule

The scheduler runs on game days:
- **Sunday**: 6am-midnight (all games)
- **Monday**: 4pm-midnight (MNF)
- **Thursday**: 4pm-midnight (TNF)
- **Saturday**: 12pm-midnight (late season)

## Data Sources

1. **The Odds API** (Historical)
   - Player props from 30+ sportsbooks
   - Historical snapshots every 5-10 minutes
   - Requires paid plan

2. **BettingPros** (Real-time)
   - Consensus lines from major books
   - Web scraping with rate limiting
   - Free to access

3. **ESPN API** (Results)
   - Actual player rushing/receiving stats
   - Free public API

## Statistical Methods

- **Chi-square test**: Tests if under rate differs from baseline
- **Wilson score interval**: 95% confidence intervals for proportions
- **P-value threshold**: < 0.05 for statistical significance

## License

MIT License - See LICENSE for details.

