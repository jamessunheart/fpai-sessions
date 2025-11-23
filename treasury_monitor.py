#!/usr/bin/env python3
"""
Treasury Monitor
Tracks cash position, burn rate, and runway.
Feeds into core/STATE/TREASURY.json for the Pulse Aggregator.
"""
import json
import os
from datetime import datetime
from pathlib import Path

# --- Configuration ---
ROOT_DIR = Path(__file__).parent.parent.absolute()
TREASURY_FILE = ROOT_DIR / "core/STATE/TREASURY.json"

# Default initial state (Human must edit this file to set real bank balances)
DEFAULT_TREASURY = {
    "last_updated": datetime.now().isoformat(),
    "cash_on_hand": 0.0,      # Bank Balance
    "stripe_balance": 0.0,    # Pending Payouts
    "monthly_burn": 100.0,    # Server costs, subscriptions
    "currency": "USD"
}

def load_treasury():
    if not TREASURY_FILE.exists():
        return DEFAULT_TREASURY
    try:
        with open(TREASURY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading treasury: {e}")
        return DEFAULT_TREASURY

def update_treasury(data):
    """Writes the treasury state."""
    TREASURY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TREASURY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def calculate_health(data):
    """Derives runway metrics."""
    cash = data.get("cash_on_hand", 0) + data.get("stripe_balance", 0)
    burn = data.get("monthly_burn", 1) # Avoid div/0
    if burn <= 0: burn = 1.0
    
    runway_months = cash / burn
    
    return {
        "total_liquidity": cash,
        "runway_months": round(runway_months, 1),
        "status": "Critical" if runway_months < 1 else "Stable" if runway_months < 6 else "Healthy"
    }

def main():
    print("💰 Treasury Monitor Active...")
    
    # 1. Load current state
    data = load_treasury()
    
    # 2. (Future) Fetch Stripe Balance via API
    # For now, we rely on the file being manually updated or connected later
    
    # 3. Calculate Health
    health = calculate_health(data)
    data["health"] = health
    data["last_updated"] = datetime.now().isoformat()
    
    # 4. Save
    update_treasury(data)
    print(f"✅ Treasury Updated. Liquidity: ${health['total_liquidity']} | Runway: {health['runway_months']} mo")

if __name__ == "__main__":
    main()

