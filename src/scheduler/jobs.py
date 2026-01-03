"""Scheduler jobs for automated data collection."""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.config import get_settings
from src.collectors.bettingpros import BettingProsCollector
from src.collectors.player_discovery import PlayerDiscovery
from src.collectors.espn import ESPNCollector
from src.models.database import PropType


class ScraperScheduler:
    """
    Manages scheduled scraping jobs for prop line data collection.
    
    Runs scraping jobs on game days:
    - Sunday: 6am-11:59pm (all day)
    - Monday: 4pm-11:59pm (Monday Night Football)
    - Thursday: 4pm-11:59pm (Thursday Night Football)
    - Saturday: 12pm-11:59pm (late season games)
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.scheduler = AsyncIOScheduler()
        self._is_running = False
    
    async def scrape_all_props(self, week: Optional[int] = None, hours_before_kickoff: Optional[float] = None):
        """
        Main scraping job that collects prop data for all players.
        
        Args:
            week: NFL week number (1-18), None for current week
            hours_before_kickoff: Hours before kickoff threshold, None for default
        """
        week_str = f"Week {week}" if week else "current week"
        hours = hours_before_kickoff or (self.settings.hours_before_kickoff_threshold + 9)
        
        print(f"[{datetime.now()}] Starting prop scraping job for {week_str} (within {hours}h of kickoff)...")
        
        snapshots_saved = False
        
        try:
            async with PlayerDiscovery() as discovery:
                # Get players for specified week
                players = await discovery.get_weekly_players(week=week, use_cache=False)
                
                # Filter to players whose games are starting soon
                players_to_scrape = discovery.get_players_for_scraping(
                    players,
                    hours_before_kickoff=hours,
                )
                
                print(f"  Found {len(players_to_scrape)} players to scrape")
                
                if not players_to_scrape:
                    print("  No players in scraping window, skipping...")
                    return
            
            async with BettingProsCollector() as collector:
                # Scrape both rushing and receiving props
                snapshots = await collector.scrape_all_players(
                    players_to_scrape,
                    prop_types=[PropType.RUSHING_YARDS, PropType.RECEIVING_YARDS],
                )
                
                if snapshots:
                    saved = collector.save_snapshots(snapshots)
                    print(f"  ✓ Saved {saved} prop snapshots")
                    snapshots_saved = True
                else:
                    print("  No new snapshots to save")
        
        except Exception as e:
            print(f"  ✗ Error in scraping job: {e}")
        
        # Invalidate cache and broadcast update to WebSocket clients if we saved new data
        if snapshots_saved:
            try:
                # Import here to avoid circular dependency
                from src.api.routes.props import invalidate_dashboard_cache
                from src.api.main import broadcast_dashboard_update
                
                # Invalidate cache so next request gets fresh data
                invalidate_dashboard_cache()
                
                # Broadcast to connected WebSocket clients
                await broadcast_dashboard_update()
            except Exception as e:
                print(f"  ⚠ Failed to broadcast WebSocket update: {e}")
    
    async def scrape_week18(self):
        """Wrapper for Week 18 continuous scraping job."""
        await self.scrape_all_props(week=18, hours_before_kickoff=70.0)
    
    async def collect_game_stats(self):
        """
        Job to collect actual player stats after games complete.
        Runs on Tuesdays to collect weekend stats.
        """
        print(f"[{datetime.now()}] Starting game stats collection...")
        
        try:
            async with ESPNCollector() as collector:
                # Get current season/week
                now = datetime.now(timezone.utc)
                # NFL season typically starts in September
                season = now.year if now.month >= 9 else now.year - 1
                
                # Estimate current week (rough calculation)
                # More sophisticated logic would be needed for accuracy
                week = max(1, min(18, (now.month - 9) * 4 + now.day // 7 + 1))
                
                stats = await collector.collect_week_stats(season, week)
                
                if stats:
                    saved = collector.save_stats(stats)
                    print(f"  Saved {saved} player stat records")
                else:
                    print("  No new stats to save")
        
        except Exception as e:
            print(f"  Error in stats collection: {e}")
    
    def setup_jobs(self):
        """Configure all scheduled jobs."""
        interval_minutes = self.settings.scrape_interval_minutes
        
        # Week 18 continuous scraping: Every 1 minute, 24/7
        # Runs with 70-hour window to catch upcoming games
        self.scheduler.add_job(
            self.scrape_week18,
            IntervalTrigger(minutes=1),
            id='week18_continuous_scrape',
            replace_existing=True,
        )
        
        # Sunday scraping: 6am-11:59pm EST (all games)
        self.scheduler.add_job(
            self.scrape_all_props,
            CronTrigger(
                day_of_week='sun',
                hour='6-23',
                minute=f'*/{interval_minutes}',
                timezone='America/New_York',
            ),
            id='sunday_scrape',
            replace_existing=True,
        )
        
        # Monday Night Football: 4pm-11:59pm EST
        self.scheduler.add_job(
            self.scrape_all_props,
            CronTrigger(
                day_of_week='mon',
                hour='16-23',
                minute=f'*/{interval_minutes}',
                timezone='America/New_York',
            ),
            id='monday_scrape',
            replace_existing=True,
        )
        
        # Thursday Night Football: 4pm-11:59pm EST
        self.scheduler.add_job(
            self.scrape_all_props,
            CronTrigger(
                day_of_week='thu',
                hour='16-23',
                minute=f'*/{interval_minutes}',
                timezone='America/New_York',
            ),
            id='thursday_scrape',
            replace_existing=True,
        )
        
        # Saturday games (late season): 12pm-11:59pm EST
        self.scheduler.add_job(
            self.scrape_all_props,
            CronTrigger(
                day_of_week='sat',
                hour='12-23',
                minute=f'*/{interval_minutes}',
                timezone='America/New_York',
            ),
            id='saturday_scrape',
            replace_existing=True,
        )
        
        # Game stats collection: Tuesday at 6am EST
        self.scheduler.add_job(
            self.collect_game_stats,
            CronTrigger(
                day_of_week='tue',
                hour=6,
                minute=0,
                timezone='America/New_York',
            ),
            id='tuesday_stats',
            replace_existing=True,
        )
        
        print("\n📅 Scheduled jobs configured:")
        for job in self.scheduler.get_jobs():
            print(f"  ✓ {job.id}: {job.trigger}")
        print()
    
    def start(self):
        """Start the scheduler."""
        if not self._is_running:
            self.setup_jobs()
            self.scheduler.start()
            self._is_running = True
            print("Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        if self._is_running:
            self.scheduler.shutdown()
            self._is_running = False
            print("Scheduler stopped")
    
    def run_now(self, job_id: str):
        """
        Manually trigger a job to run immediately.
        
        Args:
            job_id: The job ID to trigger
        """
        job = self.scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now(timezone.utc))
            print(f"Triggered job: {job_id}")
        else:
            print(f"Job not found: {job_id}")


# Global scheduler instance
_scheduler: Optional[ScraperScheduler] = None


def get_scheduler() -> ScraperScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = ScraperScheduler()
    return _scheduler


async def main():
    """Example usage of the scheduler."""
    scheduler = get_scheduler()
    
    # Start the scheduler
    scheduler.start()
    
    print("Scheduler is running. Press Ctrl+C to stop.")
    
    try:
        # Keep the script running
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        scheduler.stop()
        print("Scheduler stopped.")


if __name__ == "__main__":
    asyncio.run(main())

