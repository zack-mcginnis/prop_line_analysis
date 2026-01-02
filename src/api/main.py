"""FastAPI application main entry point."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, Set
import asyncio

from fastapi import FastAPI, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.config import get_settings
from src.models.database import get_session, init_db
from src.scheduler.jobs import get_scheduler
from src.api.routes import analysis, props, movements, health


# Global set to track active WebSocket connections
active_websockets: Set[WebSocket] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("=" * 60)
    print("Starting application...")
    
    # Don't call init_db() here - let Alembic migrations handle table creation
    # This prevents crashes if database isn't ready yet
    # Tables are created by: alembic upgrade head (run before uvicorn starts)
    
    # Always start scheduler (includes Week 18 every-minute job)
    try:
        scheduler = get_scheduler()
        scheduler.start()
        print("✓ Scheduler started")
    except Exception as e:
        print(f"⚠ Warning: Scheduler failed to start: {e}")
        # Continue anyway - scheduler isn't critical for API to work
    
    print("=" * 60)
    
    yield
    
    # Shutdown
    print("=" * 60)
    print("Shutting down application...")
    try:
        scheduler = get_scheduler()
        scheduler.stop()
        print("✓ Scheduler stopped")
    except Exception as e:
        print(f"⚠ Warning: Scheduler shutdown error: {e}")
    print("=" * 60)


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
    
    @app.websocket("/ws/dashboard")
    async def websocket_dashboard(websocket: WebSocket):
        """WebSocket endpoint for real-time dashboard updates."""
        await websocket.accept()
        active_websockets.add(websocket)
        print(f"WebSocket client connected. Total clients: {len(active_websockets)}")
        
        try:
            # Keep connection alive and wait for client messages (if any)
            while True:
                # We don't expect messages from client, but need to keep connection alive
                try:
                    await websocket.receive_text()
                except WebSocketDisconnect:
                    break
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            active_websockets.discard(websocket)
            print(f"WebSocket client disconnected. Total clients: {len(active_websockets)}")
    
    return app


async def broadcast_dashboard_update(prop_type: Optional[str] = None):
    """
    Broadcast dashboard update to all connected WebSocket clients.
    Called by the scheduler after scraping completes.
    """
    if not active_websockets:
        return
    
    print(f"Broadcasting dashboard update to {len(active_websockets)} clients...")
    
    # Import here to avoid circular dependency
    from src.api.routes.props import get_dashboard_data
    
    try:
        # Get the dashboard data (same format as HTTP endpoint)
        dashboard_data = await get_dashboard_data(prop_type=prop_type, hours_back=48)
        
        # Broadcast to all connected clients
        disconnected = set()
        successful = 0
        for websocket in active_websockets:
            try:
                await websocket.send_json(dashboard_data)
                successful += 1
            except Exception as e:
                print(f"  ⚠ Failed to send to client: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            active_websockets.discard(websocket)
        
        print(f"  ✓ Broadcast complete: {successful} successful, {len(disconnected)} failed")
    except Exception as e:
        print(f"  ✗ Broadcast failed: {e}")
        import traceback
        traceback.print_exc()


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

