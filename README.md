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
- Docker and Docker Compose
- Node.js 18+
- The Odds API key (paid plan for historical data)

### 1. Clone and Setup

```bash
cd prop_line_analysis

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
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
alembic upgrade head
```

### 5. Start Backend

```bash
uvicorn src.api.main:app --reload
```

### 6. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000 to view the dashboard.

## Usage

### Collecting Historical Data

```python
from src.collectors.odds_api import OddsAPICollector
from datetime import datetime, timezone

async with OddsAPICollector() as collector:
    snapshots = await collector.collect_week_props(
        week_start=datetime(2024, 12, 1, tzinfo=timezone.utc),
        week_end=datetime(2024, 12, 8, tzinfo=timezone.utc),
    )
    collector.save_snapshots(snapshots)
```

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
├── requirements.txt        # Python dependencies
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

