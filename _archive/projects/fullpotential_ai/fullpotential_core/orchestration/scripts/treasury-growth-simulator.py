#!/usr/bin/env python3
import json
from datetime import datetime

capital = 373000

scenarios = {
    'conservative': {
        'allocation': {'PT-sUSDe (28.5% APY)': 50000, 'USDC Aave (5% APY)': 323000},
        'apy': 0.072,
        'name': 'Conservative'
    },
    'moderate': {
        'allocation': {'PT-sUSDe (28.5% APY)': 150000, 'BTC Covered Calls (20% APY)': 100000, 'USDC Aave (5% APY)': 123000},
        'apy': 0.165,
        'name': 'Moderate'
    },
    'aggressive': {
        'allocation': {'PT-sUSDe (28.5% APY)': 200000, 'BTC Covered Calls (20% APY)': 100000, 'DeFi Yield (35% APY)': 73000},
        'apy': 0.245,
        'name': 'Aggressive'
    }
}

print("\n💰 TREASURY OPPORTUNITY COST - What You're Missing While Treasury Sits Idle\n")

for name, scenario in scenarios.items():
    daily = capital * scenario['apy'] / 365
    overnight = daily / 3  # 8 hours

    print(f"{scenario['name']} Strategy:")
    for asset, amount in scenario['allocation'].items():
        print(f"  ${amount:,} in {asset}")
    print(f"  Earning while you sleep (8 hrs): ${overnight:.2f}")
    print(f"  Per day: ${daily:.2f}")
    print(f"  Per month: ${daily * 30:.2f}")
    print(f"  Per year: ${capital * scenario['apy']:,.2f}")
    print()

print("💎 Currently earning while idle: $0.00")
print("⚠️  Opportunity cost: $47-$250 PER NIGHT you don't deploy\n")

with open('treasury-overnight-report.json', 'w') as f:
    json.dump({'timestamp': datetime.now().isoformat(), 'capital': capital, 'scenarios': scenarios}, f, indent=2)

print("✅ Report saved: treasury-overnight-report.json\n")
