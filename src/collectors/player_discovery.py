"""Player discovery module for finding players with available props."""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings


# NFL team abbreviations to full names
NFL_TEAMS = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LV": "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers",
    "SEA": "Seattle Seahawks",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}


class PlayerDiscovery:
    """
    Discovers NFL players with available props for scraping.
    
    Uses ESPN API to get weekly schedule and team rosters to identify
    skill position players who are likely to have props.
    """
    
    ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
    ESPN_SCOREBOARD = f"{ESPN_API_BASE}/scoreboard"
    ESPN_TEAMS = f"{ESPN_API_BASE}/teams"
    
    # Positions that typically have rushing/receiving props
    SKILL_POSITIONS = {"RB", "WR", "TE", "QB", "FB"}
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._player_cache: Dict[str, List[Dict]] = {}
        self._cache_expiry: Optional[datetime] = None
    
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
    
    def _is_cache_valid(self) -> bool:
        """Check if the player cache is still valid."""
        if self._cache_expiry is None or not self._player_cache:
            return False
        return datetime.now(timezone.utc) < self._cache_expiry
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_weekly_schedule(self, week: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get the NFL schedule for a specific week.
        
        Args:
            week: NFL week number (1-18, or None for current)
            
        Returns:
            List of game dicts with team info and game times
        """
        params = {}
        if week:
            params["week"] = week
        
        response = await self.client.get(self.ESPN_SCOREBOARD, params=params)
        response.raise_for_status()
        data = response.json()
        
        games = []
        for event in data.get("events", []):
            competition = event.get("competitions", [{}])[0]
            competitors = competition.get("competitors", [])
            
            if len(competitors) != 2:
                continue
            
            home_team = None
            away_team = None
            for comp in competitors:
                team_data = comp.get("team", {})
                if comp.get("homeAway") == "home":
                    home_team = {
                        "id": team_data.get("id"),
                        "abbreviation": team_data.get("abbreviation"),
                        "name": team_data.get("displayName"),
                    }
                else:
                    away_team = {
                        "id": team_data.get("id"),
                        "abbreviation": team_data.get("abbreviation"),
                        "name": team_data.get("displayName"),
                    }
            
            if home_team and away_team:
                game_time_str = event.get("date")
                game_time = None
                if game_time_str:
                    try:
                        game_time = datetime.fromisoformat(
                            game_time_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass
                
                games.append({
                    "event_id": event.get("id"),
                    "name": event.get("name"),
                    "game_commence_time": game_time,
                    "home_team": home_team,
                    "away_team": away_team,
                    "status": event.get("status", {}).get("type", {}).get("name"),
                })
        
        return games
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_team_roster(self, team_id: str) -> List[Dict[str, Any]]:
        """
        Get the roster for a specific team.
        
        Args:
            team_id: ESPN team ID
            
        Returns:
            List of player dicts with name, position, etc.
        """
        url = f"{self.ESPN_TEAMS}/{team_id}/roster"
        
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        
        players = []
        for athlete in data.get("athletes", []):
            for player in athlete.get("items", []):
                position = player.get("position", {}).get("abbreviation", "")
                
                if position in self.SKILL_POSITIONS:
                    players.append({
                        "id": player.get("id"),
                        "name": player.get("fullName"),
                        "position": position,
                        "jersey": player.get("jersey"),
                        "team_id": team_id,
                    })
        
        return players
    
    async def get_players_for_game(
        self,
        game: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Get skill position players for both teams in a game.
        
        Args:
            game: Game dict from get_weekly_schedule
            
        Returns:
            List of player dicts with game context
        """
        players = []
        
        for team_key in ["home_team", "away_team"]:
            team = game.get(team_key, {})
            team_id = team.get("id")
            
            if not team_id:
                continue
            
            try:
                roster = await self.get_team_roster(team_id)
                
                for player in roster:
                    players.append({
                        "name": player["name"],
                        "position": player["position"],
                        "team": team.get("name"),
                        "team_abbr": team.get("abbreviation"),
                        "event_id": game.get("event_id"),
                        "game_commence_time": game.get("game_commence_time"),
                        "is_home": team_key == "home_team",
                        "opponent": game.get(
                            "away_team" if team_key == "home_team" else "home_team",
                            {}
                        ).get("name"),
                    })
            except Exception as e:
                print(f"Error getting roster for team {team_id}: {e}")
        
        return players
    
    async def get_weekly_players(
        self,
        week: Optional[int] = None,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get all skill position players for the week's games.
        
        Args:
            week: NFL week number (or None for current)
            use_cache: Whether to use cached results
            
        Returns:
            List of player dicts with game context
        """
        cache_key = f"week_{week or 'current'}"
        
        if use_cache and self._is_cache_valid() and cache_key in self._player_cache:
            return self._player_cache[cache_key]
        
        games = await self.get_weekly_schedule(week)
        all_players = []
        
        for game in games:
            # Skip completed games
            if game.get("status") == "STATUS_FINAL":
                continue
            
            players = await self.get_players_for_game(game)
            all_players.extend(players)
            
            # Small delay between roster requests
            await asyncio.sleep(0.5)
        
        # Cache results for 1 hour
        self._player_cache[cache_key] = all_players
        self._cache_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        
        return all_players
    
    def filter_players_by_position(
        self,
        players: List[Dict[str, Any]],
        positions: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter players by position.
        
        Args:
            players: List of player dicts
            positions: List of positions to include (e.g., ["RB", "WR"])
            
        Returns:
            Filtered list of players
        """
        if positions is None:
            return players
        
        return [p for p in players if p.get("position") in positions]
    
    def get_players_for_scraping(
        self,
        players: List[Dict[str, Any]],
        hours_before_kickoff: float = 12.0,
    ) -> List[Dict[str, Any]]:
        """
        Filter players whose games are within the scraping window.
        
        Args:
            players: List of player dicts
            hours_before_kickoff: Start scraping this many hours before kickoff
            
        Returns:
            Players whose games are in the scraping window
        """
        now = datetime.now(timezone.utc)
        window_start = now
        window_end = now + timedelta(hours=hours_before_kickoff)
        
        result = []
        for player in players:
            game_time = player.get("game_commence_time")
            if game_time is None:
                continue
            
            # Check if game is in the scraping window
            # Game should be upcoming and within our hours_before_kickoff window
            if game_time > now and game_time <= window_end:
                result.append(player)
        
        return result


async def main():
    """Example usage of PlayerDiscovery."""
    async with PlayerDiscovery() as discovery:
        # Get current week's players
        players = await discovery.get_weekly_players()
        print(f"Found {len(players)} skill position players")
        
        # Filter to RBs and WRs only
        rb_wr = discovery.filter_players_by_position(players, ["RB", "WR"])
        print(f"RBs and WRs: {len(rb_wr)}")
        
        # Show some examples
        for player in rb_wr[:10]:
            print(f"  {player['name']} ({player['position']}) - {player['team']}")


if __name__ == "__main__":
    asyncio.run(main())

