#!/usr/bin/env python
"""Test script to verify BettingPros event ID mapping."""

import asyncio
from src.collectors.player_discovery import PlayerDiscovery


async def main():
    print("Testing BettingPros Event ID Mapping")
    print("=" * 60)
    
    async with PlayerDiscovery() as discovery:
        # Get weekly schedule from ESPN
        print("\n1. Fetching ESPN schedule...")
        games = await discovery.get_weekly_schedule()
        print(f"   Found {len(games)} games on ESPN")
        
        # Show first few games
        for i, game in enumerate(games[:3]):
            print(f"\n   Game {i+1}:")
            print(f"     ESPN Event ID: {game.get('event_id')}")
            print(f"     {game.get('away_team', {}).get('name')} @ {game.get('home_team', {}).get('name')}")
            print(f"     Time: {game.get('game_commence_time')}")
        
        # Map to BettingPros events
        print("\n2. Fetching BettingPros events and mapping...")
        event_map = await discovery.map_bettingpros_event_ids(games, season="2024-2025")
        
        print(f"\n3. Mapping Results:")
        print(f"   Successfully mapped {len(event_map)} events")
        
        if event_map:
            print("\n   Sample mappings:")
            for i, (espn_id, bp_id) in enumerate(list(event_map.items())[:5]):
                # Find the game
                game = next((g for g in games if g.get('event_id') == espn_id), None)
                if game:
                    print(f"\n   {i+1}. {game.get('away_team', {}).get('abbreviation')} @ {game.get('home_team', {}).get('abbreviation')}")
                    print(f"      ESPN ID: {espn_id}")
                    print(f"      BettingPros ID: {bp_id}")
        
        # Test with player discovery
        print("\n4. Testing player discovery with BettingPros IDs...")
        players = await discovery.get_weekly_players(include_bettingpros_ids=True)
        
        players_with_bp_id = [p for p in players if p.get('bettingpros_event_id')]
        print(f"   Total players: {len(players)}")
        print(f"   Players with BettingPros event ID: {len(players_with_bp_id)}")
        
        if players_with_bp_id:
            print("\n   Sample players with BettingPros event IDs:")
            for player in players_with_bp_id[:5]:
                print(f"     - {player['name']} ({player['team_abbr']})")
                print(f"       ESPN Event ID: {player.get('event_id')}")
                print(f"       BettingPros Event ID: {player.get('bettingpros_event_id')}")


if __name__ == "__main__":
    asyncio.run(main())

