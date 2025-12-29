"""BettingPros scraper for real-time player prop data collection."""

import asyncio
import hashlib
import json
import random
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings
from src.models.database import (
    PropLineSnapshot,
    PropType,
    DataSource,
    get_session,
)


# Realistic User-Agent strings for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# Accept-Language variations
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-US,en;q=0.9,es;q=0.8",
    "en-GB,en;q=0.9,en-US;q=0.8",
    "en-US,en;q=0.8",
    "en,en-US;q=0.9",
]


class BettingProsCollector:
    """
    Scraper for BettingPros player prop data.
    
    URL Pattern: https://www.bettingpros.com/nfl/props/{player-slug}/{prop-type}/
    Prop types: rushing-yards, receiving-yards
    """
    
    BASE_URL = "https://www.bettingpros.com"
    API_BASE_URL = "https://api.bettingpros.com/v3"
    
    PROP_TYPE_MAPPING = {
        "rushing-yards": PropType.RUSHING_YARDS,
        "receiving-yards": PropType.RECEIVING_YARDS,
    }
    
    PROP_TYPE_REVERSE = {
        PropType.RUSHING_YARDS: "rushing-yards",
        PropType.RECEIVING_YARDS: "receiving-yards",
    }
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._last_content_hashes: Dict[str, str] = {}  # For deduplication
        self._semaphore = asyncio.Semaphore(self.settings.max_concurrent_requests)
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            http2=True,
        )
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
    
    def _get_rotating_headers(self) -> Dict[str, str]:
        """Get headers with rotating User-Agent and other fingerprints."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
    
    def _get_api_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json",
            "Accept-Language": random.choice(ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": f"{self.BASE_URL}/nfl/props/",
            "Origin": self.BASE_URL,
            "x-api-key": "CHi8Hy5CEE4khd46XNYL23dCFX96oUdw6qOt1Dnh",  # Public API key from site
        }
    
    async def _random_delay(self):
        """Add a random delay between requests."""
        delay = random.uniform(
            self.settings.request_delay_min,
            self.settings.request_delay_max,
        )
        await asyncio.sleep(delay)
    
    def _content_hash(self, content: str) -> str:
        """Generate a hash of content for deduplication."""
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_duplicate(self, player_slug: str, prop_type: str, content_hash: str) -> bool:
        """Check if content is duplicate of last scrape."""
        key = f"{player_slug}_{prop_type}"
        if key in self._last_content_hashes:
            if self._last_content_hashes[key] == content_hash:
                return True
        self._last_content_hashes[key] = content_hash
        return False
    
    def _player_name_to_slug(self, player_name: str) -> str:
        """Convert player name to URL slug format."""
        # "Patrick Mahomes" -> "patrick-mahomes"
        return player_name.lower().replace(" ", "-").replace(".", "").replace("'", "")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch a page with retry logic.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content or None if failed
        """
        async with self._semaphore:
            try:
                response = await self.client.get(url, headers=self._get_rotating_headers())
                
                if response.status_code == 429:
                    # Rate limited - wait longer
                    await asyncio.sleep(30)
                    raise httpx.HTTPStatusError(
                        "Rate limited", request=response.request, response=response
                    )
                
                response.raise_for_status()
                await self._random_delay()
                return response.text
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None  # Player/prop not found
                raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _fetch_api(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Fetch from BettingPros API.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            JSON response or None if failed
        """
        async with self._semaphore:
            try:
                url = f"{self.API_BASE_URL}{endpoint}"
                response = await self.client.get(
                    url,
                    headers=self._get_api_headers(),
                    params=params,
                )
                
                if response.status_code == 429:
                    await asyncio.sleep(30)
                    raise httpx.HTTPStatusError(
                        "Rate limited", request=response.request, response=response
                    )
                
                response.raise_for_status()
                await self._random_delay()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise
    
    def _parse_prop_page(
        self,
        html: str,
        player_name: str,
        prop_type: PropType,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse player prop page HTML to extract line data.
        
        Args:
            html: Page HTML content
            player_name: Player name
            prop_type: Type of prop
            
        Returns:
            Parsed prop data or None if parsing failed
        """
        soup = BeautifulSoup(html, "lxml")
        
        result = {
            "player_name": player_name,
            "prop_type": prop_type,
            "consensus_line": None,
            "draftkings_line": None,
            "fanduel_line": None,
            "betmgm_line": None,
            "caesars_line": None,
            "pointsbet_line": None,
            "source_timestamp": None,
        }
        
        # Look for the prop lines container
        # BettingPros uses React, so we need to find the data in script tags or DOM
        
        # Try to find consensus line in the header/summary area
        consensus_elem = soup.select_one('[data-testid="consensus-line"], .consensus-value, .prop-line-value')
        if consensus_elem:
            try:
                line_text = consensus_elem.get_text(strip=True)
                # Extract number from text like "52.5" or "O/U 52.5"
                import re
                match = re.search(r'(\d+\.?\d*)', line_text)
                if match:
                    result["consensus_line"] = Decimal(match.group(1))
            except (ValueError, AttributeError):
                pass
        
        # Look for sportsbook-specific lines
        sportsbook_mapping = {
            "draftkings": "draftkings_line",
            "fanduel": "fanduel_line",
            "betmgm": "betmgm_line",
            "caesars": "caesars_line",
            "pointsbet": "pointsbet_line",
        }
        
        # Find sportsbook rows/cards
        for book_key, field_name in sportsbook_mapping.items():
            book_elem = soup.select_one(
                f'[data-sportsbook="{book_key}"], '
                f'.sportsbook-{book_key}, '
                f'[class*="{book_key}"]'
            )
            if book_elem:
                line_elem = book_elem.select_one('.line-value, .odds-value, [class*="line"]')
                if line_elem:
                    try:
                        import re
                        line_text = line_elem.get_text(strip=True)
                        match = re.search(r'(\d+\.?\d*)', line_text)
                        if match:
                            result[field_name] = Decimal(match.group(1))
                    except (ValueError, AttributeError):
                        pass
        
        # Try to find timestamp in tooltips or data attributes
        timestamp_elem = soup.select_one('[data-timestamp], [title*="Updated"], .last-updated')
        if timestamp_elem:
            timestamp_str = timestamp_elem.get('data-timestamp') or timestamp_elem.get('title', '')
            # Parse timestamp if found
            # This would need more specific parsing based on actual format
        
        # Check if we found any data
        if result["consensus_line"] is None and all(
            result[f] is None for f in sportsbook_mapping.values()
        ):
            return None
        
        return result
    
    async def scrape_player_prop(
        self,
        player_name: str,
        prop_type: PropType,
        event_id: Optional[str] = None,
        game_commence_time: Optional[datetime] = None,
    ) -> Optional[PropLineSnapshot]:
        """
        Scrape prop data for a specific player and prop type.
        
        Args:
            player_name: Full player name
            prop_type: Type of prop (rushing/receiving yards)
            event_id: Optional game event ID
            game_commence_time: Optional game start time
            
        Returns:
            PropLineSnapshot or None if scraping failed
        """
        player_slug = self._player_name_to_slug(player_name)
        prop_slug = self.PROP_TYPE_REVERSE[prop_type]
        
        url = f"{self.BASE_URL}/nfl/props/{player_slug}/{prop_slug}/"
        
        html = await self._fetch_page(url)
        if not html:
            return None
        
        # Check for duplicate content
        content_hash = self._content_hash(html)
        if self._is_duplicate(player_slug, prop_slug, content_hash):
            return None  # Skip duplicate
        
        # Parse the page
        prop_data = self._parse_prop_page(html, player_name, prop_type)
        if not prop_data:
            return None
        
        # Calculate hours before kickoff if we have game time
        hours_before = None
        if game_commence_time:
            now = datetime.now(timezone.utc)
            delta = game_commence_time - now
            hours_before = Decimal(str(round(delta.total_seconds() / 3600, 2)))
        
        # Create snapshot
        snapshot = PropLineSnapshot(
            event_id=event_id or "",
            game_commence_time=game_commence_time or datetime.now(timezone.utc),
            player_name=player_name,
            player_slug=player_slug,
            prop_type=prop_type,
            consensus_line=prop_data.get("consensus_line"),
            draftkings_line=prop_data.get("draftkings_line"),
            fanduel_line=prop_data.get("fanduel_line"),
            betmgm_line=prop_data.get("betmgm_line"),
            caesars_line=prop_data.get("caesars_line"),
            pointsbet_line=prop_data.get("pointsbet_line"),
            snapshot_time=datetime.now(timezone.utc),
            source_timestamp=prop_data.get("source_timestamp"),
            hours_before_kickoff=hours_before,
            source=DataSource.BETTINGPROS,
            raw_data=json.dumps({"html_hash": content_hash}),
        )
        
        return snapshot
    
    async def scrape_all_players(
        self,
        players: List[Dict[str, Any]],
        prop_types: Optional[List[PropType]] = None,
    ) -> List[PropLineSnapshot]:
        """
        Scrape props for all players in the list.
        
        Args:
            players: List of player dicts with 'name', 'event_id', 'game_commence_time'
            prop_types: List of prop types to scrape (defaults to both)
            
        Returns:
            List of PropLineSnapshot objects
        """
        if prop_types is None:
            prop_types = [PropType.RUSHING_YARDS, PropType.RECEIVING_YARDS]
        
        snapshots = []
        
        for player in players:
            for prop_type in prop_types:
                try:
                    snapshot = await self.scrape_player_prop(
                        player_name=player["name"],
                        prop_type=prop_type,
                        event_id=player.get("event_id"),
                        game_commence_time=player.get("game_commence_time"),
                    )
                    if snapshot:
                        snapshots.append(snapshot)
                except Exception as e:
                    print(f"Error scraping {player['name']} {prop_type.value}: {e}")
        
        return snapshots
    
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
    """Example usage of the BettingProsCollector."""
    # Example players to scrape
    players = [
        {
            "name": "Saquon Barkley",
            "event_id": "test_event_1",
            "game_commence_time": datetime(2024, 12, 29, 18, 0, tzinfo=timezone.utc),
        },
        {
            "name": "Derrick Henry",
            "event_id": "test_event_2",
            "game_commence_time": datetime(2024, 12, 29, 18, 0, tzinfo=timezone.utc),
        },
    ]
    
    async with BettingProsCollector() as collector:
        snapshots = await collector.scrape_all_players(players)
        print(f"Scraped {len(snapshots)} prop snapshots")
        
        for snapshot in snapshots:
            print(f"  {snapshot.player_name}: {snapshot.prop_type.value} = {snapshot.consensus_line}")


if __name__ == "__main__":
    asyncio.run(main())

