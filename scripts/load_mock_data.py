#!/usr/bin/env python
"""
Load mock prop line data into the database for testing.

This script loads realistic mock data that simulates various scenarios
including line movements that test the thesis.

Usage:
    # Load all mock data
    python scripts/load_mock_data.py

    # Clear existing data first
    python scripts/load_mock_data.py --clear

    # Dry run (show what would be loaded)
    python scripts/load_mock_data.py --dry-run
"""

import json
import argparse
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import List

from src.models.database import (
    PropLineSnapshot,
    PropType,
    DataSource,
    get_session,
)


def load_mock_data(clear_existing: bool = False, dry_run: bool = False) -> int:
    """
    Load mock data from JSON file into database.
    
    Args:
        clear_existing: If True, delete all existing snapshots first
        dry_run: If True, don't actually save to database
        
    Returns:
        Number of snapshots loaded
    """
    # Load JSON data
    mock_data_path = Path(__file__).parent.parent / "mock_data" / "prop_snapshots.json"
    
    print(f"\n{'='*70}")
    print("Loading Mock Prop Line Data")
    print(f"{'='*70}\n")
    
    if not mock_data_path.exists():
        print(f"❌ Mock data file not found: {mock_data_path}")
        return 0
    
    with open(mock_data_path, 'r') as f:
        data = json.load(f)
    
    print(f"📄 Loaded mock data file: {mock_data_path.name}\n")
    
    # Show scenarios
    if 'scenarios' in data:
        print("📊 Mock Data Scenarios:")
        for key, description in data['scenarios'].items():
            print(f"   • {description}")
        print()
    
    # Parse snapshots
    all_snapshots = []
    
    for player_data in data.get('snapshots', []):
        event_id = player_data['event_id']
        game_commence_time = datetime.fromisoformat(
            player_data['game_commence_time'].replace('Z', '+00:00')
        )
        home_team = player_data['home_team']
        away_team = player_data['away_team']
        player_name = player_data['player_name']
        player_slug = player_data['player_slug']
        
        # Map prop type
        prop_type_str = player_data['prop_type']
        prop_type = (
            PropType.RUSHING_YARDS if prop_type_str == 'rushing_yards'
            else PropType.RECEIVING_YARDS
        )
        
        # Create snapshots for each timeline point
        for snapshot_data in player_data['snapshots_timeline']:
            snapshot_time = datetime.fromisoformat(
                snapshot_data['snapshot_time'].replace('Z', '+00:00')
            )
            
            # Generate realistic odds (usually -110, but vary slightly)
            # When line drops significantly, odds typically get juicier on the under
            import random
            over_odds = snapshot_data.get('over_odds', random.choice([-110, -110, -115, -105]))
            under_odds = snapshot_data.get('under_odds', random.choice([-110, -110, -115, -105]))
            
            snapshot = PropLineSnapshot(
                event_id=event_id,
                game_commence_time=game_commence_time,
                home_team=home_team,
                away_team=away_team,
                player_name=player_name,
                player_slug=player_slug,
                prop_type=prop_type,
                consensus_line=Decimal(str(snapshot_data['consensus_line'])),
                draftkings_line=Decimal(str(snapshot_data.get('draftkings_line'))) if snapshot_data.get('draftkings_line') else None,
                fanduel_line=Decimal(str(snapshot_data.get('fanduel_line'))) if snapshot_data.get('fanduel_line') else None,
                betmgm_line=Decimal(str(snapshot_data.get('betmgm_line'))) if snapshot_data.get('betmgm_line') else None,
                caesars_line=Decimal(str(snapshot_data.get('caesars_line'))) if snapshot_data.get('caesars_line') else None,
                pointsbet_line=Decimal(str(snapshot_data.get('pointsbet_line'))) if snapshot_data.get('pointsbet_line') else None,
                over_odds=over_odds,
                under_odds=under_odds,
                snapshot_time=snapshot_time,
                source_timestamp=snapshot_time,
                hours_before_kickoff=Decimal(str(snapshot_data['hours_before_kickoff'])),
                source=DataSource.BETTINGPROS,
                raw_data=json.dumps({
                    "mock": True,
                    "note": snapshot_data.get('_note', ''),
                }),
            )
            all_snapshots.append(snapshot)
    
    # Show summary
    print(f"📈 Mock Data Summary:")
    print(f"   Total snapshots: {len(all_snapshots)}")
    
    unique_players = len(set(s.player_name for s in all_snapshots))
    unique_games = len(set(s.event_id for s in all_snapshots))
    rushing = sum(1 for s in all_snapshots if s.prop_type == PropType.RUSHING_YARDS)
    receiving = sum(1 for s in all_snapshots if s.prop_type == PropType.RECEIVING_YARDS)
    
    print(f"   Unique players: {unique_players}")
    print(f"   Unique games: {unique_games}")
    print(f"   Rushing props: {rushing}")
    print(f"   Receiving props: {receiving}")
    print()
    
    # Show line movements
    print("🔽 Line Movements to Test Thesis:")
    movement_count = 0
    
    # Group by player
    player_snapshots = {}
    for snapshot in all_snapshots:
        key = f"{snapshot.player_name}_{snapshot.prop_type.value}"
        if key not in player_snapshots:
            player_snapshots[key] = []
        player_snapshots[key].append(snapshot)
    
    # Find movements
    for key, snapshots in player_snapshots.items():
        snapshots_sorted = sorted(snapshots, key=lambda s: s.hours_before_kickoff, reverse=True)
        
        if len(snapshots_sorted) >= 2:
            first = snapshots_sorted[0]
            last = snapshots_sorted[-1]
            
            if first.consensus_line and last.consensus_line:
                drop = float(first.consensus_line - last.consensus_line)
                drop_pct = (drop / float(first.consensus_line)) * 100
                
                # Only show significant drops within 3 hours
                if drop > 5 and last.hours_before_kickoff <= 3:
                    movement_count += 1
                    print(f"   • {first.player_name} ({first.prop_type.value}):")
                    print(f"     {first.consensus_line} → {last.consensus_line} yards")
                    print(f"     Drop: {drop:.1f} yards ({drop_pct:.1f}%)")
                    print(f"     At: {last.hours_before_kickoff}h before kickoff")
    
    print(f"\n   Found {movement_count} significant late drops (tests thesis)")
    print()
    
    if dry_run:
        print("🔵 DRY RUN MODE - No data will be saved to database\n")
        return len(all_snapshots)
    
    # Database operations
    session = get_session()
    
    try:
        # Clear existing data if requested
        if clear_existing:
            print("🗑️  Clearing existing mock data...")
            count = session.query(PropLineSnapshot).filter(
                PropLineSnapshot.event_id.like('mock_%')
            ).delete(synchronize_session=False)
            session.commit()
            print(f"   ✓ Deleted {count} existing mock snapshot(s)\n")
        
        # Save new data
        print("💾 Saving to database...")
        session.add_all(all_snapshots)
        session.commit()
        print(f"   ✓ Saved {len(all_snapshots)} snapshot(s)\n")
        
        print(f"{'='*70}")
        print("✅ Mock data loaded successfully!")
        print(f"{'='*70}\n")
        
        print("Next steps:")
        print("  1. Start backend: uv run uvicorn src.api.main:app --reload")
        print("  2. View snapshots: curl http://localhost:8000/api/props/snapshots")
        print("  3. Check movements: curl http://localhost:8000/api/movements/")
        print("  4. Start dashboard: cd frontend && yarn dev")
        print()
        
        return len(all_snapshots)
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error saving to database: {e}")
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Load mock prop line data for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load mock data
  python scripts/load_mock_data.py

  # Clear existing mock data and reload
  python scripts/load_mock_data.py --clear

  # Show what would be loaded without saving
  python scripts/load_mock_data.py --dry-run

The mock data includes realistic scenarios:
  • Players with significant late line drops (tests thesis)
  • Players with early drops that stabilize
  • Players with stable lines
  • Players with line increases (inverse scenario)
  
This allows you to test:
  • API endpoints
  • Line movement detection
  • Statistical analysis
  • Dashboard visualizations
        """,
    )
    
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing mock data before loading",
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be loaded without saving to database",
    )
    
    args = parser.parse_args()
    
    try:
        load_mock_data(clear_existing=args.clear, dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nFatal error: {e}")
        raise


if __name__ == "__main__":
    main()

