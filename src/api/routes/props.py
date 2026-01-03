"""Props endpoints for retrieving prop line data."""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from decimal import Decimal
from collections import defaultdict
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from src.models.database import PropLineSnapshot, PropType, get_session

router = APIRouter()

# Cache for dashboard data
_dashboard_cache = {
    'data': None,
    'timestamp': 0,
    'prop_type': None,
    'hours_back': None
}
CACHE_TTL_SECONDS = 30  # Cache for 30 seconds


class PropSnapshotResponse(BaseModel):
    """Response model for a prop line snapshot."""
    id: int
    event_id: str
    player_name: str
    prop_type: str
    consensus_line: Optional[float]
    draftkings_line: Optional[float]
    fanduel_line: Optional[float]
    betmgm_line: Optional[float]
    consensus_over_odds: Optional[int]
    consensus_under_odds: Optional[int]
    snapshot_time: datetime
    game_commence_time: datetime
    hours_before_kickoff: Optional[float]
    source: str
    
    class Config:
        from_attributes = True


class PropTimelineResponse(BaseModel):
    """Response model for a player's prop line timeline."""
    player_name: str
    prop_type: str
    event_id: str
    game_commence_time: datetime
    snapshots: List[dict]


class LineChangeData(BaseModel):
    """Line change data for a time window."""
    minutes: int
    absolute: Optional[float]
    percent: Optional[float]
    old_line: Optional[float]
    old_over_odds: Optional[int]
    old_under_odds: Optional[int]
    new_over_odds: Optional[int]
    new_under_odds: Optional[int]
    label: Optional[str] = None


class SportsbookData(BaseModel):
    """Data for a specific sportsbook."""
    current_line: Optional[float]
    current_over_odds: Optional[int]
    current_under_odds: Optional[int]
    updated: Optional[datetime]  # When this book last updated their line
    m5: LineChangeData
    m10: LineChangeData
    m15: LineChangeData
    m30: LineChangeData
    m45: LineChangeData
    m60: LineChangeData
    h12: LineChangeData
    h24: LineChangeData
    since_open: LineChangeData


class PropDashboardItem(BaseModel):
    """Dashboard item with current line and all time-based movements."""
    player_name: str
    prop_type: str
    event_id: str
    game_commence_time: datetime
    snapshot_time: datetime
    # Sportsbook-specific data
    consensus: Optional[SportsbookData] = None
    draftkings: Optional[SportsbookData] = None
    fanduel: Optional[SportsbookData] = None
    betmgm: Optional[SportsbookData] = None
    caesars: Optional[SportsbookData] = None
    pointsbet: Optional[SportsbookData] = None


class DashboardResponse(BaseModel):
    """Response model for dashboard view."""
    items: List[PropDashboardItem]
    total: int


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: List[PropSnapshotResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("/snapshots", response_model=PaginatedResponse)
async def get_prop_snapshots(
    player_name: Optional[str] = Query(None, description="Filter by player name"),
    event_id: Optional[str] = Query(None, description="Filter by event ID"),
    prop_type: Optional[str] = Query(None, description="rushing_yards or receiving_yards"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    include_past_games: bool = Query(False, description="Include games that have already kicked off"),
):
    """Get paginated list of prop line snapshots. By default, only returns data for upcoming games."""
    session = get_session()
    try:
        query = session.query(PropLineSnapshot)
        
        # By default, only show games that haven't kicked off yet
        if not include_past_games:
            current_time_utc = datetime.now(timezone.utc)
            query = query.filter(PropLineSnapshot.game_commence_time > current_time_utc)
        
        if player_name:
            query = query.filter(PropLineSnapshot.player_name.ilike(f"%{player_name}%"))
        
        if event_id:
            query = query.filter(PropLineSnapshot.event_id == event_id)
        
        if prop_type:
            try:
                pt = PropType(prop_type)
                query = query.filter(PropLineSnapshot.prop_type == pt)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid prop_type: {prop_type}")
        
        if start_date:
            query = query.filter(PropLineSnapshot.game_commence_time >= start_date)
        
        if end_date:
            query = query.filter(PropLineSnapshot.game_commence_time <= end_date)
        
        # Get total count
        total = query.count()
        
        # Paginate
        query = query.order_by(PropLineSnapshot.snapshot_time.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        snapshots = query.all()
        
        items = []
        for s in snapshots:
            items.append(PropSnapshotResponse(
                id=s.id,
                event_id=s.event_id,
                player_name=s.player_name,
                prop_type=s.prop_type.value,
                consensus_line=float(s.consensus_line) if s.consensus_line else None,
                draftkings_line=float(s.draftkings_line) if s.draftkings_line else None,
                fanduel_line=float(s.fanduel_line) if s.fanduel_line else None,
                betmgm_line=float(s.betmgm_line) if s.betmgm_line else None,
                consensus_over_odds=s.consensus_over_odds,
                consensus_under_odds=s.consensus_under_odds,
                snapshot_time=s.snapshot_time,
                game_commence_time=s.game_commence_time,
                hours_before_kickoff=float(s.hours_before_kickoff) if s.hours_before_kickoff else None,
                source=s.source.value,
            ))
        
        total_pages = (total + page_size - 1) // page_size
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    finally:
        session.close()


@router.get("/timeline/{player_name}", response_model=PropTimelineResponse)
async def get_player_prop_timeline(
    player_name: str,
    event_id: str = Query(..., description="Event ID"),
    prop_type: str = Query(..., description="rushing_yards or receiving_yards"),
):
    """Get the timeline of prop line changes for a specific player and game."""
    session = get_session()
    try:
        try:
            pt = PropType(prop_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid prop_type: {prop_type}")
        
        snapshots = (
            session.query(PropLineSnapshot)
            .filter(
                PropLineSnapshot.player_name == player_name,
                PropLineSnapshot.event_id == event_id,
                PropLineSnapshot.prop_type == pt,
            )
            .order_by(PropLineSnapshot.snapshot_time)
            .all()
        )
        
        if not snapshots:
            raise HTTPException(status_code=404, detail="No snapshots found")
        
        timeline = []
        for s in snapshots:
            timeline.append({
                "snapshot_time": s.snapshot_time.isoformat(),
                "hours_before_kickoff": float(s.hours_before_kickoff) if s.hours_before_kickoff else None,
                "consensus_line": float(s.consensus_line) if s.consensus_line else None,
                "draftkings_line": float(s.draftkings_line) if s.draftkings_line else None,
                "fanduel_line": float(s.fanduel_line) if s.fanduel_line else None,
                "betmgm_line": float(s.betmgm_line) if s.betmgm_line else None,
            })
        
        return PropTimelineResponse(
            player_name=player_name,
            prop_type=prop_type,
            event_id=event_id,
            game_commence_time=snapshots[0].game_commence_time,
            snapshots=timeline,
        )
    finally:
        session.close()


@router.get("/players")
async def get_players(
    search: Optional[str] = Query(None, description="Search by name"),
    limit: int = Query(50, ge=1, le=200),
):
    """Get list of unique players in the database."""
    session = get_session()
    try:
        query = session.query(PropLineSnapshot.player_name).distinct()
        
        if search:
            query = query.filter(PropLineSnapshot.player_name.ilike(f"%{search}%"))
        
        query = query.limit(limit)
        results = query.all()
        
        return {"players": [r[0] for r in results]}
    finally:
        session.close()


@router.get("/events")
async def get_events(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    include_past_games: bool = Query(False, description="Include games that have already kicked off"),
):
    """Get list of unique events (games) in the database. By default, only returns upcoming games."""
    session = get_session()
    try:
        query = session.query(
            PropLineSnapshot.event_id,
            PropLineSnapshot.home_team,
            PropLineSnapshot.away_team,
            PropLineSnapshot.game_commence_time,
        ).distinct()
        
        # By default, only show games that haven't kicked off yet
        if not include_past_games:
            current_time_utc = datetime.now(timezone.utc)
            query = query.filter(PropLineSnapshot.game_commence_time > current_time_utc)
        
        if start_date:
            query = query.filter(PropLineSnapshot.game_commence_time >= start_date)
        
        if end_date:
            query = query.filter(PropLineSnapshot.game_commence_time <= end_date)
        
        query = query.order_by(PropLineSnapshot.game_commence_time.desc())
        query = query.limit(limit)
        
        results = query.all()
        
        return {
            "events": [
                {
                    "event_id": r[0],
                    "home_team": r[1],
                    "away_team": r[2],
                    "game_commence_time": r[3].isoformat() if r[3] else None,
                }
                for r in results
            ]
        }
    finally:
        session.close()


async def get_dashboard_data(
    prop_type: Optional[str] = None,
    hours_back: int = 48,
) -> dict:
    """
    Get dashboard data with all calculations for all sportsbooks.
    Used by both HTTP endpoint and WebSocket broadcasts.
    
    Returns:
        Dictionary with items containing sportsbook-specific data
    """
    # Check cache first
    current_time = time.time()
    cache_key = f"{prop_type}_{hours_back}"
    
    if (_dashboard_cache['data'] is not None and 
        _dashboard_cache['prop_type'] == prop_type and
        _dashboard_cache['hours_back'] == hours_back and
        (current_time - _dashboard_cache['timestamp']) < CACHE_TTL_SECONDS):
        print(f"✓ Serving dashboard data from cache (age: {current_time - _dashboard_cache['timestamp']:.1f}s)")
        return _dashboard_cache['data']
    
    print(f"⏱ Computing dashboard data (cache miss or expired)...")
    start_time = time.time()
    
    session = get_session()
    try:
        # Get all snapshots from the last N hours
        # IMPORTANT: Only get snapshots for games that haven't kicked off yet
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        current_time_utc = datetime.now(timezone.utc)
        
        query = session.query(PropLineSnapshot).filter(
            PropLineSnapshot.snapshot_time >= cutoff_time,
            PropLineSnapshot.game_commence_time > current_time_utc  # Only future games (not yet kicked off)
        )
        
        if prop_type:
            try:
                pt = PropType(prop_type)
                query = query.filter(PropLineSnapshot.prop_type == pt)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid prop_type: {prop_type}")
        
        query = query.order_by(PropLineSnapshot.snapshot_time)
        all_snapshots = query.all()
        
        print(f"  → Loaded {len(all_snapshots)} snapshots from database")
        
        # Group snapshots by (player_name, prop_type, event_id)
        grouped: Dict[tuple, List[PropLineSnapshot]] = defaultdict(list)
        for snap in all_snapshots:
            key = (snap.player_name, snap.prop_type, snap.event_id)
            grouped[key].append(snap)
        
        # Define sportsbooks to track
        sportsbooks = {
            'consensus': ('consensus_line', 'consensus_over_odds', 'consensus_under_odds'),
            'draftkings': ('draftkings_line', 'draftkings_over_odds', 'draftkings_under_odds'),
            'fanduel': ('fanduel_line', 'fanduel_over_odds', 'fanduel_under_odds'),
            'betmgm': ('betmgm_line', 'betmgm_over_odds', 'betmgm_under_odds'),
            'caesars': ('caesars_line', 'caesars_over_odds', 'caesars_under_odds'),
            'pointsbet': ('pointsbet_line', 'pointsbet_over_odds', 'pointsbet_under_odds'),
        }
        
        # Calculate movements for each player
        dashboard_items = []
        for (player_name, prop_type_enum, event_id), snapshots in grouped.items():
            if not snapshots:
                continue
            
            # Sort by time (should already be sorted)
            snapshots.sort(key=lambda s: s.snapshot_time)
            
            # Get the most recent snapshot
            latest = snapshots[-1]
            current_time = latest.snapshot_time
            
            # Build item with data for each sportsbook
            item = {
                "player_name": player_name,
                "prop_type": prop_type_enum.value,
                "event_id": event_id,
                "game_commence_time": latest.game_commence_time.isoformat(),
                "snapshot_time": latest.snapshot_time.isoformat(),
            }
            
            # Calculate for each sportsbook
            for book_name, (line_field, over_odds_field, under_odds_field) in sportsbooks.items():
                # Get current line for this sportsbook
                current_line_value = getattr(latest, line_field)
                if not current_line_value:
                    # Skip this sportsbook if no data
                    continue
                
                current_line = float(current_line_value)
                current_over_odds = getattr(latest, over_odds_field)
                current_under_odds = getattr(latest, under_odds_field)
                
                # Get the timestamp for when this book last updated
                timestamp_field = f"{book_name}_timestamp"
                book_timestamp = getattr(latest, timestamp_field, None)
                
                # Pre-filter snapshots for this sportsbook (only those with data for this book)
                book_snapshots = [s for s in snapshots if getattr(s, line_field) is not None]
                
                # Function to calculate line changes for this specific sportsbook
                def calculate_change_for_book(minutes: int, label: Optional[str] = None) -> dict:
                    if not book_snapshots:
                        return {
                            "minutes": minutes,
                            "absolute": None,
                            "percent": None,
                            "old_line": None,
                            "old_over_odds": None,
                            "old_under_odds": None,
                            "new_over_odds": None,
                            "new_under_odds": None,
                            "label": label
                        }
                    
                    if minutes == 0:  # "Since Open" - use first snapshot
                        first = book_snapshots[0]
                        old_line = float(getattr(first, line_field))
                        absolute = current_line - old_line
                        percent = ((current_line - old_line) / old_line) * 100 if old_line != 0 else 0
                        
                        return {
                            "minutes": 0,
                            "absolute": absolute,
                            "percent": percent,
                            "old_line": old_line,
                            "old_over_odds": getattr(first, over_odds_field),
                            "old_under_odds": getattr(first, under_odds_field),
                            "new_over_odds": current_over_odds,
                            "new_under_odds": current_under_odds,
                            "label": label
                        }
                    
                    # Find snapshot closest to target time
                    # OPTIMIZATION: Iterate backwards from end (snapshots are sorted by time)
                    target_time = current_time - timedelta(minutes=minutes)
                    closest_snap = None
                    min_diff = timedelta.max
                    
                    # Start from most recent and work backwards
                    for snap in reversed(book_snapshots[:-1]):  # Exclude the latest
                        if snap.snapshot_time > current_time:
                            continue
                        
                        diff = abs(snap.snapshot_time - target_time)
                        if diff < min_diff:
                            min_diff = diff
                            closest_snap = snap
                        elif snap.snapshot_time < target_time:
                            # We've passed the target time, no need to keep searching
                            break
                    
                    if not closest_snap:
                        return {
                            "minutes": minutes,
                            "absolute": None,
                            "percent": None,
                            "old_line": None,
                            "old_over_odds": None,
                            "old_under_odds": None,
                            "new_over_odds": None,
                            "new_under_odds": None,
                            "label": label
                        }
                    
                    old_line = float(getattr(closest_snap, line_field))
                    absolute = current_line - old_line
                    percent = ((current_line - old_line) / old_line) * 100 if old_line != 0 else 0
                    
                    return {
                        "minutes": minutes,
                        "absolute": absolute,
                        "percent": percent,
                        "old_line": old_line,
                        "old_over_odds": getattr(closest_snap, over_odds_field),
                        "old_under_odds": getattr(closest_snap, under_odds_field),
                        "new_over_odds": current_over_odds,
                        "new_under_odds": current_under_odds,
                        "label": label
                    }
                
                # Add sportsbook data to item
                item[book_name] = {
                    "current_line": current_line,
                    "current_over_odds": current_over_odds,
                    "current_under_odds": current_under_odds,
                    "updated": book_timestamp.isoformat() if book_timestamp else None,
                    "m5": calculate_change_for_book(5),
                    "m10": calculate_change_for_book(10),
                    "m15": calculate_change_for_book(15),
                    "m30": calculate_change_for_book(30),
                    "m45": calculate_change_for_book(45),
                    "m60": calculate_change_for_book(60),
                    "h12": calculate_change_for_book(12 * 60, "Last 12h"),
                    "h24": calculate_change_for_book(24 * 60, "Last 24h"),
                    "since_open": calculate_change_for_book(0, "Since Open")
                }
            
            # Only add item if it has at least consensus data
            if 'consensus' in item:
                dashboard_items.append(item)
        
        # Return as dict (JSON-serializable)
        result = {
            "items": dashboard_items,
            "total": len(dashboard_items)
        }
        
        # Update cache
        _dashboard_cache['data'] = result
        _dashboard_cache['timestamp'] = time.time()
        _dashboard_cache['prop_type'] = prop_type
        _dashboard_cache['hours_back'] = hours_back
        
        elapsed = time.time() - start_time
        print(f"✓ Dashboard data computed in {elapsed:.2f}s ({len(dashboard_items)} items)")
        
        return result
    
    finally:
        session.close()


def invalidate_dashboard_cache():
    """Invalidate the dashboard cache. Called when new data is scraped."""
    global _dashboard_cache
    _dashboard_cache = {
        'data': None,
        'timestamp': 0,
        'prop_type': None,
        'hours_back': None
    }
    print("✓ Dashboard cache invalidated")


@router.get("/dashboard")
async def get_dashboard_view(
    prop_type: Optional[str] = Query(None, description="Filter by prop type"),
    hours_back: int = Query(48, description="Look back this many hours for snapshots"),
):
    """
    Get dashboard view with one item per player containing all time-based line movements
    for all sportsbooks. Each item contains keys for different sportsbooks (consensus, 
    draftkings, fanduel, etc.) with their respective line data and movements.
    
    This endpoint does all calculations on the backend and returns ready-to-display data.
    
    PERFORMANCE NOTE: Results are cached for 30 seconds to reduce database load.
    """
    data = await get_dashboard_data(prop_type=prop_type, hours_back=hours_back)
    return data

