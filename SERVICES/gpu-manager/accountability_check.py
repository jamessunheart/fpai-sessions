#!/usr/bin/env python3
"""
GPU ACCOUNTABILITY CHECKER
==========================

Run this anytime to see EXACTLY what's happening with Vast.ai.
No promises, no "smart" logic - just facts.

Usage:
    python3 accountability_check.py              # Check status
    python3 accountability_check.py --destroy    # Destroy all instances
    python3 accountability_check.py --watch      # Watch every 60 seconds
"""

import os
import sys
import json
import time
import urllib.request
import ssl
from datetime import datetime

# Bypass SSL verification (for simplicity)
ssl._create_default_https_context = ssl._create_unverified_context

API_KEY = os.environ.get("VASTAI_API_KEY", "1bad9920ce02d7e73e1e33a05de73e01038b1975c2c4ed2f3a13b944d52dd906")


def get_instances():
    """Get all Vast.ai instances"""
    try:
        url = f"https://console.vast.ai/api/v0/instances/?api_key={API_KEY}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            return data.get("instances", [])
    except Exception as e:
        print(f"ERROR: Could not fetch instances: {e}")
        return []


def destroy_instance(instance_id):
    """Destroy a single instance"""
    try:
        url = f"https://console.vast.ai/api/v0/instances/{instance_id}/?api_key={API_KEY}"
        req = urllib.request.Request(url, method='DELETE')
        with urllib.request.urlopen(req, timeout=15) as response:
            return True
    except Exception as e:
        print(f"  Failed to destroy {instance_id}: {e}")
        return False


def print_status():
    """Print current status"""
    print("=" * 60)
    print(f"GPU ACCOUNTABILITY CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    instances = get_instances()
    running = [i for i in instances if i.get("actual_status") == "running"]
    
    hourly_cost = sum(i.get("dph_total", 0) for i in running)
    daily_cost = hourly_cost * 24
    monthly_cost = daily_cost * 30
    
    print(f"\n📊 CURRENT STATE:")
    print(f"   Total instances:    {len(instances)}")
    print(f"   Running instances:  {len(running)}")
    print(f"")
    print(f"💰 CURRENT COST:")
    print(f"   Hourly:   ${hourly_cost:.2f}")
    print(f"   Daily:    ${daily_cost:.2f}")
    print(f"   Monthly:  ${monthly_cost:.2f}")
    
    if running:
        print(f"\n🖥️  RUNNING INSTANCES:")
        for i in running:
            print(f"   {i['id']:>10} | {i.get('gpu_name', 'Unknown'):20} | ${i.get('dph_total', 0):.3f}/hr")
        
        print(f"\n⚠️  WARNING: GPUs are running and costing money!")
        print(f"   Run with --destroy to stop them")
    else:
        print(f"\n✅ NO RUNNING INSTANCES - $0 being spent")
    
    print("")
    print("=" * 60)
    
    return running


def destroy_all():
    """Destroy all running instances"""
    print("\n🚨 DESTROYING ALL INSTANCES...")
    
    instances = get_instances()
    running = [i for i in instances if i.get("actual_status") == "running"]
    
    if not running:
        print("   No instances to destroy")
        return
    
    destroyed = 0
    for inst in running:
        inst_id = inst["id"]
        gpu_name = inst.get("gpu_name", "Unknown")
        cost = inst.get("dph_total", 0)
        
        if destroy_instance(inst_id):
            print(f"   ✅ Destroyed {inst_id} ({gpu_name}) - was ${cost:.3f}/hr")
            destroyed += 1
            time.sleep(1)  # Rate limit
        else:
            print(f"   ❌ Failed {inst_id}")
    
    print(f"\n   Destroyed {destroyed}/{len(running)} instances")
    
    # Verify
    time.sleep(2)
    remaining = len([i for i in get_instances() if i.get("actual_status") == "running"])
    print(f"   Remaining after destroy: {remaining}")
    
    if remaining > 0:
        print(f"\n   ⚠️  STILL RUNNING: {remaining} instances")
        print(f"   The GPU Hunter daemon on your server may be recreating them!")


def watch_mode():
    """Watch mode - check every 60 seconds"""
    print("👁️  WATCH MODE - Checking every 60 seconds (Ctrl+C to stop)")
    print("")
    
    last_count = -1
    
    while True:
        running = print_status()
        current_count = len(running)
        
        if last_count >= 0 and current_count > last_count:
            print(f"\n🚨 ALERT: {current_count - last_count} NEW INSTANCES APPEARED!")
            print(f"   The GPU Hunter is still creating instances!")
        
        last_count = current_count
        
        print(f"\nNext check in 60 seconds... (Ctrl+C to stop)")
        try:
            time.sleep(60)
        except KeyboardInterrupt:
            print("\nStopped watching.")
            break


def main():
    if "--destroy" in sys.argv:
        print_status()
        destroy_all()
        print("\nVerifying...")
        time.sleep(3)
        print_status()
    
    elif "--watch" in sys.argv:
        watch_mode()
    
    else:
        print_status()
        print("\nOptions:")
        print("  --destroy   Destroy all running instances")
        print("  --watch     Watch and alert on new instances")


if __name__ == "__main__":
    main()
