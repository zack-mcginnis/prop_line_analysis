#!/usr/bin/env python
"""Test BettingPros API to find the correct endpoint for player props."""

import asyncio
import json
import httpx


API_BASE = "https://api.bettingpros.com/v3"
API_KEY = "CHi8Hy5CEE4khd46XNYL23dCFX96oUdw6qOt1Dnh"

# Drake London's player ID (from the page data)
PLAYER_ID = "23163"
PLAYER_SLUG = "drake-london"

# Receiving yards market ID (from the page data)
MARKET_ID = "105"


async def test_endpoint(client, url, params=None):
    """Test an API endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing: {url}")
    if params:
        print(f"Params: {params}")
    print('='*60)
    
    headers = {
        "Accept": "application/json",
        "x-api-key": API_KEY,
        "Referer": "https://www.bettingpros.com/",
    }
    
    try:
        response = await client.get(url, headers=headers, params=params, timeout=10.0)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
            print(f"Response preview: {json.dumps(data, indent=2)[:500]}")
            return data
        else:
            print(f"Error: {response.text[:200]}")
            
    except Exception as e:
        print(f"Exception: {e}")
    
    return None


async def main():
    # Drake London's game event ID
    EVENT_ID = "21583"
    
    async with httpx.AsyncClient() as client:
        # Try the offers endpoint with all required params
        print("\n\nTrying /v3/offers with event_id...")
        result = await test_endpoint(
            client,
            f"{API_BASE}/offers",
            params={
                "market_id": MARKET_ID,
                "event_id": EVENT_ID,
                "player_id": PLAYER_ID
            }
        )
        
        if result:
            print("\n✓ SUCCESS!")
            print("\nFull response:")
            print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

