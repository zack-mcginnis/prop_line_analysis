# Automatic Table Creation Setup

## Overview
The database tables will now be created automatically when deploying to Railway.

## What Was Done

### 1. Created Initial Migration
- **File**: `alembic/versions/09d0389c0b53_initial_tables.py`
- Creates all 4 required tables:
  - `prop_line_snapshots` - Main table for tracking prop line data over time
  - `player_game_stats` - Actual player performance data
  - `line_movements` - Pre-computed significant line movements
  - `analysis_results` - Aggregated correlation analysis results
- Creates all necessary indexes for performance
- Creates PostgreSQL ENUM types for `PropType` and `DataSource`

### 2. Deployment Flow
When your app deploys to Railway:

1. **Container builds** (Dockerfile)
   - Copies `alembic/` directory with the migration
   - Copies `alembic.ini` configuration
   - Sets up `start.sh` as executable

2. **Container starts** (start.sh)
   - Connects to Railway's PostgreSQL database
   - Runs `alembic upgrade head` 
     - This executes the migration and creates all tables
   - Starts the FastAPI application with uvicorn

### 3. What Gets Created

#### Tables Created:
```sql
-- prop_line_snapshots: Primary data table
-- Columns: id, event_id, game_commence_time, home_team, away_team, 
--          player_name, player_slug, team, prop_type, consensus_line,
--          draftkings_line, fanduel_line, betmgm_line, caesars_line,
--          pointsbet_line, over_odds, under_odds, snapshot_time,
--          source_timestamp, hours_before_kickoff, source, created_at, raw_data
-- Indexes: event_id, player_name, snapshot_time, game_commence_time

-- player_game_stats: Actual game results
-- Columns: id, event_id, game_date, season, week, player_name, player_id,
--          team, opponent, rushing_attempts, rushing_yards, rushing_tds,
--          receptions, receiving_targets, receiving_yards, receiving_tds,
--          is_home, game_result, created_at, updated_at
-- Indexes: event_id, player_name, game_date

-- line_movements: Pre-calculated movement analysis
-- Columns: id, event_id, player_name, prop_type, initial_line, final_line,
--          initial_snapshot_time, final_snapshot_time, movement_absolute,
--          movement_pct, hours_before_kickoff, actual_yards, went_over,
--          went_under, game_commence_time, created_at
-- Indexes: event_id, player_name, prop_type, movement_pct, hours_before_kickoff

-- analysis_results: Statistical analysis cache
-- Columns: id, analysis_name, prop_type, movement_threshold_pct,
--          movement_threshold_abs, hours_before_threshold, sample_size,
--          date_range_start, date_range_end, over_count, under_count,
--          push_count, over_rate, under_rate, chi_square_statistic,
--          p_value, is_significant, confidence_interval_low,
--          confidence_interval_high, baseline_over_rate,
--          baseline_sample_size, created_at
-- Indexes: analysis_name
```

#### ENUM Types Created:
- `proptype`: 'RUSHING_YARDS', 'RECEIVING_YARDS'
- `datasource`: 'BETTINGPROS', 'ODDS_API'

## Testing

### Verify Tables Exist
After deployment, you can verify tables were created:

1. Check Railway logs for:
   ```
   Running database migrations...
   ✓ Migrations completed successfully
   ```

2. Use Railway's PostgreSQL plugin to query:
   ```sql
   -- List all tables
   SELECT table_name FROM information_schema.tables 
   WHERE table_schema = 'public';
   
   -- Check alembic version
   SELECT * FROM alembic_version;
   ```

3. Use your API health endpoint:
   ```bash
   curl https://your-app.railway.app/health
   ```

## Next Steps

1. **Deploy to Railway**
   - Commit this migration: `git add alembic/versions/09d0389c0b53_initial_tables.py`
   - Push to trigger Railway deployment
   - Watch logs to confirm migration runs successfully

2. **Verify Deployment**
   - Check that `/health` endpoint returns success
   - Verify tables exist in Railway's PostgreSQL dashboard

3. **Populate Data** (optional)
   - Use your data collection scripts to populate tables
   - Run `scripts/load_mock_data.py` for testing

## Troubleshooting

### If migration fails:
1. Check Railway logs for specific error messages
2. Verify DATABASE_URL is set correctly in Railway
3. Ensure PostgreSQL service is linked to your app
4. Check that the database is accessible (network/firewall)

### To manually run migration:
```bash
# SSH into Railway or run locally with Railway DB URL
export DATABASE_URL="your-railway-postgres-url"
alembic upgrade head
```

### To rollback (if needed):
```bash
alembic downgrade -1  # Go back one migration
alembic downgrade base  # Remove all tables
```

## Notes

- The migration is idempotent - it won't fail if tables already exist
- Alembic tracks which migrations have been applied using the `alembic_version` table
- Future schema changes should use new migrations: `alembic revision -m "description"`
- The migration will run automatically on every deployment (but only applies new migrations)

