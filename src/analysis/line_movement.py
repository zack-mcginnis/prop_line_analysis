"""Line movement detection algorithm."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from src.config import get_settings
from src.models.database import (
    PropLineSnapshot,
    PlayerGameStats,
    LineMovement,
    PropType,
    get_session,
)


class LineMovementDetector:
    """
    Detects significant line movements in player props.
    
    A significant movement is defined as:
    - A drop in the line by >= X% (configurable, default 10%)
    - OR a drop in the line by >= Y yards (configurable, default 5)
    - Occurring within Z hours before kickoff (configurable, default 3)
    """
    
    def __init__(
        self,
        threshold_pct: Optional[float] = None,
        threshold_abs: Optional[float] = None,
        hours_before: Optional[float] = None,
    ):
        settings = get_settings()
        self.threshold_pct = threshold_pct or settings.line_movement_threshold_pct
        self.threshold_abs = threshold_abs or settings.line_movement_threshold_abs
        self.hours_before = hours_before or settings.hours_before_kickoff_threshold
    
    def get_snapshots_for_event(
        self,
        session: Session,
        event_id: str,
        player_name: str,
        prop_type: PropType,
    ) -> List[PropLineSnapshot]:
        """
        Get all snapshots for a specific player/event/prop combination.
        
        Args:
            session: Database session
            event_id: Game event ID
            player_name: Player name
            prop_type: Type of prop
            
        Returns:
            List of snapshots ordered by time
        """
        return (
            session.query(PropLineSnapshot)
            .filter(
                PropLineSnapshot.event_id == event_id,
                PropLineSnapshot.player_name == player_name,
                PropLineSnapshot.prop_type == prop_type,
            )
            .order_by(PropLineSnapshot.snapshot_time)
            .all()
        )
    
    def calculate_movement(
        self,
        initial_line: Decimal,
        final_line: Decimal,
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate absolute and percentage movement.
        
        Args:
            initial_line: Starting line value
            final_line: Ending line value
            
        Returns:
            Tuple of (absolute_change, percentage_change)
        """
        absolute = final_line - initial_line
        
        if initial_line != 0:
            pct = (absolute / initial_line) * 100
        else:
            pct = Decimal("0")
        
        return absolute, pct
    
    def is_significant_movement(
        self,
        movement_abs: Decimal,
        movement_pct: Decimal,
    ) -> bool:
        """
        Check if a movement is significant based on thresholds.
        
        Note: We're looking for DROPS (negative movements).
        
        Args:
            movement_abs: Absolute change in yards
            movement_pct: Percentage change
            
        Returns:
            True if the movement is significant
        """
        # Check for significant DROP (negative movement)
        return (
            movement_abs <= -self.threshold_abs
            or movement_pct <= -self.threshold_pct
        )
    
    def detect_late_movement(
        self,
        snapshots: List[PropLineSnapshot],
        game_commence_time: datetime,
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if there was significant late movement in the line.
        
        "Late" means within self.hours_before hours of kickoff.
        
        Args:
            snapshots: List of snapshots for a player/event/prop
            game_commence_time: When the game starts
            
        Returns:
            Dict with movement details if significant, else None
        """
        if len(snapshots) < 2:
            return None
        
        # Find snapshots within the late window
        late_cutoff = game_commence_time.timestamp() - (self.hours_before * 3600)
        
        # Find the earliest snapshot before the late window (or earliest overall)
        early_snapshots = [
            s for s in snapshots
            if s.snapshot_time.timestamp() < late_cutoff
        ]
        
        # Find the latest snapshot in the late window
        late_snapshots = [
            s for s in snapshots
            if s.snapshot_time.timestamp() >= late_cutoff
        ]
        
        if not early_snapshots or not late_snapshots:
            # If we don't have snapshots both before and after the cutoff,
            # use the first and last snapshots overall
            early_snapshot = snapshots[0]
            late_snapshot = snapshots[-1]
        else:
            # Use the last snapshot before the late window as the baseline
            early_snapshot = early_snapshots[-1]
            # Use the last (most recent) late snapshot
            late_snapshot = late_snapshots[-1]
        
        # Calculate movement
        initial_line = early_snapshot.consensus_line
        final_line = late_snapshot.consensus_line
        
        if initial_line is None or final_line is None:
            return None
        
        movement_abs, movement_pct = self.calculate_movement(initial_line, final_line)
        
        # Check if movement is significant
        if not self.is_significant_movement(movement_abs, movement_pct):
            return None
        
        # Calculate hours before kickoff for the final snapshot
        hours_before_kickoff = (
            game_commence_time.timestamp() - late_snapshot.snapshot_time.timestamp()
        ) / 3600
        
        return {
            "event_id": snapshots[0].event_id,
            "player_name": snapshots[0].player_name,
            "prop_type": snapshots[0].prop_type,
            "initial_line": initial_line,
            "final_line": final_line,
            "initial_snapshot_time": early_snapshot.snapshot_time,
            "final_snapshot_time": late_snapshot.snapshot_time,
            "movement_absolute": movement_abs,
            "movement_pct": movement_pct,
            "hours_before_kickoff": Decimal(str(round(hours_before_kickoff, 2))),
            "game_commence_time": game_commence_time,
        }
    
    def detect_all_movements(
        self,
        session: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LineMovement]:
        """
        Detect all significant line movements in the database.
        
        Args:
            session: Database session
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of LineMovement objects
        """
        movements = []
        
        # Get unique combinations of event/player/prop
        query = (
            session.query(
                PropLineSnapshot.event_id,
                PropLineSnapshot.player_name,
                PropLineSnapshot.prop_type,
                PropLineSnapshot.game_commence_time,
            )
            .distinct()
        )
        
        if start_date:
            query = query.filter(PropLineSnapshot.game_commence_time >= start_date)
        if end_date:
            query = query.filter(PropLineSnapshot.game_commence_time <= end_date)
        
        combinations = query.all()
        
        for event_id, player_name, prop_type, game_commence_time in combinations:
            snapshots = self.get_snapshots_for_event(
                session, event_id, player_name, prop_type
            )
            
            if not snapshots:
                continue
            
            movement_data = self.detect_late_movement(snapshots, game_commence_time)
            
            if movement_data:
                movement = LineMovement(
                    event_id=movement_data["event_id"],
                    player_name=movement_data["player_name"],
                    prop_type=movement_data["prop_type"],
                    initial_line=movement_data["initial_line"],
                    final_line=movement_data["final_line"],
                    initial_snapshot_time=movement_data["initial_snapshot_time"],
                    final_snapshot_time=movement_data["final_snapshot_time"],
                    movement_absolute=movement_data["movement_absolute"],
                    movement_pct=movement_data["movement_pct"],
                    hours_before_kickoff=movement_data["hours_before_kickoff"],
                    game_commence_time=movement_data["game_commence_time"],
                )
                movements.append(movement)
        
        return movements
    
    def match_with_results(
        self,
        session: Session,
        movements: List[LineMovement],
    ) -> List[LineMovement]:
        """
        Match line movements with actual game results.
        
        Args:
            session: Database session
            movements: List of LineMovement objects
            
        Returns:
            Updated movements with actual_yards and went_over/under flags
        """
        for movement in movements:
            # Find the player's game stats
            stats = (
                session.query(PlayerGameStats)
                .filter(
                    PlayerGameStats.event_id == movement.event_id,
                    PlayerGameStats.player_name == movement.player_name,
                )
                .first()
            )
            
            if not stats:
                continue
            
            # Get the relevant yards based on prop type
            if movement.prop_type == PropType.RUSHING_YARDS:
                actual_yards = stats.rushing_yards
            elif movement.prop_type == PropType.RECEIVING_YARDS:
                actual_yards = stats.receiving_yards
            else:
                continue
            
            if actual_yards is None:
                continue
            
            movement.actual_yards = actual_yards
            movement.went_over = actual_yards > float(movement.final_line)
            movement.went_under = actual_yards < float(movement.final_line)
        
        return movements
    
    def save_movements(
        self,
        session: Session,
        movements: List[LineMovement],
    ) -> int:
        """
        Save line movements to the database.
        
        Args:
            session: Database session
            movements: List of LineMovement objects
            
        Returns:
            Number of movements saved
        """
        if not movements:
            return 0
        
        try:
            # Check for existing movements to avoid duplicates
            for movement in movements:
                existing = (
                    session.query(LineMovement)
                    .filter(
                        LineMovement.event_id == movement.event_id,
                        LineMovement.player_name == movement.player_name,
                        LineMovement.prop_type == movement.prop_type,
                    )
                    .first()
                )
                
                if existing:
                    # Update existing
                    existing.initial_line = movement.initial_line
                    existing.final_line = movement.final_line
                    existing.movement_absolute = movement.movement_absolute
                    existing.movement_pct = movement.movement_pct
                    existing.actual_yards = movement.actual_yards
                    existing.went_over = movement.went_over
                    existing.went_under = movement.went_under
                else:
                    session.add(movement)
            
            session.commit()
            return len(movements)
        except Exception as e:
            session.rollback()
            raise e


def run_detection(
    threshold_pct: float = 10.0,
    threshold_abs: float = 5.0,
    hours_before: float = 3.0,
) -> int:
    """
    Run line movement detection on all data.
    
    Args:
        threshold_pct: Percentage threshold for significant movement
        threshold_abs: Absolute threshold for significant movement
        hours_before: Hours before kickoff to consider as "late"
        
    Returns:
        Number of significant movements detected
    """
    detector = LineMovementDetector(
        threshold_pct=threshold_pct,
        threshold_abs=threshold_abs,
        hours_before=hours_before,
    )
    
    session = get_session()
    try:
        # Detect all movements
        movements = detector.detect_all_movements(session)
        
        # Match with actual results
        movements = detector.match_with_results(session, movements)
        
        # Save to database
        saved = detector.save_movements(session, movements)
        
        return saved
    finally:
        session.close()


if __name__ == "__main__":
    count = run_detection()
    print(f"Detected {count} significant line movements")

