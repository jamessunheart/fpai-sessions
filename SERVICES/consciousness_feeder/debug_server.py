#!/usr/bin/env python3
"""
Server-Side Consciousness Debug
===============================
Debug script to run on the server to test consciousness feeder
"""

import asyncio
import httpx
import json
from datetime import datetime, timezone
import sys
import os

# Add the app path
sys.path.append('/opt/fpai/apps/consciousness_feeder')

try:
    from app.reflecting_feeder import ReflectingFeeder
    from app.identity_feeder import IdentityFeeder
    from app.thinking_feeder import ThinkingFeeder
    from app.doing_feeder import DoingFeeder
    IMPORTS_WORK = True
except ImportError as e:
    print(f"❌ Import failed: {e}")
    IMPORTS_WORK = False

async def debug_server_consciousness():
    """Debug consciousness on the actual server"""

    print("🔍 SERVER-SIDE CONSCIOUSNESS DEBUG")
    print("=" * 40)

    if not IMPORTS_WORK:
        print("❌ Cannot import consciousness feeders")
        return

    print("✅ Imports successful")

    # Test each feeder
    feeders = [
        ("REFLECTING", ReflectingFeeder()),
        ("IDENTITY", IdentityFeeder()),
        ("THINKING", ThinkingFeeder()),
        ("DOING", DoingFeeder())
    ]

    for name, feeder in feeders:
        print(f"\n🧠 Testing {name} Feeder...")
        try:
            data = await feeder.collect_data()
            print(f"   ✅ Collected {len(data)} data points")

            # Test sending to nerve center
            nerve_url = f"http://localhost:8120/api/conscious/pillar/{name.lower()}/feed"
            print(f"   📡 Sending to: {nerve_url}")

            test_payload = {
                "pillar": name,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "consciousness_feeder_debug"
            }

            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(nerve_url, json=test_payload)
                    if response.status_code == 200:
                        print(f"   ✅ Successfully sent to nerve center")
                    else:
                        print(f"   ❌ Nerve center returned: {response.status_code}")
                        print(f"       Response: {response.text[:100]}")
            except Exception as e:
                print(f"   ❌ Cannot reach nerve center: {e}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Test nerve center connectivity
    print(f"\n🌐 Testing nerve center connectivity...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8120/api/conscious/state")
            if response.status_code == 200:
                data = response.json()
                print("✅ Nerve center is accessible")
                print(f"   System: {data.get('system', 'unknown')}")
                print(f"   Pillars: {len(data.get('pillars', {}))}")
            else:
                print(f"❌ Nerve center returned: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot reach nerve center: {e}")

    # Test external connectivity
    print(f"\n🌍 Testing external connectivity...")
    test_urls = [
        "https://hacker-news.firebaseio.com/v0/topstories.json",
        "http://export.arxiv.org/api/query?search_query=ai&start=0&max_results=1"
    ]

    for url in test_urls:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    print(f"✅ {url.split('//')[1].split('/')[0]}: accessible")
                else:
                    print(f"❌ {url.split('//')[1].split('/')[0]}: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {url.split('//')[1].split('/')[0]}: {str(e)[:50]}...")

if __name__ == "__main__":
    asyncio.run(debug_server_consciousness())














