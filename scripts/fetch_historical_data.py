#!/usr/bin/env python
"""
CLI script for fetching historical player prop data from The Odds API.

Usage:
    # Fetch data for a specific week
    python scripts/fetch_historical_data.py --start 2024-12-17 --end 2024-12-23
    
    # Fetch data for a single day
    python scripts/fetch_historical_data.py --date 2024-12-20
    
    # Fetch with custom snapshot intervals
    python scripts/fetch_historical_data.py --start 2024-12-17 --end 2024-12-23 --interval 15
    
    # Fetch with more snapshots (more hours before kickoff)
    python scripts/fetch_historical_data.py --start 2024-12-17 --end 2024-12-23 --hours-before 24
"""

import asyncio
import argparse
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.collectors.odds_api import OddsAPICollector
from src.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
)
logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime object."""
    try:
        # Try parsing as date only (YYYY-MM-DD)
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            # Try parsing with time (YYYY-MM-DD HH:MM:SS)
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            # Try ISO format
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))


async def fetch_historical_data(
    start_date: datetime,
    end_date: datetime,
    hours_before: int = 12,
    interval_minutes: int = 30,
    dry_run: bool = False,
):
    """
    Fetch historical player prop data for a date range.
    
    Args:
        start_date: Start of date range
        end_date: End of date range
        hours_before: How many hours before kickoff to start collecting snapshots
        interval_minutes: Minutes between each snapshot
        dry_run: If True, don't save to database
    """
    settings = get_settings()
    
    # Check if API key is configured
    if not settings.odds_api_key or settings.odds_api_key == "":
        logger.error("❌ The Odds API key not configured!")
        logger.error("   Please set ODDS_API_KEY in your .env file")
        logger.error("   Get your API key at: https://the-odds-api.com/")
        return
    
    logger.info("=" * 70)
    logger.info("Fetching Historical Player Prop Data from The Odds API")
    logger.info("=" * 70)
    logger.info(f"\nDate Range: {start_date.date()} to {end_date.date()}")
    logger.info(f"Snapshot Window: {hours_before} hours before kickoff")
    logger.info(f"Snapshot Interval: {interval_minutes} minutes")
    
    if dry_run:
        logger.info("\n⚠️  DRY RUN MODE - Data will not be saved to database")
    
    logger.info("\n" + "=" * 70)
    
    async with OddsAPICollector() as collector:
        logger.info("\n1. Fetching events from The Odds API...")
        
        try:
            # Get events for the date range
            events_data = await collector.get_historical_events(start_date)
            
            if not events_data or "data" not in events_data:
                logger.error("   ❌ No events data returned from API")
                logger.error("   This could mean:")
                logger.error("      - No games scheduled in this date range")
                logger.error("      - API key issue")
                logger.error("      - Date is outside available historical range")
                return
            
            events = events_data.get("data", [])
            logger.info(f"   ✓ Found {len(events)} events from API")
            
            # Filter events within our date range
            filtered_events = []
            for event in events:
                commence_time_str = event.get("commence_time")
                if not commence_time_str:
                    continue
                
                game_time = datetime.fromisoformat(
                    commence_time_str.replace("Z", "+00:00")
                )
                
                if start_date <= game_time <= end_date:
                    filtered_events.append(event)
            
            if not filtered_events:
                logger.warning(f"   ⚠️  No events found within date range")
                logger.warning(f"      {start_date.date()} to {end_date.date()}")
                return
            
            logger.info(f"   ✓ {len(filtered_events)} events within date range\n")
            
            # Display events
            logger.info("2. Events to process:")
            for i, event in enumerate(filtered_events, 1):
                game_time = datetime.fromisoformat(
                    event.get("commence_time").replace("Z", "+00:00")
                )
                logger.info(f"   {i}. {event.get('away_team')} @ {event.get('home_team')}")
                logger.info(f"      Game Time: {game_time}")
                logger.info(f"      Event ID: {event.get('id')}")
            
            logger.info(f"\n3. Collecting prop snapshots...")
            
            all_snapshots = []
            
            for i, event in enumerate(filtered_events, 1):
                event_id = event.get("id")
                commence_time_str = event.get("commence_time")
                home_team = event.get("home_team", "")
                away_team = event.get("away_team", "")
                
                game_time = datetime.fromisoformat(
                    commence_time_str.replace("Z", "+00:00")
                )
                
                logger.info(f"\n   Processing event {i}/{len(filtered_events)}")
                logger.info(f"   {away_team} @ {home_team}")
                
                # Generate snapshot times
                snapshot_times = collector.generate_snapshot_times(
                    game_time,
                    hours_before=hours_before,
                    interval_minutes=interval_minutes,
                )
                logger.info(f"   → Fetching {len(snapshot_times)} snapshots...")
                
                # Collect props
                try:
                    snapshots = await collector.collect_event_props(
                        event_id=event_id,
                        game_commence_time=game_time,
                        home_team=home_team,
                        away_team=away_team,
                        snapshot_times=snapshot_times,
                    )
                    
                    logger.info(f"   ✓ Collected {len(snapshots)} prop snapshots")
                    all_snapshots.extend(snapshots)
                    
                except Exception as e:
                    logger.error(f"   ❌ Error collecting props: {e}")
            
            # Summary
            logger.info(f"\n{'=' * 70}")
            logger.info(f"4. Collection Summary")
            logger.info(f"{'=' * 70}")
            logger.info(f"\nTotal snapshots collected: {len(all_snapshots)}")
            
            if all_snapshots:
                # Count unique players and prop types
                unique_players = len(set(s.player_name for s in all_snapshots))
                rushing = sum(1 for s in all_snapshots if s.prop_type.value == "rushing_yards")
                receiving = sum(1 for s in all_snapshots if s.prop_type.value == "receiving_yards")
                
                logger.info(f"Unique players: {unique_players}")
                logger.info(f"Rushing yards props: {rushing}")
                logger.info(f"Receiving yards props: {receiving}")
                
                # Show sample
                logger.info(f"\nSample snapshots:")
                for snapshot in all_snapshots[:5]:
                    logger.info(f"  - {snapshot.player_name}: {snapshot.prop_type.value}")
                    logger.info(f"    Consensus: {snapshot.consensus_line}, "
                               f"DK: {snapshot.draftkings_line}, "
                               f"FD: {snapshot.fanduel_line}")
                    logger.info(f"    Time: {snapshot.snapshot_time} "
                               f"({snapshot.hours_before_kickoff}h before kickoff)")
                
                if len(all_snapshots) > 5:
                    logger.info(f"  ... and {len(all_snapshots) - 5} more")
                
                # Save to database
                if not dry_run:
                    logger.info(f"\n5. Saving to database...")
                    try:
                        saved = collector.save_snapshots(all_snapshots)
                        logger.info(f"   ✓ Saved {saved} snapshots to database")
                    except Exception as e:
                        logger.error(f"   ❌ Error saving to database: {e}")
                else:
                    logger.info(f"\n5. Skipping database save (dry run mode)")
            else:
                logger.warning("\n⚠️  No prop data collected")
                logger.warning("   This could mean:")
                logger.warning("      - No player props available for these games")
                logger.warning("      - Games are outside The Odds API's coverage")
                logger.warning("      - Historical data not available for this date range")
            
            logger.info(f"\n{'=' * 70}")
            logger.info("✓ Done!")
            logger.info(f"{'=' * 70}\n")
            
        except Exception as e:
            logger.error(f"\n❌ Error fetching data: {e}")
            logger.error(f"   Check your API key and date range")
            raise


def main():
    parser = argparse.ArgumentParser(
        description="Fetch historical player prop data from The Odds API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch data for a specific week (NFL regular season)
  python scripts/fetch_historical_data.py --start 2024-12-17 --end 2024-12-23

  # Fetch data for a single day
  python scripts/fetch_historical_data.py --date 2024-12-20

  # Fetch with 15-minute snapshot intervals
  python scripts/fetch_historical_data.py --start 2024-12-17 --end 2024-12-23 --interval 15

  # Fetch more data (24 hours before kickoff)
  python scripts/fetch_historical_data.py --start 2024-12-17 --end 2024-12-23 --hours-before 24

  # Dry run (don't save to database)
  python scripts/fetch_historical_data.py --date 2024-12-20 --dry-run

Note: Requires a valid API key from The Odds API (https://the-odds-api.com/)
      Historical data requires a paid subscription plan.
        """,
    )
    
    # Date arguments
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument(
        "--date",
        type=str,
        help="Single date to fetch (YYYY-MM-DD)",
    )
    date_group.add_argument(
        "--start",
        type=str,
        help="Start date of range (YYYY-MM-DD)",
    )
    
    parser.add_argument(
        "--end",
        type=str,
        help="End date of range (YYYY-MM-DD) - required if --start is used",
    )
    
    # Snapshot configuration
    parser.add_argument(
        "--hours-before",
        type=int,
        default=12,
        help="How many hours before kickoff to start collecting snapshots (default: 12)",
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Minutes between each snapshot (default: 30)",
    )
    
    # Options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch data but don't save to database",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Parse dates
    try:
        if args.date:
            # Single date - fetch for that day
            date = parse_date(args.date)
            start_date = date.replace(hour=0, minute=0, second=0)
            end_date = date.replace(hour=23, minute=59, second=59)
        else:
            # Date range
            if not args.end:
                parser.error("--end is required when using --start")
            
            start_date = parse_date(args.start).replace(hour=0, minute=0, second=0)
            end_date = parse_date(args.end).replace(hour=23, minute=59, second=59)
        
        # Validate date range
        if end_date < start_date:
            parser.error("End date must be after start date")
        
        # Run the fetcher
        asyncio.run(fetch_historical_data(
            start_date=start_date,
            end_date=end_date,
            hours_before=args.hours_before,
            interval_minutes=args.interval,
            dry_run=args.dry_run,
        ))
        
    except ValueError as e:
        parser.error(f"Invalid date format: {e}")
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        logger.error(f"\nFatal error: {e}")
        raise


if __name__ == "__main__":
    main()

