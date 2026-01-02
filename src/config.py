"""Application configuration using Pydantic settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/prop_analysis",
        description="PostgreSQL connection string"
    )
    
    # The Odds API
    odds_api_key: str = Field(
        default="",
        description="API key for The Odds API"
    )
    odds_api_base_url: str = Field(
        default="https://api.the-odds-api.com/v4",
        description="Base URL for The Odds API"
    )
    
    # Scraping Configuration
    scrape_interval_minutes: int = Field(
        default=5,
        description="How often to scrape BettingPros (in minutes)"
    )
    max_concurrent_requests: int = Field(
        default=5,
        description="Maximum concurrent HTTP requests"
    )
    request_delay_min: float = Field(
        default=1.0,
        description="Minimum delay between requests (seconds)"
    )
    request_delay_max: float = Field(
        default=2.0,
        description="Maximum delay between requests (seconds)"
    )
    
    # Analysis Configuration
    line_movement_threshold_pct: float = Field(
        default=10.0,
        description="Percentage threshold for significant line movement"
    )
    line_movement_threshold_abs: float = Field(
        default=5.0,
        description="Absolute yards threshold for significant line movement"
    )
    hours_before_kickoff_threshold: float = Field(
        default=3.0,
        description="Hours before kickoff to consider for late movement"
    )
    
    # Environment
    environment: str = Field(
        default="development",
        description="Environment name"
    )
    debug: bool = Field(
        default=True,
        description="Enable debug mode"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra env vars not in Settings


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

