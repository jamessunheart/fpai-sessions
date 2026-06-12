#!/usr/bin/env python3
"""
THE SACRED LOOP - Integration of Treasury + Delegation + AI Services

Revenue → Treasury (60%) + Reinvest (40%)
Treasury → DeFi yields (25-50% APY) → More capital
Reinvest → More VAs → Faster service delivery → More revenue
Compound → Exponential growth

This is the engine that turns $2,500 customers into a $1B+ treasury.
"""

import json
import datetime
from pathlib import Path
from typing import Dict, List
from decimal import Decimal


class SacredLoop:
    """
    The compounding growth engine

    Flow:
    1. AI Service generates revenue ($2,500 - $15,000)
    2. Auto-split: 60% → Treasury, 40% → Reinvestment
    3. Treasury earns DeFi yields (25-50% APY)
    4. Reinvestment funds more VAs → faster execution
    5. Faster execution → more customers → more revenue
    6. Repeat → Exponential growth
    """

    def __init__(self, data_path="/root/delegation-system/sacred-loop"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)

        # Core data files
        self.revenue_log = self.data_path / "revenue_log.json"
        self.treasury_log = self.data_path / "treasury_log.json"
        self.reinvest_log = self.data_path / "reinvest_log.json"
        self.metrics_log = self.data_path / "metrics_log.json"

        # Initialize files
        for log_file in [self.revenue_log, self.treasury_log,
                         self.reinvest_log, self.metrics_log]:
            if not log_file.exists():
                log_file.write_text(json.dumps([], indent=2))

        # Capital allocation strategy
        self.treasury_allocation = 0.60  # 60% to treasury
        self.reinvest_allocation = 0.40  # 40% to reinvest (VAs, tools, ads)

        # Treasury assumptions (from TREASURY_DYNAMIC_STRATEGY.md)
        self.treasury_base_apy = 0.08  # 8% base yield (conservative)
        self.treasury_tactical_apy = 0.40  # 40% tactical plays (aggressive)
        self.treasury_blended_apy = 0.25  # 25% blended (realistic)

    def log_revenue(self, amount: float, service: str, customer_name: str,
                    fulfillment_cost: float = 0, notes: str = ""):
        """
        Log revenue from AI service
        Automatically splits to treasury and reinvestment
        """
        revenue = {
            "timestamp": datetime.datetime.now().isoformat(),
            "amount": amount,
            "service": service,
            "customer": customer_name,
            "fulfillment_cost": fulfillment_cost,
            "net_revenue": amount - fulfillment_cost,
            "notes": notes
        }

        # Calculate splits
        net = amount - fulfillment_cost
        to_treasury = net * self.treasury_allocation
        to_reinvest = net * self.reinvest_allocation

        revenue["split"] = {
            "treasury": to_treasury,
            "reinvest": to_reinvest
        }

        # Log revenue
        revenues = json.loads(self.revenue_log.read_text())
        revenues.append(revenue)
        self.revenue_log.write_text(json.dumps(revenues, indent=2))

        # Auto-deploy to treasury
        self._deploy_to_treasury(to_treasury, f"Revenue from {service} - {customer_name}")

        # Auto-allocate to reinvestment pool
        self._allocate_reinvestment(to_reinvest, f"Reinvest from {service} - {customer_name}")

        # Update metrics
        self._update_metrics()

        return revenue

    def _deploy_to_treasury(self, amount: float, source: str):
        """Deploy capital to treasury"""
        deployment = {
            "timestamp": datetime.datetime.now().isoformat(),
            "amount": amount,
            "source": source,
            "strategy": "dynamic_allocation",
            "expected_apy": self.treasury_blended_apy,
            "status": "deployed"
        }

        treasury = json.loads(self.treasury_log.read_text())
        treasury.append(deployment)
        self.treasury_log.write_text(json.dumps(treasury, indent=2))

    def _allocate_reinvestment(self, amount: float, source: str):
        """Allocate to reinvestment pool (VAs, tools, ads)"""
        allocation = {
            "timestamp": datetime.datetime.now().isoformat(),
            "amount": amount,
            "source": source,
            "status": "available",
            "allocated_to": None
        }

        reinvest = json.loads(self.reinvest_log.read_text())
        reinvest.append(allocation)
        self.reinvest_log.write_text(json.dumps(reinvest, indent=2))

    def spend_reinvestment(self, amount: float, category: str, purpose: str):
        """
        Spend from reinvestment pool
        Categories: "vas", "tools", "ads", "infrastructure"
        """
        reinvest = json.loads(self.reinvest_log.read_text())

        # Calculate available
        total_in = sum(r["amount"] for r in reinvest if r["status"] == "available")
        total_spent = sum(r["amount"] for r in reinvest if r["status"] == "spent")
        available = total_in - total_spent

        if amount > available:
            raise ValueError(f"Insufficient reinvestment funds. Available: ${available:.2f}, Requested: ${amount:.2f}")

        spend = {
            "timestamp": datetime.datetime.now().isoformat(),
            "amount": -amount,  # Negative for spend
            "category": category,
            "purpose": purpose,
            "status": "spent"
        }

        reinvest.append(spend)
        self.reinvest_log.write_text(json.dumps(reinvest, indent=2))

        print(f"💳 Spent ${amount:.2f} on {category}: {purpose}")
        print(f"💰 Remaining reinvestment budget: ${available - amount:.2f}")

    def get_treasury_balance(self) -> Dict:
        """Calculate current treasury balance with projected yields"""
        treasury = json.loads(self.treasury_log.read_text())

        if not treasury:
            return {
                "principal": 0,
                "projected_annual_yield": 0,
                "projected_monthly_yield": 0
            }

        # Sum all deployments
        total_deployed = sum(t["amount"] for t in treasury)

        # Calculate projected yields
        annual_yield = total_deployed * self.treasury_blended_apy
        monthly_yield = annual_yield / 12

        return {
            "principal": total_deployed,
            "projected_annual_yield": annual_yield,
            "projected_monthly_yield": monthly_yield,
            "apy": self.treasury_blended_apy
        }

    def get_reinvestment_balance(self) -> Dict:
        """Calculate available reinvestment funds"""
        reinvest = json.loads(self.reinvest_log.read_text())

        total_allocated = sum(r["amount"] for r in reinvest if r["amount"] > 0)
        total_spent = sum(abs(r["amount"]) for r in reinvest if r["amount"] < 0)
        available = total_allocated - total_spent

        # Breakdown by category
        by_category = {}
        for r in reinvest:
            if r["amount"] < 0:  # Spend
                cat = r.get("category", "unknown")
                by_category[cat] = by_category.get(cat, 0) + abs(r["amount"])

        return {
            "total_allocated": total_allocated,
            "total_spent": total_spent,
            "available": available,
            "spending_by_category": by_category
        }

    def _update_metrics(self):
        """Update performance metrics"""
        revenues = json.loads(self.revenue_log.read_text())
        treasury = self.get_treasury_balance()
        reinvest = self.get_reinvestment_balance()

        # Calculate totals
        total_revenue = sum(r["amount"] for r in revenues)
        total_net_revenue = sum(r["net_revenue"] for r in revenues)
        total_customers = len(revenues)

        # Calculate by service
        by_service = {}
        for r in revenues:
            service = r["service"]
            if service not in by_service:
                by_service[service] = {
                    "count": 0,
                    "revenue": 0,
                    "net_revenue": 0
                }
            by_service[service]["count"] += 1
            by_service[service]["revenue"] += r["amount"]
            by_service[service]["net_revenue"] += r["net_revenue"]

        metrics = {
            "timestamp": datetime.datetime.now().isoformat(),
            "total_revenue": total_revenue,
            "total_net_revenue": total_net_revenue,
            "total_customers": total_customers,
            "avg_revenue_per_customer": total_revenue / max(total_customers, 1),
            "by_service": by_service,
            "treasury": treasury,
            "reinvestment": reinvest,
            "loop_health": self._calculate_loop_health()
        }

        # Save metrics
        metrics_history = json.loads(self.metrics_log.read_text())
        metrics_history.append(metrics)
        self.metrics_log.write_text(json.dumps(metrics_history, indent=2))

    def _calculate_loop_health(self) -> Dict:
        """
        Calculate health of the sacred loop

        Healthy loop:
        - Revenue growing month-over-month
        - Treasury growing steadily
        - Reinvestment being deployed effectively
        - Yields compounding
        """
        revenues = json.loads(self.revenue_log.read_text())
        treasury_balance = self.get_treasury_balance()
        reinvest_balance = self.get_reinvestment_balance()

        if not revenues:
            return {
                "status": "starting",
                "revenue_trend": "N/A",
                "treasury_utilization": 0,
                "reinvestment_utilization": 0
            }

        # Revenue trend (simple: last vs previous)
        if len(revenues) >= 2:
            recent = revenues[-1]["amount"]
            previous = revenues[-2]["amount"]
            revenue_growth = ((recent - previous) / previous) * 100 if previous > 0 else 0
        else:
            revenue_growth = 0

        # Reinvestment utilization
        reinvest_util = (reinvest_balance["total_spent"] / max(reinvest_balance["total_allocated"], 1)) * 100

        return {
            "status": "healthy" if revenue_growth > 0 else "needs_attention",
            "revenue_growth_pct": round(revenue_growth, 2),
            "treasury_balance": treasury_balance["principal"],
            "treasury_monthly_yield": treasury_balance["projected_monthly_yield"],
            "reinvestment_available": reinvest_balance["available"],
            "reinvestment_utilization_pct": round(reinvest_util, 2)
        }

    def project_growth(self, months: int = 12, customers_per_month: int = 10,
                       avg_revenue_per_customer: float = 3500) -> List[Dict]:
        """
        Project growth over N months

        Assumptions:
        - X customers per month
        - Avg revenue per customer
        - Treasury yields compound
        - Reinvestment enables more customers (velocity increase)
        """
        projections = []

        current_treasury = self.get_treasury_balance()["principal"]
        current_reinvest = self.get_reinvestment_balance()["available"]

        for month in range(1, months + 1):
            # Revenue this month
            monthly_revenue = customers_per_month * avg_revenue_per_customer
            monthly_net = monthly_revenue * 0.85  # Assume 15% fulfillment cost

            # Split revenue
            to_treasury = monthly_net * self.treasury_allocation
            to_reinvest = monthly_net * self.reinvest_allocation

            # Treasury compounds
            treasury_yield = current_treasury * (self.treasury_blended_apy / 12)

            # Update balances
            current_treasury += to_treasury + treasury_yield
            current_reinvest += to_reinvest

            # Velocity multiplier (more reinvestment = more VAs = more capacity)
            # Every $1000 in reinvest pool increases capacity by 5%
            velocity_multiplier = 1 + (current_reinvest / 1000) * 0.05

            # Next month capacity increases
            customers_per_month = int(customers_per_month * min(velocity_multiplier, 1.2))  # Cap at 20% monthly growth

            projection = {
                "month": month,
                "customers": customers_per_month,
                "monthly_revenue": monthly_revenue,
                "monthly_net": monthly_net,
                "treasury_balance": current_treasury,
                "treasury_monthly_yield": current_treasury * (self.treasury_blended_apy / 12),
                "reinvest_pool": current_reinvest,
                "total_capital": current_treasury + current_reinvest
            }

            projections.append(projection)

        return projections

    def show_dashboard(self):
        """Display the sacred loop dashboard"""
        print("\n" + "="*70)
        print("🔄 THE SACRED LOOP - Growth Engine Dashboard")
        print("="*70)

        # Current metrics
        treasury = self.get_treasury_balance()
        reinvest = self.get_reinvestment_balance()
        revenues = json.loads(self.revenue_log.read_text())

        print(f"\n💰 TREASURY")
        print(f"  Balance: ${treasury['principal']:,.2f}")
        print(f"  Projected monthly yield: ${treasury['projected_monthly_yield']:,.2f}")
        print(f"  APY: {treasury['apy']*100:.1f}%")

        print(f"\n🔄 REINVESTMENT POOL")
        print(f"  Available: ${reinvest['available']:,.2f}")
        print(f"  Total allocated: ${reinvest['total_allocated']:,.2f}")
        print(f"  Total spent: ${reinvest['total_spent']:,.2f}")

        if reinvest['spending_by_category']:
            print(f"\n  Spending breakdown:")
            for cat, amount in reinvest['spending_by_category'].items():
                print(f"    {cat}: ${amount:,.2f}")

        print(f"\n📊 REVENUE")
        if revenues:
            total_rev = sum(r["amount"] for r in revenues)
            print(f"  Total revenue: ${total_rev:,.2f}")
            print(f"  Customers: {len(revenues)}")
            print(f"  Avg per customer: ${total_rev/len(revenues):,.2f}")

            # Recent customers
            print(f"\n  Recent customers:")
            for r in revenues[-5:]:
                print(f"    {r['timestamp'][:10]} - {r['service']}: ${r['amount']:,.2f}")
        else:
            print(f"  No revenue yet - awaiting first customer!")

        # Loop health
        health = self._calculate_loop_health()
        print(f"\n🔥 LOOP HEALTH: {health['status'].upper()}")

        if health['status'] != 'starting':
            print(f"  Revenue growth: {health['revenue_growth_pct']:+.1f}%")
            print(f"  Treasury monthly yield: ${health['treasury_monthly_yield']:,.2f}")
            print(f"  Reinvestment utilization: {health['reinvestment_utilization_pct']:.1f}%")

        # 12-month projection
        print(f"\n📈 12-MONTH PROJECTION")
        projections = self.project_growth(months=12, customers_per_month=5, avg_revenue_per_customer=3500)

        print(f"\n  Month | Customers | Revenue    | Treasury    | Total Capital")
        print(f"  ------|-----------|------------|-------------|---------------")
        for p in [projections[0], projections[2], projections[5], projections[11]]:
            print(f"  {p['month']:5d} | {p['customers']:9d} | ${p['monthly_revenue']:9,.0f} | ${p['treasury_balance']:10,.0f} | ${p['total_capital']:12,.0f}")

        final = projections[-1]
        print(f"\n  🎯 Year-end projection:")
        print(f"    Total capital: ${final['total_capital']:,.2f}")
        print(f"    Treasury: ${final['treasury_balance']:,.2f}")
        print(f"    Monthly yield: ${final['treasury_monthly_yield']:,.2f}")
        print(f"    Customer velocity: {final['customers']} per month")

        print("\n" + "="*70)


def example_usage():
    """Example: Complete flow from first customer to scaling"""

    loop = SacredLoop()

    print("🚀 SACRED LOOP - Example Flow\n")

    # Week 1: First customer (church formation)
    print("WEEK 1: First customer!")
    loop.log_revenue(
        amount=2500,
        service="Church Formation - Basic",
        customer_name="John Smith",
        fulfillment_cost=100,  # 45 min at $100/hr = $75, plus $25 tools
        notes="First customer via LAUNCH TODAY campaign"
    )

    # Spend some reinvestment on VA
    print("\nDelegating setup tasks to VA...")
    loop.spend_reinvestment(
        amount=220,
        category="vas",
        purpose="Stripe + Facebook Ads + Google Ads setup for scaling"
    )

    # Week 2: Two more customers
    print("\nWEEK 2: Momentum building...")
    loop.log_revenue(
        amount=15000,
        service="Church Formation - Full Service",
        customer_name="Mary Johnson",
        fulfillment_cost=500,
        notes="High-ticket customer, full service with legal review"
    )

    loop.log_revenue(
        amount=2500,
        service="Church Formation - Basic",
        customer_name="Robert Davis",
        fulfillment_cost=75,
        notes="Second basic customer"
    )

    # Spend on ads
    print("\nScaling ads...")
    loop.spend_reinvestment(
        amount=500,
        category="ads",
        purpose="Facebook + Google Ads budget for Week 3"
    )

    # Week 3: Add new service
    print("\nWEEK 3: Launching Custom GPT service...")
    loop.log_revenue(
        amount=5000,
        service="Custom GPT",
        customer_name="Tech Startup Inc",
        fulfillment_cost=300,
        notes="Customer support GPT for SaaS company"
    )

    # Week 4: More customers
    print("\nWEEK 4: Scaling...")
    loop.log_revenue(2500, "Church Formation - Basic", "Sarah Wilson", 75)
    loop.log_revenue(5000, "Custom GPT", "Local Business LLC", 300)
    loop.log_revenue(2500, "Church Formation - Basic", "Mike Brown", 75)

    # Show dashboard
    print("\n" + "="*70)
    loop.show_dashboard()

    print("\n✅ THE SACRED LOOP IS RUNNING!")
    print("\nWhat's happening:")
    print("  • 60% of profits → Treasury (earning 25% APY)")
    print("  • 40% of profits → Reinvestment (VAs, ads, tools)")
    print("  • Treasury yields compound monthly")
    print("  • Reinvestment enables faster delivery")
    print("  • Faster delivery → more customers → more revenue")
    print("\n🔄 This is exponential growth in action.")


if __name__ == "__main__":
    example_usage()
