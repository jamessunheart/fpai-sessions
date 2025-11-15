#!/usr/bin/env python3
"""
TREASURY TRACKER - Unified Portfolio & Strategy Management

Tracks all positions, calculates P&L, monitors liquidation risks,
and manages treasury deployment strategies.
"""

import json
import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path


@dataclass
class SpotPosition:
    """Unleveraged spot holding"""
    asset: str
    amount: float
    entry_price: float
    current_price: float
    location: str  # "trust_wallet", "btrue", etc.

    @property
    def value_usd(self) -> float:
        return self.amount * self.current_price

    @property
    def pnl_usd(self) -> float:
        return self.amount * (self.current_price - self.entry_price)

    @property
    def pnl_percent(self) -> float:
        if self.entry_price == 0:
            return 0
        return ((self.current_price - self.entry_price) / self.entry_price) * 100


@dataclass
class LeveragedPosition:
    """Leveraged/margin position"""
    asset: str
    amount: float  # Total position size
    leverage: float  # 2x, 3x, etc.
    entry_price: float
    current_price: float
    liquidation_price: float
    margin_deployed: float  # Actual capital at risk
    exchange: str

    @property
    def position_value(self) -> float:
        return self.amount * self.current_price

    @property
    def borrowed_amount(self) -> float:
        return self.margin_deployed * (self.leverage - 1)

    @property
    def pnl_usd(self) -> float:
        # P&L is leveraged
        return self.amount * (self.current_price - self.entry_price)

    @property
    def pnl_percent(self) -> float:
        if self.entry_price == 0:
            return 0
        price_change_pct = ((self.current_price - self.entry_price) / self.entry_price) * 100
        return price_change_pct * self.leverage

    @property
    def distance_to_liquidation_usd(self) -> float:
        return self.current_price - self.liquidation_price

    @property
    def distance_to_liquidation_percent(self) -> float:
        if self.current_price == 0:
            return 0
        return ((self.current_price - self.liquidation_price) / self.current_price) * 100

    @property
    def liquidation_risk(self) -> str:
        pct = self.distance_to_liquidation_percent
        if pct > 30:
            return "LOW"
        elif pct > 15:
            return "MEDIUM"
        else:
            return "HIGH"


class TreasuryTracker:
    """
    Unified treasury management and tracking system
    """

    def __init__(self, data_file: str = "treasury_data.json"):
        self.data_file = Path(data_file)
        self.spot_positions: List[SpotPosition] = []
        self.leveraged_positions: List[LeveragedPosition] = []
        self.strategies: Dict = {}
        self.historical_snapshots: List = []

    def add_spot_position(self, **kwargs):
        """Add a spot position"""
        position = SpotPosition(**kwargs)
        self.spot_positions.append(position)
        return position

    def add_leveraged_position(self, **kwargs):
        """Add a leveraged position"""
        position = LeveragedPosition(**kwargs)
        self.leveraged_positions.append(position)
        return position

    def get_total_spot_value(self) -> float:
        """Total value of all spot positions"""
        return sum(p.value_usd for p in self.spot_positions)

    def get_total_margin_deployed(self) -> float:
        """Total margin/capital deployed in leveraged positions"""
        return sum(p.margin_deployed for p in self.leveraged_positions)

    def get_total_leveraged_value(self) -> float:
        """Total notional value of leveraged positions"""
        return sum(p.position_value for p in self.leveraged_positions)

    def get_total_pnl(self) -> float:
        """Total unrealized P&L across all positions"""
        spot_pnl = sum(p.pnl_usd for p in self.spot_positions)
        leveraged_pnl = sum(p.pnl_usd for p in self.leveraged_positions)
        return spot_pnl + leveraged_pnl

    def get_total_capital(self) -> float:
        """Total capital = spot value + margin deployed"""
        return self.get_total_spot_value() + self.get_total_margin_deployed()

    def get_summary(self) -> Dict:
        """Get portfolio summary"""
        total_capital = self.get_total_capital()
        total_pnl = self.get_total_pnl()

        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "spot": {
                "total_value": self.get_total_spot_value(),
                "positions": len(self.spot_positions),
                "pnl": sum(p.pnl_usd for p in self.spot_positions)
            },
            "leveraged": {
                "margin_deployed": self.get_total_margin_deployed(),
                "notional_value": self.get_total_leveraged_value(),
                "positions": len(self.leveraged_positions),
                "pnl": sum(p.pnl_usd for p in self.leveraged_positions)
            },
            "total": {
                "capital": total_capital,
                "pnl": total_pnl,
                "pnl_percent": (total_pnl / total_capital * 100) if total_capital > 0 else 0
            }
        }

    def get_liquidation_report(self) -> List[Dict]:
        """Get liquidation risk report for all leveraged positions"""
        return [{
            "asset": p.asset,
            "current_price": p.current_price,
            "liquidation_price": p.liquidation_price,
            "distance_usd": p.distance_to_liquidation_usd,
            "distance_percent": f"{p.distance_to_liquidation_percent:.2f}%",
            "risk_level": p.liquidation_risk,
            "margin_at_risk": p.margin_deployed
        } for p in self.leveraged_positions]

    def show_dashboard(self):
        """Print formatted dashboard"""
        summary = self.get_summary()

        print("\n" + "="*70)
        print("💰 TREASURY DASHBOARD")
        print("="*70)

        print(f"\n📊 TOTAL CAPITAL: ${summary['total']['capital']:,.2f}")
        print(f"📈 TOTAL P&L: ${summary['total']['pnl']:,.2f} ({summary['total']['pnl_percent']:.2f}%)")

        print(f"\n💎 SPOT POSITIONS ({summary['spot']['positions']}):")
        print(f"   Value: ${summary['spot']['total_value']:,.2f}")
        print(f"   P&L: ${summary['spot']['pnl']:,.2f}")

        for p in self.spot_positions:
            print(f"   └─ {p.amount:.4f} {p.asset} @ ${p.current_price:,.2f}")
            print(f"      Value: ${p.value_usd:,.2f} | P&L: ${p.pnl_usd:,.2f} ({p.pnl_percent:+.2f}%)")

        print(f"\n⚡ LEVERAGED POSITIONS ({summary['leveraged']['positions']}):")
        print(f"   Margin Deployed: ${summary['leveraged']['margin_deployed']:,.2f}")
        print(f"   Notional Value: ${summary['leveraged']['notional_value']:,.2f}")
        print(f"   P&L: ${summary['leveraged']['pnl']:,.2f}")

        for p in self.leveraged_positions:
            print(f"   └─ {p.amount:.4f} {p.asset} @ ${p.current_price:,.2f} ({p.leverage}x)")
            print(f"      Entry: ${p.entry_price:,.2f} | Liq: ${p.liquidation_price:,.2f}")
            print(f"      P&L: ${p.pnl_usd:,.2f} ({p.pnl_percent:+.2f}%) | Risk: {p.liquidation_risk}")
            print(f"      Distance to liq: ${p.distance_to_liquidation_usd:,.2f} ({p.distance_to_liquidation_percent:.2f}%)")

        print("\n" + "="*70)

    def save(self):
        """Save current state to JSON"""
        data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "spot_positions": [asdict(p) for p in self.spot_positions],
            "leveraged_positions": [asdict(p) for p in self.leveraged_positions],
            "summary": self.get_summary(),
            "liquidation_report": self.get_liquidation_report()
        }

        self.data_file.write_text(json.dumps(data, indent=2))
        print(f"\n💾 Treasury data saved to: {self.data_file}")

    def load(self):
        """Load state from JSON"""
        if self.data_file.exists():
            data = json.loads(self.data_file.read_text())

            self.spot_positions = [
                SpotPosition(**p) for p in data.get("spot_positions", [])
            ]
            self.leveraged_positions = [
                LeveragedPosition(**p) for p in data.get("leveraged_positions", [])
            ]

            print(f"\n📂 Treasury data loaded from: {self.data_file}")
            return data
        return None


if __name__ == "__main__":
    # Example: Initialize with current positions
    tracker = TreasuryTracker()

    # Add spot positions
    tracker.add_spot_position(
        asset="BTC",
        amount=1.0,
        entry_price=101825,  # User's actual entry
        current_price=96000,
        location="trust_wallet"
    )

    tracker.add_spot_position(
        asset="SOL",
        amount=373,
        entry_price=176,  # Entry from portfolio total
        current_price=148,
        location="trust_wallet"
    )

    tracker.add_spot_position(
        asset="HOT",
        amount=4134786,
        entry_price=0.003,
        current_price=0.003,
        location="trust_wallet"
    )

    tracker.add_spot_position(
        asset="USDT",
        amount=1000,
        entry_price=1,
        current_price=1,
        location="trust_wallet+btrue"
    )

    # Add leveraged positions
    tracker.add_leveraged_position(
        asset="BTC",
        amount=0.32,
        leverage=3.0,
        entry_price=107536,
        current_price=96000,
        liquidation_price=72559,
        margin_deployed=10000,
        exchange="btrue"
    )

    tracker.add_leveraged_position(
        asset="BTC",
        amount=2.54,
        leverage=2.0,
        entry_price=100300,
        current_price=96000,
        liquidation_price=67316,
        margin_deployed=63653,  # User confirmed BTC total margin = $73,653 ($10K + $63,653)
        exchange="btrue"
    )

    tracker.add_leveraged_position(
        asset="SOL",
        amount=1981,
        leverage=2.0,
        entry_price=148.08,
        current_price=148,
        liquidation_price=75.008,
        margin_deployed=135000,  # User confirmed SOL margin
        exchange="btrue"
    )

    # Show dashboard
    tracker.show_dashboard()

    # Save
    tracker.save()
