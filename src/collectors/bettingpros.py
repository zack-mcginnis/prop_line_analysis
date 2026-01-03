"""BettingPros scraper for real-time player prop data collection via API."""

import asyncio
import brotli
import gzip
import json
import logging
import random
from datetime import datetime, timezone
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

# Configure logger
logger = logging.getLogger(__name__)


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
    
    # Market IDs for different prop types (from BettingPros API)
    MARKET_IDS = {
        PropType.RUSHING_YARDS: "107",
        PropType.RECEIVING_YARDS: "105",
    }
    
    # Sportsbook IDs (from BettingPros API)
    BOOK_IDS = {
        0: "consensus",
        10: "fanduel",
        12: "draftkings",
        19: "betmgm",
        13: "caesars",
        78: "pointsbet",
    }
    
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
    
    def _player_name_to_slug(self, player_name: str) -> str:
        """Convert player name to URL slug format."""
        # "Patrick Mahomes" -> "patrick-mahomes"
        try:
            # Handle unicode characters and special chars (like curly quotes)
            return player_name.lower().replace(" ", "-").replace(".", "").replace("'", "").replace("'", "")
        except (UnicodeDecodeError, AttributeError):
            # Fallback for problematic characters
            return str(player_name).encode('ascii', 'ignore').decode('ascii').lower().replace(" ", "-")
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
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
                    timeout=30.0,  # Add explicit timeout
                )
                
                if response.status_code == 429:
                    logger.warning(f"  ⚠ Rate limited, waiting 30s...")
                    await asyncio.sleep(30)
                    raise httpx.HTTPStatusError(
                        "Rate limited", request=response.request, response=response
                    )
                
                response.raise_for_status()
                await self._random_delay()
                
                # Check if response needs manual decompression
                content_encoding = response.headers.get('content-encoding', '').lower()
                raw_content = response.content
                
                # Manually decompress if needed (httpx usually handles this, but not always for Brotli)
                # Check if the content is actually compressed by looking at the first bytes
                if content_encoding == 'br' and not raw_content.startswith(b'{') and not raw_content.startswith(b'['):
                    try:
                        logger.debug(f"  🔓 Manually decompressing Brotli data ({len(raw_content)} bytes)")
                        raw_content = brotli.decompress(raw_content)
                        logger.debug(f"  ✓ Decompressed to {len(raw_content)} bytes")
                    except Exception as decompress_err:
                        # Only warn if this looks like it should be compressed
                        if not raw_content.startswith(b'{') and not raw_content.startswith(b'['):
                            logger.debug(f"  ⚠ Brotli decompression failed: {decompress_err}")
                        # Continue - might already be decompressed
                elif content_encoding == 'gzip' and not raw_content.startswith(b'{') and not raw_content.startswith(b'['):
                    # Check for GZIP magic number
                    if raw_content.startswith(b'\x1f\x8b'):
                        try:
                            logger.debug(f"  🔓 Manually decompressing GZIP data ({len(raw_content)} bytes)")
                            raw_content = gzip.decompress(raw_content)
                            logger.debug(f"  ✓ Decompressed to {len(raw_content)} bytes")
                        except Exception as decompress_err:
                            logger.debug(f"  ⚠ GZIP decompression failed: {decompress_err}")
                
                # Try to decode the response with error handling for encoding issues
                try:
                    # First try to parse as JSON directly
                    if isinstance(raw_content, bytes):
                        decoded_text = raw_content.decode('utf-8')
                    else:
                        decoded_text = raw_content
                    return json.loads(decoded_text)
                except (UnicodeDecodeError, json.JSONDecodeError) as decode_err:
                    # Log diagnostic information about the problematic response
                    logger.warning(f"  ⚠ Decode error: {decode_err}")
                    logger.warning(f"  📊 Response diagnostics for {endpoint}:")
                    logger.warning(f"     • Status code: {response.status_code}")
                    logger.warning(f"     • Content-Type: {response.headers.get('content-type', 'not set')}")
                    logger.warning(f"     • Content-Encoding: {content_encoding or 'not set'}")
                    logger.warning(f"     • Content-Length: {len(response.content)} bytes")
                    logger.warning(f"     • Decompressed size: {len(raw_content)} bytes")
                    
                    # Show first 100 bytes in hex format to see what we're dealing with
                    hex_preview = ' '.join(f'{b:02x}' for b in raw_content[:50])
                    logger.warning(f"     • First 50 bytes (hex): {hex_preview}")
                    
                    # Try to identify the data type
                    if raw_content.startswith(b'\x1f\x8b'):
                        logger.warning(f"     • Data appears to be GZIP compressed (not decompressed)")
                    elif raw_content.startswith(b'PK'):
                        logger.warning(f"     • Data appears to be ZIP compressed")
                    elif raw_content.startswith(b'{') or raw_content.startswith(b'['):
                        logger.warning(f"     • Data appears to be JSON but with encoding issues")
                    else:
                        logger.warning(f"     • Data type: Unknown binary format")
                    
                    try:
                        # Try decoding with latin-1 (accepts all byte values)
                        if isinstance(raw_content, bytes):
                            content = raw_content.decode('latin-1', errors='replace')
                        else:
                            content = raw_content
                        return json.loads(content)
                    except Exception as fallback_err:
                        logger.warning(f"  ⚠ Fallback decode also failed: {fallback_err}")
                        # Return None to skip this response rather than failing completely
                        return None
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                logger.warning(f"  ⚠ HTTP error {e.response.status_code}: {e}")
                raise
            except httpx.TimeoutException as e:
                logger.warning(f"  ⚠ Request timeout: {e}")
                raise
            except Exception as e:
                logger.warning(f"  ⚠ Unexpected error: {type(e).__name__}: {e}")
                raise
    
    def _parse_api_offer(
        self,
        offer: Dict[str, Any],
        player_name: str,
        prop_type: PropType,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse player prop offer data from BettingPros API.
        
        Args:
            offer: Offer dict from API response
            player_name: Player name
            prop_type: Type of prop
            
        Returns:
            Parsed prop data dict or None
        """
        result = {
            "player_name": player_name,
            "prop_type": prop_type,
            "consensus_line": None,
            "draftkings_line": None,
            "fanduel_line": None,
            "betmgm_line": None,
            "caesars_line": None,
            "pointsbet_line": None,
            "consensus_over_odds": None,
            "consensus_under_odds": None,
            "draftkings_over_odds": None,
            "draftkings_under_odds": None,
            "fanduel_over_odds": None,
            "fanduel_under_odds": None,
            "betmgm_over_odds": None,
            "betmgm_under_odds": None,
            "caesars_over_odds": None,
            "caesars_under_odds": None,
            "pointsbet_over_odds": None,
            "pointsbet_under_odds": None,
            "consensus_timestamp": None,
            "draftkings_timestamp": None,
            "fanduel_timestamp": None,
            "betmgm_timestamp": None,
            "caesars_timestamp": None,
            "pointsbet_timestamp": None,
            "source_timestamp": None,
        }
        
        # Get the "Over" and "Under" selections
        selections = offer.get('selections', [])
        if not selections:
            logger.debug(f"      No selections in offer")
            return None
        
        # Debug: Log the structure of selections
        logger.debug(f"      Found {len(selections)} selection(s)")
        
        # Find the Over and Under selections
        over_selection = None
        under_selection = None
        for sel in selections:
            selection_type = sel.get('selection')
            logger.debug(f"      Selection type: {selection_type}")
            if selection_type == 'over':
                over_selection = sel
            elif selection_type == 'under':
                under_selection = sel
        
        if not over_selection:
            logger.debug(f"      No 'over' selection found")
            return None
        
        # Extract lines and odds from each sportsbook (using over selection)
        books = over_selection.get('books', [])
        latest_timestamp = None
        
        for book in books:
            book_id = book.get('id')
            lines = book.get('lines', [])
            
            if not lines:
                continue
            
            # Get the main line (first one, or one marked as main=True)
            line_data = None
            for line in lines:
                if line.get('main', False) or line == lines[0]:
                    line_data = line
                    break
            
            if not line_data:
                continue
            
            line_value = line_data.get('line')
            odds_value = line_data.get('cost')  # American odds for over (field is 'cost' not 'odds')
            updated_str = line_data.get('updated')
            
            # Parse timestamp string to datetime object
            # Format: '2026-01-03 14:53:38'
            updated = None
            if updated_str:
                try:
                    updated = datetime.strptime(updated_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                except (ValueError, AttributeError):
                    logger.debug(f"      Could not parse timestamp: {updated_str}")
            
            if line_value is None:
                continue
            
            # Track latest timestamp
            if updated and (not latest_timestamp or updated > latest_timestamp):
                latest_timestamp = updated
            
            # Map book_id to field name and save line + over odds + timestamp
            if book_id == 0:  # Consensus
                result['consensus_line'] = Decimal(str(line_value))
                result['consensus_timestamp'] = updated
                if odds_value is not None:
                    result['consensus_over_odds'] = int(odds_value)
                    logger.debug(f"      Consensus: {line_value} @ {odds_value} (over odds set)")
                else:
                    logger.debug(f"      Consensus: {line_value} @ None (no over odds in API)")
            elif book_id == 12:  # DraftKings
                result['draftkings_line'] = Decimal(str(line_value))
                result['draftkings_timestamp'] = updated
                if odds_value is not None:
                    result['draftkings_over_odds'] = int(odds_value)
            elif book_id == 10:  # FanDuel
                result['fanduel_line'] = Decimal(str(line_value))
                result['fanduel_timestamp'] = updated
                if odds_value is not None:
                    result['fanduel_over_odds'] = int(odds_value)
            elif book_id == 19:  # BetMGM
                result['betmgm_line'] = Decimal(str(line_value))
                result['betmgm_timestamp'] = updated
                if odds_value is not None:
                    result['betmgm_over_odds'] = int(odds_value)
            elif book_id == 13:  # Caesars
                result['caesars_line'] = Decimal(str(line_value))
                result['caesars_timestamp'] = updated
                if odds_value is not None:
                    result['caesars_over_odds'] = int(odds_value)
            elif book_id == 78:  # PointsBet
                result['pointsbet_line'] = Decimal(str(line_value))
                result['pointsbet_timestamp'] = updated
                if odds_value is not None:
                    result['pointsbet_over_odds'] = int(odds_value)
        
        # Extract under odds from under selection (all books)
        if under_selection:
            under_books = under_selection.get('books', [])
            logger.debug(f"      Found {len(under_books)} book(s) in under selection")
            for book in under_books:
                book_id = book.get('id')
                under_lines = book.get('lines', [])
                
                if not under_lines:
                    continue
                
                # Get the main line
                under_line_data = None
                for line in under_lines:
                    if line.get('main', False) or line == under_lines[0]:
                        under_line_data = line
                        break
                
                if under_line_data:
                    under_odds_value = under_line_data.get('cost')  # Field is 'cost' not 'odds'
                    if under_odds_value is not None:
                        # Map book_id to the appropriate field
                        if book_id == 0:  # Consensus
                            result['consensus_under_odds'] = int(under_odds_value)
                            logger.debug(f"      Consensus under odds: {under_odds_value}")
                        elif book_id == 12:  # DraftKings
                            result['draftkings_under_odds'] = int(under_odds_value)
                        elif book_id == 10:  # FanDuel
                            result['fanduel_under_odds'] = int(under_odds_value)
                        elif book_id == 19:  # BetMGM
                            result['betmgm_under_odds'] = int(under_odds_value)
                        elif book_id == 13:  # Caesars
                            result['caesars_under_odds'] = int(under_odds_value)
                        elif book_id == 78:  # PointsBet
                            result['pointsbet_under_odds'] = int(under_odds_value)
        else:
            logger.debug(f"      No under selection found in offer")
        
        result['source_timestamp'] = latest_timestamp
        
        # Check if we found any lines
        if result['consensus_line'] is None and all(
            result[f] is None for f in ['draftkings_line', 'fanduel_line', 'betmgm_line', 'caesars_line', 'pointsbet_line']
        ):
            logger.debug(f"      No prop lines found in API response")
            return None
        
        # Log final odds values for debugging
        if result['consensus_over_odds'] is None and result['consensus_under_odds'] is None:
            logger.info(f"      ⚠ WARNING: No consensus odds found for {player_name}")
        
        return result
    
    async def scrape_player_prop(
        self,
        player_name: str,
        prop_type: PropType,
        event_id: Optional[str] = None,
        game_commence_time: Optional[datetime] = None,
    ) -> Optional[PropLineSnapshot]:
        """
        Scrape prop data for a specific player and prop type using BettingPros API.
        
        Args:
            player_name: Full player name
            prop_type: Type of prop (rushing/receiving yards)
            event_id: Game event ID (required for API)
            game_commence_time: Game start time
            
        Returns:
            PropLineSnapshot or None if scraping failed
        """
        if not event_id:
            logger.warning(f"  ✗ No event_id provided for {player_name} - required for API")
            return None
        
        player_slug = self._player_name_to_slug(player_name)
        market_id = self.MARKET_IDS.get(prop_type)
        
        if not market_id:
            logger.error(f"  ✗ Unknown prop type: {prop_type}")
            return None
        
        logger.info(f"Scraping {player_name} ({prop_type.value}) via API")
        logger.debug(f"  Event ID: {event_id}, Market ID: {market_id}")
        
        # Fetch prop data from API
        endpoint = "/offers"
        params = {
            "market_id": market_id,
            "event_id": event_id,
        }
        
        api_data = await self._fetch_api(endpoint, params)
        if not api_data:
            logger.warning(f"  ✗ No API data returned for {player_name}")
            return None
        
        # Find the offer for this specific player
        offers = api_data.get('offers', [])
        player_offer = None
        
        for offer in offers:
            # Check if this offer is for our player
            participants = offer.get('participants', [])
            if participants:
                participant = participants[0]
                offer_player_name = participant.get('name', '')
                # Match by name (case-insensitive, normalized)
                if self._player_name_to_slug(offer_player_name) == player_slug:
                    player_offer = offer
                    break
        
        if not player_offer:
            logger.warning(f"  ✗ No offer found for {player_name} in API response ({len(offers)} total offers)")
            return None
        
        logger.debug(f"  ✓ Found offer for {player_name}")
        
        # Parse the offer data
        prop_data = self._parse_api_offer(player_offer, player_name, prop_type)
        if not prop_data:
            logger.warning(f"  ✗ Failed to parse API offer for {player_name}")
            return None
        
        logger.info(f"  ✓ Parsed data for {player_name}: consensus={prop_data.get('consensus_line')}")
        
        # Calculate hours before kickoff if we have game time
        hours_before = None
        if game_commence_time:
            now = datetime.now(timezone.utc)
            delta = game_commence_time - now
            hours_before = Decimal(str(round(delta.total_seconds() / 3600, 2)))
        
        # Create snapshot
        snapshot = PropLineSnapshot(
            event_id=event_id,
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
            consensus_over_odds=prop_data.get("consensus_over_odds"),
            consensus_under_odds=prop_data.get("consensus_under_odds"),
            draftkings_over_odds=prop_data.get("draftkings_over_odds"),
            draftkings_under_odds=prop_data.get("draftkings_under_odds"),
            fanduel_over_odds=prop_data.get("fanduel_over_odds"),
            fanduel_under_odds=prop_data.get("fanduel_under_odds"),
            betmgm_over_odds=prop_data.get("betmgm_over_odds"),
            betmgm_under_odds=prop_data.get("betmgm_under_odds"),
            caesars_over_odds=prop_data.get("caesars_over_odds"),
            caesars_under_odds=prop_data.get("caesars_under_odds"),
            pointsbet_over_odds=prop_data.get("pointsbet_over_odds"),
            pointsbet_under_odds=prop_data.get("pointsbet_under_odds"),
            consensus_timestamp=prop_data.get("consensus_timestamp"),
            draftkings_timestamp=prop_data.get("draftkings_timestamp"),
            fanduel_timestamp=prop_data.get("fanduel_timestamp"),
            betmgm_timestamp=prop_data.get("betmgm_timestamp"),
            caesars_timestamp=prop_data.get("caesars_timestamp"),
            pointsbet_timestamp=prop_data.get("pointsbet_timestamp"),
            snapshot_time=datetime.now(timezone.utc),
            source_timestamp=prop_data.get("source_timestamp"),
            hours_before_kickoff=hours_before,
            source=DataSource.BETTINGPROS,
            raw_data=json.dumps({
                "api_endpoint": "/offers",
                "market_id": market_id,
                "offer_id": player_offer.get('id'),
            }),
        )
        
        logger.info(f"  ✓ Created snapshot for {player_name}")
        return snapshot
    
    async def scrape_all_players(
        self,
        players: List[Dict[str, Any]],
        prop_types: Optional[List[PropType]] = None,
    ) -> List[PropLineSnapshot]:
        """
        Scrape props for all players in the list.
        
        OPTIMIZED: Groups players by event and fetches all offers for each event/market
        in a single API call, dramatically reducing the number of requests.
        
        Args:
            players: List of player dicts with 'name', 'bettingpros_event_id' or 'event_id', 
                     and 'game_commence_time'
            prop_types: List of prop types to scrape (defaults to both)
            
        Returns:
            List of PropLineSnapshot objects
        """
        if prop_types is None:
            prop_types = [PropType.RUSHING_YARDS, PropType.RECEIVING_YARDS]
        
        # Filter to only positions that typically have props
        PROP_POSITIONS = {'RB', 'WR', 'TE', 'QB'}
        filtered_players = [
            p for p in players 
            if p.get('position') in PROP_POSITIONS
        ]
        
        print(f"Filtered to {len(filtered_players)} players from {len(players)} total (positions: {PROP_POSITIONS})")
        
        # Group players by event_id for batch processing
        events = {}
        for player in filtered_players:
            event_id = player.get("bettingpros_event_id") or player.get("event_id")
            if not event_id:
                continue
            
            if event_id not in events:
                events[event_id] = {
                    'event_id': event_id,
                    'game_commence_time': player.get('game_commence_time'),
                    'players': []
                }
            events[event_id]['players'].append(player)
        
        print(f"Grouped into {len(events)} event(s) to scrape")
        
        # Scrape all events concurrently (with some concurrency limit)
        snapshots = []
        tasks = []
        
        for event_data in events.values():
            for prop_type in prop_types:
                task = self._scrape_event_market(
                    event_id=event_data['event_id'],
                    prop_type=prop_type,
                    players=event_data['players'],
                    game_commence_time=event_data['game_commence_time']
                )
                tasks.append(task)
        
        # Process in batches to avoid overwhelming the API
        BATCH_SIZE = 5
        errors = 0
        successes = 0
        
        for i in range(0, len(tasks), BATCH_SIZE):
            batch = tasks[i:i + BATCH_SIZE]
            results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    errors += 1
                    error_type = type(result).__name__
                    error_msg = str(result)[:100]  # Truncate long error messages
                    logger.warning(f"  ⚠ Error in batch: {error_type}: {error_msg}")
                elif result:
                    successes += 1
                    snapshots.extend(result)
            
            # Small delay between batches
            if i + BATCH_SIZE < len(tasks):
                await asyncio.sleep(0.5)
        
        print(f"Batch processing complete: {successes} successful, {errors} failed")
        return snapshots
    
    async def _scrape_event_market(
        self,
        event_id: str,
        prop_type: PropType,
        players: List[Dict[str, Any]],
        game_commence_time: Optional[datetime] = None,
    ) -> List[PropLineSnapshot]:
        """
        Scrape all players for a specific event/market combination in ONE API call.
        
        Args:
            event_id: BettingPros event ID
            prop_type: Type of prop to scrape
            players: List of players in this event
            game_commence_time: When the game starts
            
        Returns:
            List of PropLineSnapshot objects for all players with offers
        """
        market_id = self.MARKET_IDS.get(prop_type)
        if not market_id:
            return []
        
        logger.info(f"Fetching {prop_type.value} offers for event {event_id} ({len(players)} players)")
        
        try:
            # Fetch ALL offers for this event/market in one API call
            endpoint = "/offers"
            params = {
                "market_id": market_id,
                "event_id": event_id,
            }
            
            api_data = await self._fetch_api(endpoint, params)
            if not api_data:
                logger.warning(f"  ✗ No API data for event {event_id}")
                return []
        except Exception as e:
            # Handle RetryError and other exceptions gracefully
            logger.warning(f"  ✗ Failed to fetch data for event {event_id}: {type(e).__name__}")
            return []
        
        offers = api_data.get('offers', [])
        logger.info(f"  → Got {len(offers)} offer(s) from API")
        
        # Create a lookup of player slugs for quick matching
        player_lookup = {
            self._player_name_to_slug(p['name']): p 
            for p in players
        }
        
        snapshots = []
        matched_count = 0
        
        # Process all offers and match to our player list
        for offer in offers:
            participants = offer.get('participants', [])
            if not participants:
                continue
            
            participant = participants[0]
            offer_player_name = participant.get('name', '')
            offer_player_slug = self._player_name_to_slug(offer_player_name)
            
            # Check if this offer is for one of our players
            player_data = player_lookup.get(offer_player_slug)
            if not player_data:
                continue
            
            # Extract prop data from the offer
            prop_data = self._parse_api_offer(
                offer=offer,
                player_name=player_data['name'],
                prop_type=prop_type
            )
            
            if not prop_data:
                continue
            
            # Create snapshot
            player_slug = self._player_name_to_slug(player_data['name'])
            
            # Calculate hours before kickoff if we have game time
            hours_before = None
            if game_commence_time:
                now = datetime.now(timezone.utc)
                delta = game_commence_time - now
                hours_before = Decimal(str(round(delta.total_seconds() / 3600, 2)))
            
            snapshot = PropLineSnapshot(
                event_id=event_id,
                game_commence_time=game_commence_time or datetime.now(timezone.utc),
                player_name=player_data['name'],
                player_slug=player_slug,
                prop_type=prop_type,
                consensus_line=prop_data.get("consensus_line"),
                draftkings_line=prop_data.get("draftkings_line"),
                fanduel_line=prop_data.get("fanduel_line"),
                betmgm_line=prop_data.get("betmgm_line"),
                caesars_line=prop_data.get("caesars_line"),
                pointsbet_line=prop_data.get("pointsbet_line"),
                consensus_over_odds=prop_data.get("consensus_over_odds"),
                consensus_under_odds=prop_data.get("consensus_under_odds"),
                draftkings_over_odds=prop_data.get("draftkings_over_odds"),
                draftkings_under_odds=prop_data.get("draftkings_under_odds"),
                fanduel_over_odds=prop_data.get("fanduel_over_odds"),
                fanduel_under_odds=prop_data.get("fanduel_under_odds"),
                betmgm_over_odds=prop_data.get("betmgm_over_odds"),
                betmgm_under_odds=prop_data.get("betmgm_under_odds"),
                caesars_over_odds=prop_data.get("caesars_over_odds"),
                caesars_under_odds=prop_data.get("caesars_under_odds"),
                pointsbet_over_odds=prop_data.get("pointsbet_over_odds"),
                pointsbet_under_odds=prop_data.get("pointsbet_under_odds"),
                consensus_timestamp=prop_data.get("consensus_timestamp"),
                draftkings_timestamp=prop_data.get("draftkings_timestamp"),
                fanduel_timestamp=prop_data.get("fanduel_timestamp"),
                betmgm_timestamp=prop_data.get("betmgm_timestamp"),
                caesars_timestamp=prop_data.get("caesars_timestamp"),
                pointsbet_timestamp=prop_data.get("pointsbet_timestamp"),
                snapshot_time=datetime.now(timezone.utc),
                source_timestamp=prop_data.get("source_timestamp"),
                hours_before_kickoff=hours_before,
                source=DataSource.BETTINGPROS,
                raw_data=json.dumps({
                    "api_endpoint": "/offers",
                    "market_id": market_id,
                    "offer_id": offer.get('id'),
                }),
            )
            
            snapshots.append(snapshot)
            matched_count += 1
        
        logger.info(f"  ✓ Matched {matched_count} player(s) with offers")
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

