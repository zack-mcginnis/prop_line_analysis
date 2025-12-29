"""The Odds API client for historical player prop data collection."""

import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings
from src.models.database import (
    PropLineSnapshot,
    PropType,
    DataSource,
    get_session,
)


class OddsAPICollector:
    """
    Client for The Odds API to collect historical player prop data.
    
    API Documentation: https://the-odds-api.com/historical-odds-data/
    """
    
    SPORT_KEY = "americanfootball_nfl"
    PLAYER_PROPS_MARKETS = ["player_rush_yds", "player_reception_yds"]
    
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
    
    def _get_default_params(self) -> Dict[str, str]:
        """Get default query parameters."""
        return {
            "apiKey": self.api_key,
            "regions": "us",
            "oddsFormat": "american",
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_historical_events(
        self,
        date: datetime,
    ) -> Dict[str, Any]:
        """
        Get historical NFL events for a specific date.
        
        Args:
            date: The date to query for events
            
        Returns:
            API response with events data
        """
        url = f"{self.base_url}/historical/sports/{self.SPORT_KEY}/events"
        params = {
            **self._get_default_params(),
            "date": date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_historical_event_odds(
        self,
        event_id: str,
        date: datetime,
        markets: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get historical odds for a specific event (game) including player props.
        
        Args:
            event_id: The unique event ID
            date: The snapshot timestamp to query
            markets: List of markets to query (defaults to player props)
            
        Returns:
            API response with odds data
        """
        if markets is None:
            markets = self.PLAYER_PROPS_MARKETS
        
        url = f"{self.base_url}/historical/sports/{self.SPORT_KEY}/events/{event_id}/odds"
        params = {
            **self._get_default_params(),
            "date": date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "markets": ",".join(markets),
        }
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def _parse_prop_type(self, market_key: str) -> Optional[PropType]:
        """Convert API market key to PropType enum."""
        mapping = {
            "player_rush_yds": PropType.RUSHING_YARDS,
            "player_reception_yds": PropType.RECEIVING_YARDS,
        }
        return mapping.get(market_key)
    
    def _extract_line_value(self, outcome: Dict[str, Any]) -> Optional[Decimal]:
        """Extract line value from outcome data."""
        point = outcome.get("point")
        if point is not None:
            return Decimal(str(point))
        return None
    
    def _calculate_hours_before_kickoff(
        self,
        snapshot_time: datetime,
        game_time: datetime,
    ) -> Decimal:
        """Calculate hours between snapshot and game time."""
        delta = game_time - snapshot_time
        hours = delta.total_seconds() / 3600
        return Decimal(str(round(hours, 2)))
    
    async def collect_event_props(
        self,
        event_id: str,
        game_commence_time: datetime,
        home_team: str,
        away_team: str,
        snapshot_times: List[datetime],
    ) -> List[PropLineSnapshot]:
        """
        Collect player prop snapshots for a specific event across multiple timestamps.
        
        Args:
            event_id: The unique event ID
            game_commence_time: When the game starts
            home_team: Home team name
            away_team: Away team name
            snapshot_times: List of timestamps to collect snapshots for
            
        Returns:
            List of PropLineSnapshot objects
        """
        snapshots = []
        
        for snapshot_time in snapshot_times:
            try:
                data = await self.get_historical_event_odds(event_id, snapshot_time)
                
                if not data or "data" not in data:
                    continue
                
                event_data = data["data"]
                timestamp = datetime.fromisoformat(
                    data.get("timestamp", snapshot_time.isoformat()).replace("Z", "+00:00")
                )
                
                # Process each bookmaker
                bookmaker_lines: Dict[str, Dict[str, Dict[str, Any]]] = {}
                
                for bookmaker in event_data.get("bookmakers", []):
                    book_key = bookmaker["key"]
                    
                    for market in bookmaker.get("markets", []):
                        market_key = market["key"]
                        prop_type = self._parse_prop_type(market_key)
                        
                        if prop_type is None:
                            continue
                        
                        for outcome in market.get("outcomes", []):
                            player_name = outcome.get("description", "")
                            if not player_name:
                                continue
                            
                            line_value = self._extract_line_value(outcome)
                            if line_value is None:
                                continue
                            
                            # Initialize player entry if needed
                            key = f"{player_name}_{prop_type.value}"
                            if key not in bookmaker_lines:
                                bookmaker_lines[key] = {
                                    "player_name": player_name,
                                    "prop_type": prop_type,
                                    "lines": {},
                                }
                            
                            # Store line for this bookmaker
                            bookmaker_lines[key]["lines"][book_key] = {
                                "line": line_value,
                                "price": outcome.get("price"),
                                "name": outcome.get("name"),  # Over/Under
                            }
                
                # Create snapshot records
                for key, player_data in bookmaker_lines.items():
                    lines = player_data["lines"]
                    
                    # Calculate consensus (average of all books)
                    all_lines = [v["line"] for v in lines.values()]
                    consensus = sum(all_lines) / len(all_lines) if all_lines else None
                    
                    snapshot = PropLineSnapshot(
                        event_id=event_id,
                        game_commence_time=game_commence_time,
                        home_team=home_team,
                        away_team=away_team,
                        player_name=player_data["player_name"],
                        prop_type=player_data["prop_type"],
                        consensus_line=Decimal(str(round(consensus, 1))) if consensus else None,
                        draftkings_line=lines.get("draftkings", {}).get("line"),
                        fanduel_line=lines.get("fanduel", {}).get("line"),
                        betmgm_line=lines.get("betmgm", {}).get("line"),
                        caesars_line=lines.get("williamhill_us", {}).get("line"),
                        pointsbet_line=lines.get("pointsbetus", {}).get("line"),
                        snapshot_time=timestamp,
                        source_timestamp=timestamp,
                        hours_before_kickoff=self._calculate_hours_before_kickoff(
                            timestamp, game_commence_time
                        ),
                        source=DataSource.ODDS_API,
                        raw_data=json.dumps(lines),
                    )
                    snapshots.append(snapshot)
                
                # Rate limiting between API calls
                await asyncio.sleep(0.5)
                
            except httpx.HTTPStatusError as e:
                print(f"HTTP error for event {event_id} at {snapshot_time}: {e}")
            except Exception as e:
                print(f"Error processing event {event_id} at {snapshot_time}: {e}")
        
        return snapshots
    
    def generate_snapshot_times(
        self,
        game_commence_time: datetime,
        hours_before: int = 12,
        interval_minutes: int = 30,
    ) -> List[datetime]:
        """
        Generate a list of snapshot timestamps leading up to a game.
        
        Args:
            game_commence_time: When the game starts
            hours_before: How many hours before kickoff to start
            interval_minutes: Minutes between each snapshot
            
        Returns:
            List of datetime objects for each snapshot time
        """
        times = []
        current = game_commence_time - timedelta(hours=hours_before)
        
        while current < game_commence_time:
            times.append(current)
            current += timedelta(minutes=interval_minutes)
        
        return times
    
    async def collect_week_props(
        self,
        week_start: datetime,
        week_end: datetime,
    ) -> List[PropLineSnapshot]:
        """
        Collect player props for all games in a week.
        
        Args:
            week_start: Start of the week (usually Tuesday)
            week_end: End of the week (usually Monday)
            
        Returns:
            List of all collected PropLineSnapshot objects
        """
        all_snapshots = []
        
        # Get events for the week
        events_data = await self.get_historical_events(week_start)
        
        if not events_data or "data" not in events_data:
            return all_snapshots
        
        for event in events_data.get("data", []):
            event_id = event.get("id")
            commence_time_str = event.get("commence_time")
            
            if not event_id or not commence_time_str:
                continue
            
            game_commence_time = datetime.fromisoformat(
                commence_time_str.replace("Z", "+00:00")
            )
            
            # Skip games outside our week range
            if game_commence_time < week_start or game_commence_time > week_end:
                continue
            
            home_team = event.get("home_team", "")
            away_team = event.get("away_team", "")
            
            # Generate snapshot times for this game
            snapshot_times = self.generate_snapshot_times(game_commence_time)
            
            # Collect props for this event
            snapshots = await self.collect_event_props(
                event_id=event_id,
                game_commence_time=game_commence_time,
                home_team=home_team,
                away_team=away_team,
                snapshot_times=snapshot_times,
            )
            
            all_snapshots.extend(snapshots)
            
            # Rate limiting between events
            await asyncio.sleep(1.0)
        
        return all_snapshots
    
    def save_snapshots(self, snapshots: List[PropLineSnapshot]) -> int:
        """
        Save prop line snapshots to the database.
        
        Args:
            snapshots: List of PropLineSnapshot objects
            
        Returns:
            Number of snapshots saved
        """
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


async def main():
    """Example usage of the OddsAPICollector."""
    from datetime import timezone
    
    # Example: Collect props for a specific week
    week_start = datetime(2024, 12, 17, tzinfo=timezone.utc)
    week_end = datetime(2024, 12, 23, tzinfo=timezone.utc)
    
    async with OddsAPICollector() as collector:
        snapshots = await collector.collect_week_props(week_start, week_end)
        print(f"Collected {len(snapshots)} prop snapshots")
        
        if snapshots:
            saved = collector.save_snapshots(snapshots)
            print(f"Saved {saved} snapshots to database")


if __name__ == "__main__":
    asyncio.run(main())

