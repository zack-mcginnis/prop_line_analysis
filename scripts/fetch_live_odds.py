#!/usr/bin/env python
"""
CLI script for fetching live player prop odds from The Odds API.

This uses the LIVE odds endpoint (not historical), which is included in standard plans.

Usage:
    # Fetch live props for all upcoming games
    python scripts/fetch_live_odds.py
    
    # Fetch only rushing yards props
    python scripts/fetch_live_odds.py --prop-type rushing
    
    # Fetch only receiving yards props
    python scripts/fetch_live_odds.py --prop-type receiving
    
    # Dry run (don't save to database)
    python scripts/fetch_live_odds.py --dry-run
    
    # Limit to specific number of games (save API quota)
    python scripts/fetch_live_odds.py --limit 3
"""

import asyncio
import argparse
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings
from src.models.database import (
    PropLineSnapshot,
    PropType,
    DataSource,
    get_session,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
)
logger = logging.getLogger(__name__)


class LiveOddsAPICollector:
    """Collector for live player prop odds from The Odds API."""
    
    SPORT_KEY = "americanfootball_nfl"
    
    MARKET_MAP = {
        "rushing": "player_rush_yds",
        "receiving": "player_reception_yds",
    }
    
    PROP_TYPE_MAP = {
        "player_rush_yds": PropType.RUSHING_YARDS,
        "player_reception_yds": PropType.RECEIVING_YARDS,
    }
    
    # Bookmaker key mapping
    BOOKMAKER_MAP = {
        "draftkings": "draftkings_line",
        "fanduel": "fanduel_line",
        "betmgm": "betmgm_line",
        "williamhill_us": "caesars_line",
        "pointsbetus": "pointsbet_line",
    }
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.odds_api_base_url
        self.api_key = self.settings.odds_api_key
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client."""
        if self._client is None:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_live_odds(
        self,
        markets: List[str],
    ) -> dict:
        """
        Get live odds for NFL player props.
        
        Args:
            markets: List of market keys (e.g., ['player_rush_yds', 'player_reception_yds'])
            
        Returns:
            API response with odds data
        """
        url = f"{self.base_url}/sports/{self.SPORT_KEY}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": ",".join(markets),
            "oddsFormat": "american",
        }
        
        logger.debug(f"Fetching from: {url}")
        logger.debug(f"Markets: {markets}")
        
        response = await self.client.get(url, params=params)
        
        # Log quota usage from headers
        requests_used = response.headers.get("x-requests-used", "?")
        requests_remaining = response.headers.get("x-requests-remaining", "?")
        requests_last = response.headers.get("x-requests-last", "?")
        
        logger.info(f"\n📊 API Quota Usage:")
        logger.info(f"   This request: {requests_last} credits")
        logger.info(f"   Used: {requests_used} | Remaining: {requests_remaining}")
        
        response.raise_for_status()
        return response.json()
    
    def _calculate_consensus(self, lines: dict) -> Optional[Decimal]:
        """Calculate consensus line from all bookmaker lines."""
        values = [v for v in lines.values() if v is not None]
        if not values:
            return None
        return Decimal(str(round(sum(values) / len(values), 1)))
    
    def _calculate_hours_before_kickoff(
        self,
        snapshot_time: datetime,
        game_time: datetime,
    ) -> Decimal:
        """Calculate hours between snapshot and game time."""
        delta = game_time - snapshot_time
        hours = delta.total_seconds() / 3600
        return Decimal(str(round(hours, 2)))
    
    def parse_odds_response(self, data: dict) -> List[PropLineSnapshot]:
        """
        Parse the API response and create PropLineSnapshot objects.
        
        Args:
            data: Response from The Odds API
            
        Returns:
            List of PropLineSnapshot objects
        """
        snapshots = []
        snapshot_time = datetime.now(timezone.utc)
        
        for event in data:
            event_id = event.get("id")
            commence_time_str = event.get("commence_time")
            home_team = event.get("home_team")
            away_team = event.get("away_team")
            
            if not all([event_id, commence_time_str, home_team, away_team]):
                continue
            
            game_time = datetime.fromisoformat(
                commence_time_str.replace("Z", "+00:00")
            )
            
            # Track player props: {player_name: {prop_type: {bookmaker: line}}}
            player_props = {}
            
            for bookmaker in event.get("bookmakers", []):
                book_key = bookmaker.get("key")
                
                for market in bookmaker.get("markets", []):
                    market_key = market.get("key")
                    prop_type = self.PROP_TYPE_MAP.get(market_key)
                    
                    if not prop_type:
                        continue
                    
                    # Find "Over" outcomes (we use the Over line value)
                    for outcome in market.get("outcomes", []):
                        if outcome.get("name") != "Over":
                            continue
                        
                        player_name = outcome.get("description")
                        line_value = outcome.get("point")
                        
                        if not player_name or line_value is None:
                            continue
                        
                        # Initialize nested dicts
                        if player_name not in player_props:
                            player_props[player_name] = {}
                        if prop_type not in player_props[player_name]:
                            player_props[player_name][prop_type] = {}
                        
                        # Store line for this bookmaker
                        player_props[player_name][prop_type][book_key] = Decimal(str(line_value))
            
            # Create snapshots for each player/prop combination
            for player_name, props in player_props.items():
                for prop_type, bookmaker_lines in props.items():
                    # Map bookmaker keys to our field names
                    line_fields = {}
                    for book_key, line_value in bookmaker_lines.items():
                        field_name = self.BOOKMAKER_MAP.get(book_key)
                        if field_name:
                            line_fields[field_name] = line_value
                    
                    # Calculate consensus
                    consensus = self._calculate_consensus(bookmaker_lines)
                    
                    snapshot = PropLineSnapshot(
                        event_id=event_id,
                        game_commence_time=game_time,
                        home_team=home_team,
                        away_team=away_team,
                        player_name=player_name,
                        player_slug=player_name.lower().replace(" ", "-").replace(".", "").replace("'", ""),
                        prop_type=prop_type,
                        consensus_line=consensus,
                        draftkings_line=line_fields.get("draftkings_line"),
                        fanduel_line=line_fields.get("fanduel_line"),
                        betmgm_line=line_fields.get("betmgm_line"),
                        caesars_line=line_fields.get("caesars_line"),
                        pointsbet_line=line_fields.get("pointsbet_line"),
                        snapshot_time=snapshot_time,
                        source_timestamp=snapshot_time,
                        hours_before_kickoff=self._calculate_hours_before_kickoff(
                            snapshot_time, game_time
                        ),
                        source=DataSource.ODDS_API,
                        raw_data=json.dumps({
                            "bookmakers": list(bookmaker_lines.keys()),
                            "event_id": event_id,
                        }),
                    )
                    snapshots.append(snapshot)
        
        return snapshots
    
    def save_snapshots(self, snapshots: List[PropLineSnapshot]) -> int:
        """Save snapshots to database."""
        if not snapshots:
            return 0
        
        session = get_session()
        try:
            session.add_all(snapshots)
            session.commit()
            return len(snapshots)
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()


async def fetch_live_odds(
    prop_types: List[str],
    limit: Optional[int] = None,
    dry_run: bool = False,
):
    """
    Fetch live player prop odds.
    
    Args:
        prop_types: List of prop types to fetch ('rushing', 'receiving', or both)
        limit: Optional limit on number of games to process
        dry_run: If True, don't save to database
    """
    settings = get_settings()
    
    # Check API key
    if not settings.odds_api_key or settings.odds_api_key == "":
        logger.error("❌ The Odds API key not configured!")
        logger.error("   Please set ODDS_API_KEY in your .env file")
        return
    
    logger.info("=" * 70)
    logger.info("Fetching Live Player Prop Odds from The Odds API")
    logger.info("=" * 70)
    logger.info(f"\nProp Types: {', '.join(prop_types)}")
    
    if limit:
        logger.info(f"Game Limit: {limit}")
    
    if dry_run:
        logger.info("\n⚠️  DRY RUN MODE - Data will not be saved to database")
    
    logger.info("\n" + "=" * 70)
    
    async with LiveOddsAPICollector() as collector:
        # Map prop types to market keys
        markets = [collector.MARKET_MAP[pt] for pt in prop_types]
        
        logger.info("\n1. Fetching live odds from The Odds API...")
        
        try:
            data = await collector.get_live_odds(markets)
            
            if not data:
                logger.warning("   ⚠️  No data returned from API")
                return
            
            logger.info(f"\n   ✓ Found {len(data)} upcoming games")
            
            # Apply limit if specified
            if limit:
                data = data[:limit]
                logger.info(f"   → Processing first {len(data)} games (limit applied)")
            
            # Display games
            logger.info("\n2. Games found:")
            for i, event in enumerate(data, 1):
                game_time = datetime.fromisoformat(
                    event.get("commence_time").replace("Z", "+00:00")
                )
                logger.info(f"   {i}. {event.get('away_team')} @ {event.get('home_team')}")
                logger.info(f"      Kickoff: {game_time}")
                
                # Count available props
                prop_count = 0
                for bookmaker in event.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        prop_count += len(market.get("outcomes", [])) // 2  # Divide by 2 (Over/Under)
                
                logger.info(f"      Props available: {prop_count}")
            
            # Parse odds
            logger.info(f"\n3. Parsing prop data...")
            snapshots = collector.parse_odds_response(data)
            
            logger.info(f"\n{'=' * 70}")
            logger.info("4. Collection Summary")
            logger.info(f"{'=' * 70}")
            logger.info(f"\nTotal snapshots collected: {len(snapshots)}")
            
            if snapshots:
                # Count unique players and prop types
                unique_players = len(set(s.player_name for s in snapshots))
                rushing = sum(1 for s in snapshots if s.prop_type == PropType.RUSHING_YARDS)
                receiving = sum(1 for s in snapshots if s.prop_type == PropType.RECEIVING_YARDS)
                
                logger.info(f"Unique players: {unique_players}")
                logger.info(f"Rushing yards props: {rushing}")
                logger.info(f"Receiving yards props: {receiving}")
                
                # Show sample
                logger.info(f"\nSample snapshots:")
                for snapshot in snapshots[:10]:
                    logger.info(f"  - {snapshot.player_name} ({snapshot.away_team} @ {snapshot.home_team})")
                    logger.info(f"    {snapshot.prop_type.value}: Consensus={snapshot.consensus_line}, "
                               f"DK={snapshot.draftkings_line}, FD={snapshot.fanduel_line}")
                    logger.info(f"    Kickoff in {snapshot.hours_before_kickoff} hours")
                
                if len(snapshots) > 10:
                    logger.info(f"  ... and {len(snapshots) - 10} more")
                
                # Save to database
                if not dry_run:
                    logger.info(f"\n5. Saving to database...")
                    try:
                        saved = collector.save_snapshots(snapshots)
                        logger.info(f"   ✓ Saved {saved} snapshots to database")
                    except Exception as e:
                        logger.error(f"   ❌ Error saving to database: {e}")
                else:
                    logger.info(f"\n5. Skipping database save (dry run mode)")
            else:
                logger.warning("\n⚠️  No prop data collected")
            
            logger.info(f"\n{'=' * 70}")
            logger.info("✓ Done!")
            logger.info(f"{'=' * 70}\n")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.error("\n❌ 401 Unauthorized - API key is invalid or expired")
                logger.error("   Check your API key at: https://the-odds-api.com/")
            elif e.response.status_code == 422:
                logger.error("\n❌ 422 Unprocessable Entity - Player props not available")
                logger.error("   Your API subscription does not include live player props.")
                logger.error("\n   Solutions:")
                logger.error("   1. Use BettingPros scraper (free): uv run python scripts/run_scraper.py")
                logger.error("   2. Upgrade your plan at: https://the-odds-api.com/")
                logger.error("   3. Use historical player props (if available in your plan)")
            elif e.response.status_code == 429:
                logger.error("\n❌ 429 Rate Limited - Too many requests")
                logger.error("   Wait a moment and try again")
            else:
                logger.error(f"\n❌ HTTP {e.response.status_code} Error: {e}")
            raise
        except Exception as e:
            # Check if this is a RetryError wrapping an HTTPStatusError
            from tenacity import RetryError
            
            if isinstance(e, RetryError):
                # Extract the original exception
                try:
                    original_exception = e.last_attempt.exception()
                    if isinstance(original_exception, httpx.HTTPStatusError):
                        if original_exception.response.status_code == 422:
                            logger.error("\n❌ 422 Unprocessable Entity - Player props not available")
                            logger.error("   Your API subscription does not include live player props.")
                            logger.error("\n   💡 Solutions:")
                            logger.error("   1. Use BettingPros scraper (free): uv run python scripts/run_scraper.py")
                            logger.error("   2. Upgrade your plan at: https://the-odds-api.com/")
                            logger.error("   3. Run diagnostic: uv run python scripts/check_available_markets.py")
                            return
                        else:
                            logger.error(f"\n❌ HTTP {original_exception.response.status_code} Error")
                except:
                    pass
            
            logger.error(f"\n❌ Error fetching data: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(
        description="Fetch live player prop odds from The Odds API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch all props (rushing and receiving)
  python scripts/fetch_live_odds.py

  # Fetch only rushing yards
  python scripts/fetch_live_odds.py --prop-type rushing

  # Fetch only receiving yards
  python scripts/fetch_live_odds.py --prop-type receiving

  # Limit to 3 games (save API quota)
  python scripts/fetch_live_odds.py --limit 3

  # Dry run (don't save to database)
  python scripts/fetch_live_odds.py --dry-run

  # Verbose logging
  python scripts/fetch_live_odds.py --verbose

Note: This uses the LIVE odds endpoint, included in standard API plans.
      Each request costs credits based on: 1 x [markets] x [regions]
      Example: 2 markets (rush+receive) x 1 region = 2 credits per request
        """,
    )
    
    parser.add_argument(
        "--prop-type",
        choices=["rushing", "receiving", "both"],
        default="both",
        help="Type of prop to fetch (default: both)",
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of games to process (saves API quota)",
    )
    
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
    
    # Determine prop types
    prop_types = []
    if args.prop_type in ["rushing", "both"]:
        prop_types.append("rushing")
    if args.prop_type in ["receiving", "both"]:
        prop_types.append("receiving")
    
    # Run the fetcher
    try:
        asyncio.run(fetch_live_odds(
            prop_types=prop_types,
            limit=args.limit,
            dry_run=args.dry_run,
        ))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        logger.error(f"\nFatal error: {e}")
        raise


if __name__ == "__main__":
    main()

