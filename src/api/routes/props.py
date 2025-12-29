"""Props endpoints for retrieving prop line data."""

from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from src.models.database import PropLineSnapshot, PropType, get_session

router = APIRouter()


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
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
):
    """Get paginated list of prop line snapshots."""
    session = get_session()
    try:
        query = session.query(PropLineSnapshot)
        
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
):
    """Get list of unique events (games) in the database."""
    session = get_session()
    try:
        query = session.query(
            PropLineSnapshot.event_id,
            PropLineSnapshot.home_team,
            PropLineSnapshot.away_team,
            PropLineSnapshot.game_commence_time,
        ).distinct()
        
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

