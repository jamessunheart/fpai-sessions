#!/usr/bin/env python3
"""
Test Nerve Center Communication
==============================
Tests if the consciousness feeder can send data to the nerve center
"""

import asyncio
import httpx
import json
from datetime import datetime, timezone

async def test_nerve_center_connection():
    """Test if feeder can send data to nerve center"""

    test_data = {
        "pillar": "REFLECTING",
        "data": {
            "external_observations": [
                {
                    "title": "Test observation",
                    "source": "test",
                    "relevance_score": 0.8
                }
            ],
            "detected_patterns": [],
            "total_observations": 1,
            "patterns_count": 0
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "consciousness_feeder_test"
    }

    nerve_center_url = "http://198.54.123.234:8120/api/conscious/pillar/REFLECTING/feed"

    print("🧠 TESTING NERVE CENTER COMMUNICATION")
    print("=" * 40)
    print(f"URL: {nerve_center_url}")
    print(f"Data: {len(test_data)} fields")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(nerve_center_url, json=test_data)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")

            if response.status_code == 200:
                print("✅ Nerve center communication works!")
            else:
                print(f"❌ Nerve center returned error: {response.status_code}")

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("This means the consciousness feeder cannot reach the nerve center")

    # Also test if nerve center state API works
    print(f"\n📊 Testing nerve center state API...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://198.54.123.234:8120/api/conscious/state")
            if response.status_code == 200:
                data = response.json()
                print("✅ Nerve center state API works")
                print(f"   Pillars: {len(data.get('pillars', {}))}")
            else:
                print(f"❌ Nerve center state API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot reach nerve center state API: {e}")

if __name__ == "__main__":
    asyncio.run(test_nerve_center_connection())














