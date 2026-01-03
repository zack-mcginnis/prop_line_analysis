"""SQLAlchemy database models for prop line analysis."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    Enum,
    Boolean,
    Index,
    ForeignKey,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func

from src.config import get_settings

Base = declarative_base()


class PropType(enum.Enum):
    """Type of player prop."""
    RUSHING_YARDS = "rushing_yards"
    RECEIVING_YARDS = "receiving_yards"


class DataSource(enum.Enum):
    """Source of prop line data."""
    BETTINGPROS = "bettingpros"
    ODDS_API = "odds_api"


class PropLineSnapshot(Base):
    """
    Stores prop line data at each snapshot time.
    This is the main table for tracking line movements over time.
    """
    __tablename__ = "prop_line_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Game identification
    event_id = Column(String(100), nullable=False, index=True)
    game_commence_time = Column(DateTime(timezone=True), nullable=False)
    home_team = Column(String(100), nullable=True)
    away_team = Column(String(100), nullable=True)
    
    # Player identification
    player_name = Column(String(200), nullable=False, index=True)
    player_slug = Column(String(200), nullable=True)  # URL-friendly name for scraping
    team = Column(String(100), nullable=True)
    
    # Prop details
    prop_type = Column(Enum(PropType), nullable=False)
    
    # Line values from different sportsbooks
    consensus_line = Column(Numeric(6, 1), nullable=True)
    draftkings_line = Column(Numeric(6, 1), nullable=True)
    fanduel_line = Column(Numeric(6, 1), nullable=True)
    betmgm_line = Column(Numeric(6, 1), nullable=True)
    caesars_line = Column(Numeric(6, 1), nullable=True)
    pointsbet_line = Column(Numeric(6, 1), nullable=True)
    
    # Odds (juice) for over/under - stored as American odds
    # Consensus odds
    consensus_over_odds = Column(Integer, nullable=True)
    consensus_under_odds = Column(Integer, nullable=True)
    
    # DraftKings odds
    draftkings_over_odds = Column(Integer, nullable=True)
    draftkings_under_odds = Column(Integer, nullable=True)
    
    # FanDuel odds
    fanduel_over_odds = Column(Integer, nullable=True)
    fanduel_under_odds = Column(Integer, nullable=True)
    
    # BetMGM odds
    betmgm_over_odds = Column(Integer, nullable=True)
    betmgm_under_odds = Column(Integer, nullable=True)
    
    # Caesars odds
    caesars_over_odds = Column(Integer, nullable=True)
    caesars_under_odds = Column(Integer, nullable=True)
    
    # PointsBet odds
    pointsbet_over_odds = Column(Integer, nullable=True)
    pointsbet_under_odds = Column(Integer, nullable=True)
    
    # Timestamps
    snapshot_time = Column(DateTime(timezone=True), nullable=False, default=func.now())
    source_timestamp = Column(DateTime(timezone=True), nullable=True)  # From data source
    
    # Computed fields
    hours_before_kickoff = Column(Numeric(6, 2), nullable=True)
    
    # Data source
    source = Column(Enum(DataSource), nullable=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    raw_data = Column(Text, nullable=True)  # Store raw JSON for debugging
    
    __table_args__ = (
        Index('idx_prop_snapshot_lookup', 'event_id', 'player_name', 'prop_type', 'snapshot_time'),
        Index('idx_prop_snapshot_time', 'snapshot_time'),
        Index('idx_prop_game_time', 'game_commence_time'),
    )
    
    def __repr__(self):
        return f"<PropLineSnapshot(player={self.player_name}, prop={self.prop_type.value}, line={self.consensus_line})>"


class PlayerGameStats(Base):
    """
    Actual player performance stats from games.
    Used to compare against prop lines.
    """
    __tablename__ = "player_game_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Game identification
    event_id = Column(String(100), nullable=False, index=True)
    game_date = Column(DateTime(timezone=True), nullable=False)
    season = Column(Integer, nullable=False)
    week = Column(Integer, nullable=False)
    
    # Player identification
    player_name = Column(String(200), nullable=False, index=True)
    player_id = Column(String(50), nullable=True)  # ESPN player ID
    team = Column(String(100), nullable=True)
    opponent = Column(String(100), nullable=True)
    
    # Rushing stats
    rushing_attempts = Column(Integer, nullable=True)
    rushing_yards = Column(Integer, nullable=True)
    rushing_tds = Column(Integer, nullable=True)
    
    # Receiving stats
    receptions = Column(Integer, nullable=True)
    receiving_targets = Column(Integer, nullable=True)
    receiving_yards = Column(Integer, nullable=True)
    receiving_tds = Column(Integer, nullable=True)
    
    # Game context
    is_home = Column(Boolean, nullable=True)
    game_result = Column(String(10), nullable=True)  # W/L
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_player_stats_lookup', 'player_name', 'game_date'),
        Index('idx_player_stats_event', 'event_id'),
    )
    
    def __repr__(self):
        return f"<PlayerGameStats(player={self.player_name}, rush={self.rushing_yards}, rec={self.receiving_yards})>"


class LineMovement(Base):
    """
    Detected significant line movements.
    Pre-computed for faster analysis queries.
    """
    __tablename__ = "line_movements"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # References
    event_id = Column(String(100), nullable=False, index=True)
    player_name = Column(String(200), nullable=False, index=True)
    prop_type = Column(Enum(PropType), nullable=False)
    
    # Movement details
    initial_line = Column(Numeric(6, 1), nullable=False)
    final_line = Column(Numeric(6, 1), nullable=False)
    initial_snapshot_time = Column(DateTime(timezone=True), nullable=False)
    final_snapshot_time = Column(DateTime(timezone=True), nullable=False)
    
    # Movement metrics
    movement_absolute = Column(Numeric(6, 1), nullable=False)  # final - initial
    movement_pct = Column(Numeric(6, 2), nullable=False)  # percentage change
    hours_before_kickoff = Column(Numeric(6, 2), nullable=False)
    
    # Game result
    actual_yards = Column(Integer, nullable=True)
    went_over = Column(Boolean, nullable=True)  # Did player exceed final line?
    went_under = Column(Boolean, nullable=True)
    
    # Timestamps
    game_commence_time = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_movement_lookup', 'event_id', 'player_name', 'prop_type'),
        Index('idx_movement_analysis', 'movement_pct', 'hours_before_kickoff'),
    )
    
    def __repr__(self):
        return f"<LineMovement(player={self.player_name}, move={self.movement_pct}%)>"


class AnalysisResult(Base):
    """
    Computed correlation analysis results.
    Stores aggregated statistics for different thresholds.
    """
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Analysis parameters
    analysis_name = Column(String(200), nullable=False)
    prop_type = Column(Enum(PropType), nullable=True)  # Null means all types
    
    # Thresholds used
    movement_threshold_pct = Column(Numeric(6, 2), nullable=True)
    movement_threshold_abs = Column(Numeric(6, 1), nullable=True)
    hours_before_threshold = Column(Numeric(6, 2), nullable=True)
    
    # Sample information
    sample_size = Column(Integer, nullable=False)
    date_range_start = Column(DateTime(timezone=True), nullable=False)
    date_range_end = Column(DateTime(timezone=True), nullable=False)
    
    # Results
    over_count = Column(Integer, nullable=False)
    under_count = Column(Integer, nullable=False)
    push_count = Column(Integer, nullable=False, default=0)
    over_rate = Column(Numeric(5, 4), nullable=False)  # e.g., 0.4523 = 45.23%
    under_rate = Column(Numeric(5, 4), nullable=False)
    
    # Statistical significance
    chi_square_statistic = Column(Numeric(10, 4), nullable=True)
    p_value = Column(Numeric(10, 8), nullable=True)
    is_significant = Column(Boolean, nullable=True)  # p < 0.05
    confidence_interval_low = Column(Numeric(5, 4), nullable=True)
    confidence_interval_high = Column(Numeric(5, 4), nullable=True)
    
    # Comparison with baseline
    baseline_over_rate = Column(Numeric(5, 4), nullable=True)
    baseline_sample_size = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_analysis_name', 'analysis_name'),
    )
    
    def __repr__(self):
        return f"<AnalysisResult(name={self.analysis_name}, over_rate={self.over_rate})>"


# Database connection utilities
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_session() -> Session:
    """Get a new database session."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine()
        )
    return _SessionLocal()


def init_db():
    """Initialize the database by creating all tables."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

