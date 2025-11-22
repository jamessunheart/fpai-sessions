#!/usr/bin/env python3
"""
WHITE ROCK MINISTRY - Sacred Loop for PMA Membership Model

Revenue Sources:
1. Membership fees ($2,500-$15,000 one-time)
2. Performance fees (20% of treasury optimization gains)
3. Management fees (2% AUM annually)
4. Transaction fees (internal token movements)

Member Benefits:
- Trust setup guidance + AI compliance
- Wallet connection to treasury backend
- Treasury optimization via your infrastructure
- Internal token for inter-trust resource movement
- Ongoing support within PMA

This is NOT "church formation service" - it's a membership organization
providing financial tools and optimization within a private association.
"""

import json
import datetime
from pathlib import Path
from typing import Dict, List
from decimal import Decimal


class WhiteRockMinistry:
    """
    White Rock Ministry PMA - Membership and Treasury Management

    Structure:
    - White Rock Ministry = 508(c)(1)(A) organization (you)
    - Members = Join via Private Membership Agreement
    - Services = Trust guidance, AI tools, treasury optimization
    - Token = Internal utility for inter-trust transfers
    - Revenue = Membership + Performance + Management + Transaction fees
    """

    def __init__(self, data_path="/root/delegation-system/white-rock"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)

        # Data files
        self.members_log = self.data_path / "members.json"
        self.revenue_log = self.data_path / "revenue.json"
        self.aum_log = self.data_path / "assets_under_management.json"
        self.token_txs_log = self.data_path / "token_transactions.json"
        self.treasury_log = self.data_path / "ministry_treasury.json"

        # Initialize
        for log_file in [self.members_log, self.revenue_log, self.aum_log,
                         self.token_txs_log, self.treasury_log]:
            if not log_file.exists():
                log_file.write_text(json.dumps([], indent=2))

        # Fee structure
        self.membership_tiers = {
            "basic": {
                "price": 2500,
                "includes": [
                    "Trust setup guidance",
                    "AI compliance tools",
                    "Wallet connection",
                    "Community access"
                ]
            },
            "premium": {
                "price": 7500,
                "includes": [
                    "Everything in Basic",
                    "1-on-1 consultation",
                    "Priority support",
                    "Advanced optimization strategies"
                ]
            },
            "platinum": {
                "price": 15000,
                "includes": [
                    "Everything in Premium",
                    "Custom trust structures",
                    "Dedicated account manager",
                    "White-glove service"
                ]
            }
        }

        # Management fees
        self.management_fee_pct = 0.02  # 2% annually on AUM
        self.performance_fee_pct = 0.20  # 20% of gains above benchmark

        # Capital allocation (from Sacred Loop)
        self.ministry_treasury_allocation = 0.40  # 40% to ministry treasury
        self.member_optimization_allocation = 0.60  # 60% to member optimization

    def add_member(self, name: str, email: str, tier: str,
                   initial_assets: float = 0, notes: str = ""):
        """
        Add new member to White Rock Ministry PMA

        Args:
            name: Member name
            email: Contact email
            tier: Membership tier (basic/premium/platinum)
            initial_assets: Assets member is bringing for optimization
            notes: Additional notes
        """
        if tier not in self.membership_tiers:
            raise ValueError(f"Invalid tier. Must be: {list(self.membership_tiers.keys())}")

        member = {
            "id": f"WRM_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "joined_at": datetime.datetime.now().isoformat(),
            "name": name,
            "email": email,
            "tier": tier,
            "membership_fee_paid": self.membership_tiers[tier]["price"],
            "initial_assets": initial_assets,
            "status": "active",
            "notes": notes
        }

        # Log member
        members = json.loads(self.members_log.read_text())
        members.append(member)
        self.members_log.write_text(json.dumps(members, indent=2))

        # Log membership revenue
        self._log_revenue(
            amount=member["membership_fee_paid"],
            source="membership",
            member_id=member["id"],
            tier=tier,
            description=f"{tier.title()} membership - {name}"
        )

        # Add to AUM if they're bringing assets
        if initial_assets > 0:
            self._add_to_aum(member["id"], initial_assets, "Initial member assets")

        print(f"✅ Member added: {name}")
        print(f"   Tier: {tier.title()}")
        print(f"   Membership fee: ${member['membership_fee_paid']:,}")
        if initial_assets > 0:
            print(f"   Initial AUM: ${initial_assets:,}")

        return member

    def _log_revenue(self, amount: float, source: str, member_id: str = None,
                     tier: str = None, description: str = ""):
        """Log revenue from any source"""
        revenue = {
            "timestamp": datetime.datetime.now().isoformat(),
            "amount": amount,
            "source": source,  # membership, management_fee, performance_fee, transaction_fee
            "member_id": member_id,
            "tier": tier,
            "description": description
        }

        revenues = json.loads(self.revenue_log.read_text())
        revenues.append(revenue)
        self.revenue_log.write_text(json.dumps(revenues, indent=2))

        # Allocate revenue
        self._allocate_revenue(amount, source)

    def _allocate_revenue(self, amount: float, source: str):
        """
        Allocate revenue between ministry treasury and member optimization

        Different sources get different allocations:
        - Membership fees: 40% ministry, 60% member optimization infrastructure
        - Management fees: 50% ministry, 50% member optimization
        - Performance fees: 40% ministry, 60% reinvest in member gains
        """
        if source == "membership":
            to_ministry = amount * 0.40
            to_optimization = amount * 0.60
        elif source == "management_fee":
            to_ministry = amount * 0.50
            to_optimization = amount * 0.50
        elif source == "performance_fee":
            to_ministry = amount * 0.40
            to_optimization = amount * 0.60
        else:
            to_ministry = amount * 0.40
            to_optimization = amount * 0.60

        # Deploy to ministry treasury
        treasury = json.loads(self.treasury_log.read_text())
        treasury.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "amount": to_ministry,
            "source": source,
            "allocation": "ministry_treasury"
        })
        self.treasury_log.write_text(json.dumps(treasury, indent=2))

        # Note optimization allocation (this funds the backend infrastructure)
        treasury.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "amount": to_optimization,
            "source": source,
            "allocation": "member_optimization"
        })
        self.treasury_log.write_text(json.dumps(treasury, indent=2))

    def _add_to_aum(self, member_id: str, amount: float, description: str):
        """Add assets under management"""
        aum = json.loads(self.aum_log.read_text())
        aum.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "member_id": member_id,
            "amount": amount,
            "description": description,
            "type": "deposit"
        })
        self.aum_log.write_text(json.dumps(aum, indent=2))

    def calculate_monthly_fees(self):
        """
        Calculate monthly management fees on AUM

        2% annual = 0.167% monthly
        """
        aum = json.loads(self.aum_log.read_text())

        # Calculate total AUM
        total_aum = sum(a["amount"] for a in aum if a["type"] == "deposit")
        total_aum -= sum(abs(a["amount"]) for a in aum if a["type"] == "withdrawal")

        if total_aum <= 0:
            return 0

        # Monthly management fee
        monthly_fee = total_aum * (self.management_fee_pct / 12)

        # Log fee
        self._log_revenue(
            amount=monthly_fee,
            source="management_fee",
            description=f"Monthly management fee on ${total_aum:,.2f} AUM"
        )

        return monthly_fee

    def log_performance_fee(self, member_id: str, gains: float, benchmark_gains: float = 0):
        """
        Log performance fee (20% of gains above benchmark)

        Args:
            member_id: Member ID
            gains: Actual gains from optimization
            benchmark_gains: Benchmark comparison (e.g., S&P 500)
        """
        excess_gains = max(0, gains - benchmark_gains)
        performance_fee = excess_gains * self.performance_fee_pct

        if performance_fee > 0:
            self._log_revenue(
                amount=performance_fee,
                source="performance_fee",
                member_id=member_id,
                description=f"20% performance fee on ${excess_gains:,.2f} excess gains"
            )

        return performance_fee

    def log_token_transaction(self, from_member: str, to_member: str,
                              amount: float, purpose: str, fee: float = 0):
        """
        Log internal token transaction between member trusts

        Args:
            from_member: Sending member ID
            to_member: Receiving member ID
            amount: Token amount
            purpose: Transaction purpose
            fee: Transaction fee
        """
        tx = {
            "timestamp": datetime.datetime.now().isoformat(),
            "from": from_member,
            "to": to_member,
            "amount": amount,
            "purpose": purpose,
            "fee": fee
        }

        txs = json.loads(self.token_txs_log.read_text())
        txs.append(tx)
        self.token_txs_log.write_text(json.dumps(txs, indent=2))

        # Log transaction fee as revenue
        if fee > 0:
            self._log_revenue(
                amount=fee,
                source="transaction_fee",
                description=f"Token transfer fee - {purpose}"
            )

    def get_dashboard_metrics(self) -> Dict:
        """Get key metrics for dashboard"""
        members = json.loads(self.members_log.read_text())
        revenues = json.loads(self.revenue_log.read_text())
        aum = json.loads(self.aum_log.read_text())
        treasury = json.loads(self.treasury_log.read_text())

        # Total members
        active_members = [m for m in members if m["status"] == "active"]
        total_members = len(active_members)

        # Members by tier
        by_tier = {}
        for m in active_members:
            tier = m["tier"]
            by_tier[tier] = by_tier.get(tier, 0) + 1

        # Total revenue
        total_revenue = sum(r["amount"] for r in revenues)

        # Revenue by source
        by_source = {}
        for r in revenues:
            source = r["source"]
            by_source[source] = by_source.get(source, 0) + r["amount"]

        # Total AUM
        total_aum = sum(a["amount"] for a in aum if a["type"] == "deposit")
        total_aum -= sum(abs(a["amount"]) for a in aum if a.get("type") == "withdrawal")

        # Ministry treasury
        ministry_balance = sum(t["amount"] for t in treasury if t["allocation"] == "ministry_treasury")

        # Optimization pool
        optimization_balance = sum(t["amount"] for t in treasury if t["allocation"] == "member_optimization")

        return {
            "members": {
                "total": total_members,
                "by_tier": by_tier
            },
            "revenue": {
                "total": total_revenue,
                "by_source": by_source
            },
            "aum": total_aum,
            "treasury": {
                "ministry": ministry_balance,
                "optimization": optimization_balance,
                "total": ministry_balance + optimization_balance
            }
        }

    def show_dashboard(self):
        """Display White Rock Ministry dashboard"""
        print("\n" + "="*70)
        print("🙏 WHITE ROCK MINISTRY - Dashboard")
        print("="*70)

        metrics = self.get_dashboard_metrics()

        print(f"\n👥 MEMBERS")
        print(f"  Total active: {metrics['members']['total']}")
        for tier, count in metrics['members']['by_tier'].items():
            print(f"    {tier.title()}: {count}")

        print(f"\n💰 REVENUE")
        print(f"  Total: ${metrics['revenue']['total']:,.2f}")
        for source, amount in metrics['revenue']['by_source'].items():
            print(f"    {source.replace('_', ' ').title()}: ${amount:,.2f}")

        print(f"\n📊 ASSETS UNDER MANAGEMENT")
        print(f"  Total AUM: ${metrics['aum']:,.2f}")

        print(f"\n🏛️ MINISTRY TREASURY")
        print(f"  Ministry reserves: ${metrics['treasury']['ministry']:,.2f}")
        print(f"  Optimization pool: ${metrics['treasury']['optimization']:,.2f}")
        print(f"  Total capital: ${metrics['treasury']['total']:,.2f}")

        # Projections
        print(f"\n📈 MONTHLY PROJECTIONS")
        monthly_mgmt_fee = metrics['aum'] * (0.02 / 12) if metrics['aum'] > 0 else 0
        print(f"  Management fees: ${monthly_mgmt_fee:,.2f}/month (2% AUM)")
        print(f"  At current AUM: ${metrics['aum']:,.2f}")

        print("\n" + "="*70)


def example_usage():
    """Example: White Rock Ministry onboarding members"""

    ministry = WhiteRockMinistry()

    print("🙏 WHITE ROCK MINISTRY - Example Member Onboarding\n")

    # Member 1: Basic tier
    print("MEMBER 1: Basic Tier")
    ministry.add_member(
        name="John Smith",
        email="john@example.com",
        tier="basic",
        initial_assets=50000,
        notes="Interested in trust optimization"
    )

    # Member 2: Premium tier
    print("\nMEMBER 2: Premium Tier")
    ministry.add_member(
        name="Sarah Johnson",
        email="sarah@example.com",
        tier="premium",
        initial_assets=250000,
        notes="Wants 1-on-1 consultation"
    )

    # Member 3: Platinum tier
    print("\nMEMBER 3: Platinum Tier")
    ministry.add_member(
        name="Robert Davis",
        email="robert@example.com",
        tier="platinum",
        initial_assets=1000000,
        notes="High net worth, custom structures"
    )

    # Calculate monthly fees
    print("\n" + "="*70)
    print("MONTH 1 - Calculate Management Fees")
    monthly_fee = ministry.calculate_monthly_fees()
    print(f"✅ Monthly management fee: ${monthly_fee:,.2f}")

    # Log performance fee (example: 15% gains on $1M)
    print("\nQUARTER 1 - Performance Fees")
    gains = 150000  # 15% on $1M
    benchmark = 50000  # S&P 500 did 5%
    perf_fee = ministry.log_performance_fee("member_3", gains, benchmark)
    print(f"✅ Performance fee: ${perf_fee:,.2f}")
    print(f"   (20% of ${gains - benchmark:,.2f} excess gains)")

    # Token transaction
    print("\nINTERNAL TOKEN TRANSACTION")
    ministry.log_token_transaction(
        from_member="member_1",
        to_member="member_2",
        amount=5000,
        purpose="Trust-to-trust asset transfer",
        fee=25  # 0.5% transaction fee
    )
    print("✅ Token transaction logged (inter-trust transfer)")

    # Show dashboard
    ministry.show_dashboard()

    print("\n✅ WHITE ROCK MINISTRY MODEL READY!")
    print("\nRevenue Sources:")
    print("  • Membership fees (one-time)")
    print("  • Management fees (2% AUM annually)")
    print("  • Performance fees (20% of excess gains)")
    print("  • Transaction fees (internal token movements)")
    print("\nLegal Structure:")
    print("  • White Rock Ministry = 508(c)(1)(A)")
    print("  • Members = Private Membership Agreement (PMA)")
    print("  • Services = Trust guidance, AI tools, optimization")
    print("  • Token = Internal utility (not a security)")


if __name__ == "__main__":
    example_usage()
