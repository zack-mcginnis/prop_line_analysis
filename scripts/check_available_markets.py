#!/usr/bin/env python
"""
Script to check what markets are available for your The Odds API key.
This helps diagnose what data your subscription plan has access to.
"""

import asyncio
import json
import httpx
from src.config import get_settings


async def check_markets():
    """Check available markets and sports."""
    settings = get_settings()
    
    if not settings.odds_api_key:
        print("❌ No API key found in .env")
        return
    
    base_url = settings.odds_api_base_url
    api_key = settings.odds_api_key
    
    print("=" * 70)
    print("The Odds API - Available Markets Check")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Check sports
        print("\n1. Checking available sports...")
        try:
            response = await client.get(
                f"{base_url}/sports",
                params={"apiKey": api_key}
            )
            response.raise_for_status()
            sports = response.json()
            
            nfl_sport = next((s for s in sports if s["key"] == "americanfootball_nfl"), None)
            if nfl_sport:
                print(f"   ✓ NFL found: {nfl_sport['title']}")
                print(f"     Active: {nfl_sport['active']}")
                print(f"     Has outrights: {nfl_sport.get('has_outrights', False)}")
            else:
                print("   ⚠️  NFL not found or not active")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 2. Try to get live odds with basic market (h2h)
        print("\n2. Checking live odds endpoint (h2h market)...")
        try:
            response = await client.get(
                f"{base_url}/sports/americanfootball_nfl/odds",
                params={
                    "apiKey": api_key,
                    "regions": "us",
                    "markets": "h2h",
                }
            )
            response.raise_for_status()
            data = response.json()
            
            print(f"   ✓ Live odds endpoint works!")
            print(f"   Found {len(data)} upcoming games")
            
            if data:
                print(f"\n   Sample game:")
                game = data[0]
                print(f"   {game['away_team']} @ {game['home_team']}")
                print(f"   Commence: {game['commence_time']}")
                print(f"   Markets available in this game:")
                if game.get('bookmakers'):
                    markets = set()
                    for book in game['bookmakers']:
                        for market in book.get('markets', []):
                            markets.add(market['key'])
                    for m in sorted(markets):
                        print(f"     - {m}")
        except httpx.HTTPStatusError as e:
            print(f"   ❌ HTTP {e.response.status_code} Error")
            print(f"   Response: {e.response.text[:200]}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 3. Try player props market
        print("\n3. Checking if player props are available (player_rush_yds)...")
        try:
            response = await client.get(
                f"{base_url}/sports/americanfootball_nfl/odds",
                params={
                    "apiKey": api_key,
                    "regions": "us",
                    "markets": "player_rush_yds",
                }
            )
            response.raise_for_status()
            data = response.json()
            
            print(f"   ✓ Player props ARE available!")
            print(f"   Found {len(data)} games with player_rush_yds")
            
            # Count total props
            prop_count = 0
            for game in data:
                for book in game.get('bookmakers', []):
                    for market in book.get('markets', []):
                        if market['key'] == 'player_rush_yds':
                            prop_count += len(market.get('outcomes', [])) // 2
            
            print(f"   Total rushing props available: {prop_count}")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                print(f"   ❌ 422 Error: Player props NOT available in live odds endpoint")
                print(f"   Your subscription may not include live player props.")
                print(f"   Player props may only be available through historical endpoint.")
            else:
                print(f"   ❌ HTTP {e.response.status_code} Error")
                print(f"   Response: {e.response.text[:200]}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 4. Check quota
        print("\n4. Checking API quota...")
        try:
            response = await client.get(
                f"{base_url}/sports",
                params={"apiKey": api_key}
            )
            used = response.headers.get("x-requests-used", "?")
            remaining = response.headers.get("x-requests-remaining", "?")
            
            print(f"   Quota used: {used}")
            print(f"   Quota remaining: {remaining}")
        except Exception as e:
            print(f"   ❌ Error checking quota: {e}")
    
    print("\n" + "=" * 70)
    print("Summary:")
    print("=" * 70)
    print("""
If player props show as NOT available:
- Your current plan may only support basic markets (h2h, spreads, totals)
- Player props may require a higher tier subscription
- For live player props, consider using BettingPros scraper instead
- Check your plan at: https://the-odds-api.com/

If you need player prop data:
1. Use BettingPros scraper (free): `uv run python scripts/run_scraper.py`
2. Upgrade to a plan with player props support
3. Use historical player props if available in your plan
    """)


if __name__ == "__main__":
    asyncio.run(check_markets())

