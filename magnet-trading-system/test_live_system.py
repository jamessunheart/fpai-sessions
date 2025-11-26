#!/usr/bin/env python3
"""
Test the live WhaleTrack + Magnet Trading System

This sends sample candle data and demonstrates the system's analysis.
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://198.54.123.234:8600"

def generate_sample_candles():
    """Generate sample BTC candle data showing an uptrend toward a magnet."""
    base_price = 43000
    current_time = datetime.now().timestamp()
    
    candles = []
    
    # Simulate uptrend with displacement
    prices = [
        (43000, 43050, 42980, 43020),  # Consolidation
        (43020, 43100, 43010, 43080),  # Small up
        (43080, 43150, 43070, 43140),  # Building
        (43140, 43300, 43130, 43280),  # Displacement!
        (43280, 43350, 43260, 43320),  # Continuation
        (43320, 43400, 43310, 43380),  # Still going
        (43380, 43420, 43360, 43400),  # Slowing
        (43400, 43450, 43390, 43430),  # Near magnet at 43500
    ]
    
    for i, (o, h, l, c) in enumerate(prices):
        candles.append({
            "timestamp": current_time - (len(prices) - i) * 300,  # 5min candles
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": 100 + (i * 10)
        })
    
    return candles

def test_system():
    """Test the WhaleTrack system"""
    
    print("🐋 Testing WhaleTrack + Magnet Trading System")
    print("=" * 60)
    
    # 1. Health check
    print("\n1️⃣ Health Check...")
    resp = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {resp.json()['status']}")
    print(f"   Name: {resp.json()['name']}")
    
    # 2. Send candle data
    print("\n2️⃣ Sending Sample Candle Data (BTC uptrend)...")
    candles = generate_sample_candles()
    
    resp = requests.post(f"{BASE_URL}/api/whale/update", json=candles)
    
    if resp.status_code == 200:
        print("   ✅ Data processed successfully")
    else:
        print(f"   ❌ Error: {resp.text}")
        return
    
    # 3. Get whale status
    print("\n3️⃣ Whale Position Analysis...")
    resp = requests.get(f"{BASE_URL}/api/whale/status")
    data = resp.json()
    
    whale = data.get('whale', {})
    print(f"   Direction: {whale.get('direction', 'N/A').upper()}")
    print(f"   Velocity: {whale.get('velocity', 0):.1f}/100")
    print(f"   Confidence: {whale.get('confidence', 0):.1f}%")
    print(f"   Displacement: {whale.get('displacement', 0):.1f}/100")
    
    # 4. Get magnets
    print("\n4️⃣ Detected Magnets...")
    resp = requests.get(f"{BASE_URL}/api/magnets/current")
    magnets_data = resp.json()
    
    print(f"   Total Magnets Found: {magnets_data.get('count', 0)}")
    
    for i, magnet in enumerate(magnets_data.get('magnets', [])[:3], 1):
        print(f"   #{i} | Price: ${magnet['price']:,.2f} | Score: {magnet['score']:.1f}% | Type: {magnet['type']}")
    
    # 5. Get flow path
    print("\n5️⃣ Flow Path to Target...")
    resp = requests.get(f"{BASE_URL}/api/flow/current")
    flow = resp.json()
    
    if flow.get('active'):
        target = flow.get('target_magnet', {})
        print(f"   Target: ${target.get('price', 0):,.2f}")
        print(f"   Distance: {target.get('distance_pct', 0):.2f}%")
        print(f"   Efficiency: {flow.get('efficiency_score', 0):.1f}/100")
        print(f"   Confidence: {flow.get('confidence', 0):.1f}%")
        print(f"   Obstructions: {flow.get('obstructions', 0)}")
    else:
        print(f"   ⚠️  No clear flow path: {flow.get('reason', 'Unknown')}")
    
    # 6. Check for entry signal
    print("\n6️⃣ Entry Signal...")
    resp = requests.get(f"{BASE_URL}/api/signals/entry")
    signal = resp.json()
    
    if signal.get('active'):
        print(f"   ✅ ENTRY SIGNAL ACTIVE")
        print(f"   Type: {signal.get('entry_type', 'N/A').upper()}")
        print(f"   Entry: ${signal.get('entry_price', 0):,.2f}")
        print(f"   Stop: ${signal.get('stop_loss', 0):,.2f}")
        print(f"   Target: ${signal.get('target_price', 0):,.2f}")
        print(f"   R:R: {signal.get('risk_reward', 0):.2f}:1")
        print(f"   Confidence: {signal.get('confidence', 0):.1f}%")
        print(f"   Reason: {signal.get('reason', 'N/A')}")
    else:
        print(f"   ⚠️  No entry signal")
    
    # 7. Check position
    print("\n7️⃣ Current Position...")
    resp = requests.get(f"{BASE_URL}/api/position/current")
    pos = resp.json()
    
    if pos.get('active'):
        print(f"   ✅ POSITION OPEN")
        print(f"   Type: {'LONG' if pos.get('is_long') else 'SHORT'}")
        print(f"   Entry: ${pos.get('entry_price', 0):,.2f}")
        print(f"   Target: ${pos.get('target_price', 0):,.2f}")
    else:
        print(f"   No position open")
    
    # 8. System summary
    print("\n8️⃣ System Summary...")
    print(f"   Trades Today: {data.get('trades_today', 0)}")
    print(f"   Max Trades: 2")
    
    print("\n" + "=" * 60)
    print("🐋 Test Complete!")
    print("\nThe system is analyzing liquidity flow and tracking the whale.")
    print("It will generate entry signals when:")
    print("  - Whale direction is clear (not FOG)")
    print("  - High-probability magnet is identified")
    print("  - Flow path has low obstructions")
    print("  - R:R ratio >= 2:1")

if __name__ == "__main__":
    try:
        test_system()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is the service running?")
    except Exception as e:
        print(f"❌ Error: {e}")

