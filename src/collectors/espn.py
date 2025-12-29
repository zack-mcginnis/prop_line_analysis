"""ESPN API client for fetching actual player game statistics."""

import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings
from src.models.database import PlayerGameStats, get_session


class ESPNCollector:
    """
    Client for ESPN API to collect actual player game statistics.
    
    Used to compare player performance against prop lines.
    """
    
    ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
    ESPN_SCOREBOARD = f"{ESPN_API_BASE}/scoreboard"
    ESPN_SUMMARY = f"{ESPN_API_BASE}/summary"
    
    def __init__(self):
        self.settings = get_settings()
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
    async def get_game_summary(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed game summary including player stats.
        
        Args:
            event_id: ESPN event ID
            
        Returns:
            Game summary data or None if not found
        """
        params = {"event": event_id}
        
        response = await self.client.get(self.ESPN_SUMMARY, params=params)
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        return response.json()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_week_scores(
        self,
        season: int,
        week: int,
        season_type: int = 2,  # 2 = regular season
    ) -> List[Dict[str, Any]]:
        """
        Get all game scores/events for a specific week.
        
        Args:
            season: NFL season year
            week: Week number (1-18)
            season_type: 1=preseason, 2=regular, 3=postseason
            
        Returns:
            List of event dicts
        """
        params = {
            "dates": season,
            "seasontype": season_type,
            "week": week,
        }
        
        response = await self.client.get(self.ESPN_SCOREBOARD, params=params)
        response.raise_for_status()
        data = response.json()
        
        return data.get("events", [])
    
    def _extract_player_stats(
        self,
        game_data: Dict[str, Any],
        event_id: str,
        game_date: datetime,
        season: int,
        week: int,
    ) -> List[PlayerGameStats]:
        """
        Extract player rushing and receiving stats from game data.
        
        Args:
            game_data: ESPN game summary data
            event_id: Event ID
            game_date: Game date/time
            season: NFL season
            week: NFL week
            
        Returns:
            List of PlayerGameStats objects
        """
        stats_list = []
        
        # Get boxscore data
        boxscore = game_data.get("boxscore", {})
        players_data = boxscore.get("players", [])
        
        # Get team info
        teams_info = {}
        for team_data in players_data:
            team = team_data.get("team", {})
            team_id = team.get("id")
            team_name = team.get("displayName")
            team_abbr = team.get("abbreviation")
            is_home = team_data.get("homeAway") == "home"
            
            if team_id:
                teams_info[team_id] = {
                    "name": team_name,
                    "abbr": team_abbr,
                    "is_home": is_home,
                }
        
        # Process each team's players
        for team_data in players_data:
            team = team_data.get("team", {})
            team_id = team.get("id")
            team_name = team.get("displayName")
            team_abbr = team.get("abbreviation")
            is_home = team_data.get("homeAway") == "home"
            
            # Find opponent
            opponent = None
            for tid, tinfo in teams_info.items():
                if tid != team_id:
                    opponent = tinfo.get("name")
                    break
            
            # Process stat categories
            player_stats: Dict[str, Dict[str, Any]] = {}
            
            for stat_category in team_data.get("statistics", []):
                category_name = stat_category.get("name", "")
                
                # We care about rushing and receiving
                if category_name not in ["rushing", "receiving"]:
                    continue
                
                # Get stat labels (column headers)
                labels = stat_category.get("labels", [])
                
                for athlete in stat_category.get("athletes", []):
                    athlete_data = athlete.get("athlete", {})
                    player_id = athlete_data.get("id")
                    player_name = athlete_data.get("displayName")
                    
                    if not player_id or not player_name:
                        continue
                    
                    # Initialize player entry if needed
                    if player_id not in player_stats:
                        player_stats[player_id] = {
                            "player_id": player_id,
                            "player_name": player_name,
                            "team": team_name,
                            "team_abbr": team_abbr,
                            "is_home": is_home,
                            "opponent": opponent,
                            "rushing_attempts": None,
                            "rushing_yards": None,
                            "rushing_tds": None,
                            "receptions": None,
                            "receiving_targets": None,
                            "receiving_yards": None,
                            "receiving_tds": None,
                        }
                    
                    # Parse stats
                    stat_values = athlete.get("stats", [])
                    
                    for i, label in enumerate(labels):
                        if i >= len(stat_values):
                            break
                        
                        value = stat_values[i]
                        
                        # Parse numeric values
                        try:
                            if value == "--" or value == "":
                                num_value = 0
                            else:
                                num_value = int(float(value))
                        except (ValueError, TypeError):
                            num_value = 0
                        
                        # Map labels to fields
                        label_lower = label.lower()
                        
                        if category_name == "rushing":
                            if label_lower in ["car", "att", "attempts"]:
                                player_stats[player_id]["rushing_attempts"] = num_value
                            elif label_lower in ["yds", "yards"]:
                                player_stats[player_id]["rushing_yards"] = num_value
                            elif label_lower in ["td", "tds", "touchdowns"]:
                                player_stats[player_id]["rushing_tds"] = num_value
                        
                        elif category_name == "receiving":
                            if label_lower in ["rec", "receptions"]:
                                player_stats[player_id]["receptions"] = num_value
                            elif label_lower in ["tgt", "targets"]:
                                player_stats[player_id]["receiving_targets"] = num_value
                            elif label_lower in ["yds", "yards"]:
                                player_stats[player_id]["receiving_yards"] = num_value
                            elif label_lower in ["td", "tds", "touchdowns"]:
                                player_stats[player_id]["receiving_tds"] = num_value
            
            # Create PlayerGameStats objects
            for player_id, stats in player_stats.items():
                # Skip players with no rushing or receiving stats
                if (
                    stats["rushing_yards"] is None
                    and stats["receiving_yards"] is None
                ):
                    continue
                
                player_stat = PlayerGameStats(
                    event_id=event_id,
                    game_date=game_date,
                    season=season,
                    week=week,
                    player_name=stats["player_name"],
                    player_id=stats["player_id"],
                    team=stats["team"],
                    opponent=stats["opponent"],
                    rushing_attempts=stats["rushing_attempts"],
                    rushing_yards=stats["rushing_yards"],
                    rushing_tds=stats["rushing_tds"],
                    receptions=stats["receptions"],
                    receiving_targets=stats["receiving_targets"],
                    receiving_yards=stats["receiving_yards"],
                    receiving_tds=stats["receiving_tds"],
                    is_home=stats["is_home"],
                )
                stats_list.append(player_stat)
        
        return stats_list
    
    async def collect_game_stats(
        self,
        event_id: str,
        season: int,
        week: int,
    ) -> List[PlayerGameStats]:
        """
        Collect player stats for a specific game.
        
        Args:
            event_id: ESPN event ID
            season: NFL season
            week: NFL week
            
        Returns:
            List of PlayerGameStats objects
        """
        game_data = await self.get_game_summary(event_id)
        
        if not game_data:
            return []
        
        # Get game date from header
        header = game_data.get("header", {})
        competitions = header.get("competitions", [{}])
        game_date_str = competitions[0].get("date") if competitions else None
        
        game_date = datetime.now(timezone.utc)
        if game_date_str:
            try:
                game_date = datetime.fromisoformat(
                    game_date_str.replace("Z", "+00:00")
                )
            except ValueError:
                pass
        
        return self._extract_player_stats(
            game_data=game_data,
            event_id=event_id,
            game_date=game_date,
            season=season,
            week=week,
        )
    
    async def collect_week_stats(
        self,
        season: int,
        week: int,
    ) -> List[PlayerGameStats]:
        """
        Collect player stats for all games in a week.
        
        Args:
            season: NFL season year
            week: NFL week number
            
        Returns:
            List of all PlayerGameStats objects for the week
        """
        all_stats = []
        
        events = await self.get_week_scores(season, week)
        
        for event in events:
            event_id = event.get("id")
            status = event.get("status", {}).get("type", {}).get("name")
            
            # Only collect stats for completed games
            if status != "STATUS_FINAL":
                continue
            
            if not event_id:
                continue
            
            try:
                stats = await self.collect_game_stats(event_id, season, week)
                all_stats.extend(stats)
            except Exception as e:
                print(f"Error collecting stats for event {event_id}: {e}")
            
            # Small delay between requests
            await asyncio.sleep(0.5)
        
        return all_stats
    
    async def collect_season_stats(
        self,
        season: int,
        start_week: int = 1,
        end_week: int = 18,
    ) -> List[PlayerGameStats]:
        """
        Collect player stats for an entire season or range of weeks.
        
        Args:
            season: NFL season year
            start_week: First week to collect
            end_week: Last week to collect
            
        Returns:
            List of all PlayerGameStats objects
        """
        all_stats = []
        
        for week in range(start_week, end_week + 1):
            print(f"Collecting week {week} stats...")
            
            try:
                stats = await self.collect_week_stats(season, week)
                all_stats.extend(stats)
                print(f"  Collected {len(stats)} player stats")
            except Exception as e:
                print(f"  Error collecting week {week}: {e}")
            
            # Delay between weeks
            await asyncio.sleep(1.0)
        
        return all_stats
    
    def save_stats(self, stats: List[PlayerGameStats]) -> int:
        """
        Save player game stats to the database.
        
        Args:
            stats: List of PlayerGameStats objects
            
        Returns:
            Number of stats saved
        """
        if not stats:
            return 0
        
        session = get_session()
        try:
            # Upsert logic: check for existing records
            for stat in stats:
                existing = session.query(PlayerGameStats).filter(
                    PlayerGameStats.event_id == stat.event_id,
                    PlayerGameStats.player_name == stat.player_name,
                ).first()
                
                if existing:
                    # Update existing record
                    for key, value in {
                        "rushing_attempts": stat.rushing_attempts,
                        "rushing_yards": stat.rushing_yards,
                        "rushing_tds": stat.rushing_tds,
                        "receptions": stat.receptions,
                        "receiving_targets": stat.receiving_targets,
                        "receiving_yards": stat.receiving_yards,
                        "receiving_tds": stat.receiving_tds,
                    }.items():
                        if value is not None:
                            setattr(existing, key, value)
                else:
                    session.add(stat)
            
            session.commit()
            return len(stats)
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()


async def main():
    """Example usage of ESPNCollector."""
    async with ESPNCollector() as collector:
        # Collect stats for a specific week
        season = 2024
        week = 15
        
        print(f"Collecting stats for {season} Week {week}...")
        stats = await collector.collect_week_stats(season, week)
        
        print(f"Collected {len(stats)} player stat records")
        
        # Show some examples
        for stat in stats[:10]:
            rush = stat.rushing_yards or 0
            rec = stat.receiving_yards or 0
            print(f"  {stat.player_name}: Rush={rush}, Rec={rec}")


if __name__ == "__main__":
    asyncio.run(main())

