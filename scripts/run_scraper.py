#!/usr/bin/env python
"""
CLI script for manually running the prop line scraper.

Usage:
    # Scrape all players in current week's games
    python scripts/run_scraper.py

    # Scrape all players for a specific week (e.g., Week 18)
    python scripts/run_scraper.py --week 18

    # Scrape specific players
    python scripts/run_scraper.py --players "Saquon Barkley" "Derrick Henry"

    # Scrape only rushing yards props
    python scripts/run_scraper.py --prop-type rushing

    # Scrape only receiving yards props for Week 18
    python scripts/run_scraper.py --week 18 --prop-type receiving
"""

import asyncio
import argparse
import logging
from datetime import datetime, timezone
from typing import List, Optional

from src.collectors.bettingpros import BettingProsCollector
from src.collectors.player_discovery import PlayerDiscovery
from src.models.database import PropType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)

# Suppress noisy loggers
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('hpack').setLevel(logging.WARNING)
logging.getLogger('h2').setLevel(logging.WARNING)


async def scrape_specific_players(
    player_names: List[str],
    prop_types: Optional[List[PropType]] = None,
):
    """
    Scrape specific players by name.
    
    Args:
        player_names: List of player names to scrape
        prop_types: List of prop types to scrape (defaults to both)
    """
    if prop_types is None:
        prop_types = [PropType.RUSHING_YARDS, PropType.RECEIVING_YARDS]
    
    print(f"\n{'='*60}")
    print(f"Scraping {len(player_names)} player(s)...")
    print(f"Prop types: {', '.join(p.value for p in prop_types)}")
    print(f"{'='*60}\n")
    
    # First, discover players to get their event_ids
    print("Discovering players and their games...")
    async with PlayerDiscovery() as discovery:
        all_players = await discovery.get_weekly_players()
        
        # Match requested players by name
        players_to_scrape = []
        for requested_name in player_names:
            requested_slug = requested_name.lower().replace(" ", "-").replace(".", "").replace("'", "")
            
            # Find matching player
            found = False
            for player in all_players:
                player_slug = player['name'].lower().replace(" ", "-").replace(".", "").replace("'", "")
                if player_slug == requested_slug:
                    players_to_scrape.append(player)
                    print(f"  ✓ Found {player['name']} (Event: {player.get('event_id')})")
                    found = True
                    break
            
            if not found:
                print(f"  ✗ Player not found: {requested_name}")
        
        if not players_to_scrape:
            print("\n✗ No players found in current week's games\n")
            return
    
    print()
    
    async with BettingProsCollector() as collector:
        snapshots = await collector.scrape_all_players(players_to_scrape, prop_types)
        
        if snapshots:
            print(f"\n{'='*60}")
            print(f"Scraped {len(snapshots)} prop snapshot(s):")
            print(f"{'='*60}")
            
            for snapshot in snapshots:
                consensus = snapshot.consensus_line or "N/A"
                dk = snapshot.draftkings_line or "N/A"
                fd = snapshot.fanduel_line or "N/A"
                
                print(f"\n  {snapshot.player_name} - {snapshot.prop_type.value}")
                print(f"    Consensus: {consensus}")
                print(f"    DraftKings: {dk}")
                print(f"    FanDuel: {fd}")
            
            # Save to database
            saved = collector.save_snapshots(snapshots)
            print(f"\n{'='*60}")
            print(f"✓ Saved {saved} snapshot(s) to database")
            print(f"{'='*60}\n")
        else:
            print("\n✗ No snapshots collected (pages may not exist or had no data)\n")


async def scrape_all_weekly_players(
    prop_types: Optional[List[PropType]] = None,
    hours_before_kickoff: float = 12.0,
    week: Optional[int] = None,
):
    """
    Scrape all players in upcoming games for the current week.
    
    Args:
        prop_types: List of prop types to scrape (defaults to both)
        hours_before_kickoff: Only scrape games starting within this many hours
        week: NFL week number (1-18, or None for current)
    """
    if prop_types is None:
        prop_types = [PropType.RUSHING_YARDS, PropType.RECEIVING_YARDS]
    
    week_str = f"Week {week}" if week else "current week"
    print(f"\n{'='*60}")
    print(f"Discovering players for {week_str}...")
    print(f"Games starting within {hours_before_kickoff} hours")
    print(f"Prop types: {', '.join(p.value for p in prop_types)}")
    print(f"{'='*60}\n")
    
    async with PlayerDiscovery() as discovery:
        # Get all players for specified week
        all_players = await discovery.get_weekly_players(week=week, use_cache=False)
        print(f"  Found {len(all_players)} total player(s) this week")
        
        # Filter to players whose games are starting soon
        players_to_scrape = discovery.get_players_for_scraping(
            all_players,
            hours_before_kickoff=hours_before_kickoff,
        )
        
        if not players_to_scrape:
            print(f"\n✗ No games starting within {hours_before_kickoff} hours")
            print(f"  Tip: Increase the time window with --hours-before-kickoff")
            print()
            return
        
        print(f"  Found {len(players_to_scrape)} player(s) in scraping window\n")
        
        # Show players we're about to scrape
        print("Players to scrape:")
        for player in players_to_scrape[:10]:  # Show first 10
            game_time = player.get('game_commence_time', 'Unknown')
            print(f"  - {player['name']} (Game: {game_time})")
        
        if len(players_to_scrape) > 10:
            print(f"  ... and {len(players_to_scrape) - 10} more")
        
        print()
    
    # Scrape all players
    async with BettingProsCollector() as collector:
        snapshots = await collector.scrape_all_players(players_to_scrape, prop_types)
        
        if snapshots:
            print(f"\n{'='*60}")
            print(f"Scraped {len(snapshots)} prop snapshot(s)")
            print(f"{'='*60}\n")
            
            # Save to database
            saved = collector.save_snapshots(snapshots)
            print(f"✓ Saved {saved} snapshot(s) to database\n")
        else:
            print("\n✗ No snapshots collected\n")


def main():
    parser = argparse.ArgumentParser(
        description="Manually run the prop line scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape all players in current week's upcoming games
  python scripts/run_scraper.py

  # Scrape specific week (e.g., Week 18)
  python scripts/run_scraper.py --week 18

  # Scrape specific players
  python scripts/run_scraper.py --players "Saquon Barkley" "Derrick Henry"

  # Scrape only rushing yards for Week 18
  python scripts/run_scraper.py --week 18 --prop-type rushing

  # Scrape games starting within 24 hours
  python scripts/run_scraper.py --hours-before-kickoff 24
  
  # Enable verbose logging to see detailed scraping progress
  python scripts/run_scraper.py --verbose --week 18
  
Note: BettingPros only has data for upcoming games (24-48h before kickoff).
      For testing, use scripts/load_mock_data.py to create sample data.
        """,
    )
    
    parser.add_argument(
        "--players",
        nargs="+",
        help="Specific player name(s) to scrape (e.g., 'Saquon Barkley' 'Derrick Henry')",
    )
    
    parser.add_argument(
        "--prop-type",
        choices=["rushing", "receiving", "both"],
        default="both",
        help="Type of prop to scrape (default: both)",
    )
    
    parser.add_argument(
        "--hours-before-kickoff",
        type=float,
        default=12.0,
        help="Only scrape games starting within this many hours (default: 12.0)",
    )
    
    parser.add_argument(
        "--week",
        type=int,
        choices=range(1, 19),
        metavar="1-18",
        help="NFL week number (1-18). If not specified, uses current week",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging (shows detailed scraping progress)",
    )
    
    args = parser.parse_args()
    
    # Configure logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('src.collectors.bettingpros').setLevel(logging.DEBUG)
    
    # Determine prop types
    prop_types = []
    if args.prop_type in ["rushing", "both"]:
        prop_types.append(PropType.RUSHING_YARDS)
    if args.prop_type in ["receiving", "both"]:
        prop_types.append(PropType.RECEIVING_YARDS)
    
    # Run scraper
    if args.players:
        asyncio.run(scrape_specific_players(args.players, prop_types))
    else:
        asyncio.run(scrape_all_weekly_players(prop_types, args.hours_before_kickoff, args.week))


if __name__ == "__main__":
    main()

