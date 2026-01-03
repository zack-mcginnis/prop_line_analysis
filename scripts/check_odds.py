"""Quick script to check if odds are being saved to the database."""

from src.models.database import PropLineSnapshot, get_session

def check_odds():
    session = get_session()
    try:
        # Get the 20 most recent snapshots
        snapshots = (
            session.query(PropLineSnapshot)
            .order_by(PropLineSnapshot.snapshot_time.desc())
            .limit(20)
            .all()
        )
        
        print(f"\n📊 Checking {len(snapshots)} most recent snapshots:\n")
        
        with_odds = 0
        without_odds = 0
        
        for snap in snapshots:
            has_odds = snap.consensus_over_odds is not None or snap.consensus_under_odds is not None
            status = "✓" if has_odds else "✗"
            
            print(f"{status} {snap.player_name[:25]:25} | Line: {snap.consensus_line:5} | "
                  f"Over: {snap.consensus_over_odds if snap.consensus_over_odds else 'None':>5} | "
                  f"Under: {snap.consensus_under_odds if snap.consensus_under_odds else 'None':>5} | "
                  f"Time: {snap.snapshot_time.strftime('%H:%M:%S')}")
            
            if has_odds:
                with_odds += 1
            else:
                without_odds += 1
        
        print(f"\n📈 Summary:")
        print(f"  With odds: {with_odds}/{len(snapshots)}")
        print(f"  Without odds: {without_odds}/{len(snapshots)}")
        
        if without_odds > 0:
            print(f"\n⚠️  {without_odds} snapshot(s) are missing odds data!")
            print(f"  This suggests the BettingPros API may not be returning odds,")
            print(f"  or they're not being parsed correctly.")
        else:
            print(f"\n✅ All snapshots have odds data!")
    
    finally:
        session.close()


if __name__ == "__main__":
    check_odds()

