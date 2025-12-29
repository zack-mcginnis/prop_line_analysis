"""FastAPI application main entry point."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.config import get_settings
from src.models.database import get_session, init_db
from src.scheduler.jobs import get_scheduler
from src.api.routes import analysis, props, movements, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("Starting application...")
    init_db()
    
    settings = get_settings()
    if settings.environment != "development":
        # Start scheduler in production
        scheduler = get_scheduler()
        scheduler.start()
    
    yield
    
    # Shutdown
    print("Shutting down application...")
    scheduler = get_scheduler()
    scheduler.stop()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Prop Line Movement Analysis API",
        description="API for analyzing NFL player prop line movements and their correlation with game performance.",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(props.router, prefix="/api/props", tags=["Props"])
    app.include_router(movements.router, prefix="/api/movements", tags=["Movements"])
    app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
    
    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

