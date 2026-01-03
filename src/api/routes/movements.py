"""Line movements endpoints."""

from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.models.database import LineMovement, PropType, get_session
from src.analysis.line_movement import LineMovementDetector, run_detection

router = APIRouter()


class MovementResponse(BaseModel):
    """Response model for a line movement."""
    id: int
    event_id: str
    player_name: str
    prop_type: str
    initial_line: float
    final_line: float
    movement_absolute: float
    movement_pct: float
    hours_before_kickoff: float
    actual_yards: Optional[int]
    went_over: Optional[bool]
    went_under: Optional[bool]
    game_commence_time: datetime
    
    class Config:
        from_attributes = True


class MovementListResponse(BaseModel):
    """Paginated list of movements."""
    items: List[MovementResponse]
    total: int
    page: int
    page_size: int


class MovementSummary(BaseModel):
    """Summary statistics for movements."""
    total_movements: int
    with_results: int
    over_count: int
    under_count: int
    over_rate: Optional[float]
    under_rate: Optional[float]


@router.get("/", response_model=MovementListResponse)
async def get_movements(
    player_name: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    min_movement_pct: Optional[float] = Query(None, description="Min absolute % drop"),
    max_hours_before: Optional[float] = Query(None),
    went_under: Optional[bool] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    include_past_games: bool = Query(False, description="Include games that have already kicked off"),
):
    """Get list of detected line movements. By default, only returns data for upcoming games."""
    session = get_session()
    try:
        query = session.query(LineMovement)
        
        # By default, only show games that haven't kicked off yet
        if not include_past_games:
            from datetime import timezone
            current_time_utc = datetime.now(timezone.utc)
            query = query.filter(LineMovement.game_commence_time > current_time_utc)
        
        if player_name:
            query = query.filter(LineMovement.player_name.ilike(f"%{player_name}%"))
        
        if prop_type:
            try:
                pt = PropType(prop_type)
                query = query.filter(LineMovement.prop_type == pt)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid prop_type: {prop_type}")
        
        if min_movement_pct:
            # Filter for drops >= threshold (movement_pct is negative for drops)
            query = query.filter(LineMovement.movement_pct <= -min_movement_pct)
        
        if max_hours_before:
            query = query.filter(LineMovement.hours_before_kickoff <= max_hours_before)
        
        if went_under is not None:
            query = query.filter(LineMovement.went_under == went_under)
        
        if start_date:
            query = query.filter(LineMovement.game_commence_time >= start_date)
        
        if end_date:
            query = query.filter(LineMovement.game_commence_time <= end_date)
        
        total = query.count()
        
        query = query.order_by(LineMovement.game_commence_time.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        movements = query.all()
        
        items = []
        for m in movements:
            items.append(MovementResponse(
                id=m.id,
                event_id=m.event_id,
                player_name=m.player_name,
                prop_type=m.prop_type.value,
                initial_line=float(m.initial_line),
                final_line=float(m.final_line),
                movement_absolute=float(m.movement_absolute),
                movement_pct=float(m.movement_pct),
                hours_before_kickoff=float(m.hours_before_kickoff),
                actual_yards=m.actual_yards,
                went_over=m.went_over,
                went_under=m.went_under,
                game_commence_time=m.game_commence_time,
            ))
        
        return MovementListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    finally:
        session.close()


@router.get("/summary", response_model=MovementSummary)
async def get_movement_summary(
    prop_type: Optional[str] = Query(None),
    min_movement_pct: Optional[float] = Query(None),
    max_hours_before: Optional[float] = Query(None),
):
    """Get summary statistics for line movements."""
    session = get_session()
    try:
        query = session.query(LineMovement)
        
        if prop_type:
            try:
                pt = PropType(prop_type)
                query = query.filter(LineMovement.prop_type == pt)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid prop_type: {prop_type}")
        
        if min_movement_pct:
            query = query.filter(LineMovement.movement_pct <= -min_movement_pct)
        
        if max_hours_before:
            query = query.filter(LineMovement.hours_before_kickoff <= max_hours_before)
        
        movements = query.all()
        
        total = len(movements)
        with_results = sum(1 for m in movements if m.actual_yards is not None)
        over_count = sum(1 for m in movements if m.went_over)
        under_count = sum(1 for m in movements if m.went_under)
        
        over_rate = over_count / with_results if with_results > 0 else None
        under_rate = under_count / with_results if with_results > 0 else None
        
        return MovementSummary(
            total_movements=total,
            with_results=with_results,
            over_count=over_count,
            under_count=under_count,
            over_rate=over_rate,
            under_rate=under_rate,
        )
    finally:
        session.close()


@router.post("/detect")
async def trigger_detection(
    background_tasks: BackgroundTasks,
    threshold_pct: float = Query(10.0),
    threshold_abs: float = Query(5.0),
    hours_before: float = Query(3.0),
):
    """Trigger line movement detection as a background task."""
    def run_in_background():
        count = run_detection(threshold_pct, threshold_abs, hours_before)
        print(f"Detected {count} significant movements")
    
    background_tasks.add_task(run_in_background)
    
    return {
        "status": "started",
        "message": "Line movement detection started in background",
        "parameters": {
            "threshold_pct": threshold_pct,
            "threshold_abs": threshold_abs,
            "hours_before": hours_before,
        }
    }


@router.get("/{movement_id}", response_model=MovementResponse)
async def get_movement(movement_id: int):
    """Get a specific line movement by ID."""
    session = get_session()
    try:
        movement = session.query(LineMovement).filter(LineMovement.id == movement_id).first()
        
        if not movement:
            raise HTTPException(status_code=404, detail="Movement not found")
        
        return MovementResponse(
            id=movement.id,
            event_id=movement.event_id,
            player_name=movement.player_name,
            prop_type=movement.prop_type.value,
            initial_line=float(movement.initial_line),
            final_line=float(movement.final_line),
            movement_absolute=float(movement.movement_absolute),
            movement_pct=float(movement.movement_pct),
            hours_before_kickoff=float(movement.hours_before_kickoff),
            actual_yards=movement.actual_yards,
            went_over=movement.went_over,
            went_under=movement.went_under,
            game_commence_time=movement.game_commence_time,
        )
    finally:
        session.close()

