"""Initialize demo data to show dashboard in action"""

from datetime import datetime, timedelta
import asyncio
from src.models import SOLDeposit, POTSpending
from src.treasury import treasury

async def init_demo_data():
    """Create initial demo data"""

    print("🎯 Initializing SOL Treasury SSOT with demo data...")

    # Simulate some deposits over the past month
    base_time = datetime.now() - timedelta(days=30)

    deposits = [
        SOLDeposit(
            user_id="user_001",
            sol_amount=100.0,
            sol_price_usd=150.0,
            pot_issued=1000.0,  # 1 SOL → 10 POT
            conversion_rate=10.0,
            timestamp=base_time + timedelta(days=1)
        ),
        SOLDeposit(
            user_id="user_002",
            sol_amount=250.0,
            sol_price_usd=155.0,
            pot_issued=2500.0,
            conversion_rate=10.0,
            timestamp=base_time + timedelta(days=7)
        ),
        SOLDeposit(
            user_id="user_003",
            sol_amount=500.0,
            sol_price_usd=160.0,
            pot_issued=5000.0,
            conversion_rate=10.0,
            timestamp=base_time + timedelta(days=14)
        ),
        SOLDeposit(
            user_id="user_001",
            sol_amount=300.0,
            sol_price_usd=158.0,
            pot_issued=3000.0,
            conversion_rate=10.0,
            timestamp=base_time + timedelta(days=21)
        ),
        SOLDeposit(
            user_id="user_004",
            sol_amount=200.0,
            sol_price_usd=162.0,
            pot_issued=2000.0,
            conversion_rate=10.0,
            timestamp=base_time + timedelta(days=25)
        ),
    ]

    # Simulate POT spending with 2x+ value creation
    spending = [
        POTSpending(
            user_id="user_001",
            service="i-match",
            pot_spent=500.0,
            value_created_usd=1200.0,  # 2.4x ROI
            roi_multiplier=2.4,
            description="Career coaching package - got job offer with $30K salary increase",
            timestamp=base_time + timedelta(days=10)
        ),
        POTSpending(
            user_id="user_002",
            service="i-match",
            pot_spent=800.0,
            value_created_usd=1680.0,  # 2.1x ROI
            roi_multiplier=2.1,
            description="Financial advisor - saved $15K on taxes, optimized investments",
            timestamp=base_time + timedelta(days=15)
        ),
        POTSpending(
            user_id="user_003",
            service="i-match",
            pot_spent=1200.0,
            value_created_usd=3000.0,  # 2.5x ROI
            roi_multiplier=2.5,
            description="Business consultant - increased revenue by $80K",
            timestamp=base_time + timedelta(days=20)
        ),
        POTSpending(
            user_id="user_001",
            service="jobs",
            pot_spent=300.0,
            value_created_usd=720.0,  # 2.4x ROI
            roi_multiplier=2.4,
            description="Job placement - placed in $95K/year position",
            timestamp=base_time + timedelta(days=26)
        ),
    ]

    # Record all data
    for deposit in deposits:
        treasury.record_deposit(deposit)
        print(f"  ✅ Deposit: {deposit.sol_amount} SOL → {deposit.pot_issued} POT")

    for spend in spending:
        treasury.record_spending(spend)
        print(f"  ✅ Spending: {spend.pot_spent} POT → ${spend.value_created_usd} value ({spend.roi_multiplier}x)")

    # Calculate and display metrics
    print("\n📊 Treasury Metrics:")
    metrics = await treasury.get_metrics()
    print(f"  SOL Balance: {metrics.sol_balance:.2f} SOL (${metrics.sol_value_usd:,.0f})")
    print(f"  POT Outstanding: {metrics.pot_outstanding:,.0f} POT")
    print(f"  Reserve Ratio: {metrics.reserve_ratio * 100:.1f}% (Target: {metrics.tipping_point_ratio * 100:.0f}%)")
    print(f"  Overall ROI: {metrics.overall_roi_multiplier:.2f}x {'✅ PROVEN 2x!' if metrics.overall_roi_multiplier >= 2.0 else '⚠️'}")
    print(f"  Treasury Status: {metrics.status.value.upper()}")

    if metrics.can_leverage:
        print("\n🎯 TIPPING POINT REACHED - Can leverage SOL without selling!")
    else:
        print(f"\n📈 Need {metrics.sol_needed_for_tipping_point:.2f} more SOL to reach tipping point")
        if metrics.days_to_tipping_point:
            print(f"   Estimated: {metrics.days_to_tipping_point:.0f} days at current growth rate")

    print("\n✅ Demo data initialized successfully!")
    print(f"\n🌐 Dashboard: http://localhost:8035")

if __name__ == "__main__":
    asyncio.run(init_demo_data())
