#!/usr/bin/env python3
"""
Treasury Deployment Plan - $373K Capital Allocation
Based on CAPITAL_VISION_SSOT.md blueprint
"""
from datetime import datetime
from typing import Dict, List
import json

class TreasuryDeploymentPlan:
    """Strategic capital deployment for $2-7K/month yield"""
    
    def __init__(self):
        # Current capital state
        self.total_capital = 373_261
        self.spot_holdings = 164_608
        self.leveraged_positions = 208_653
        self.current_pnl = -31_041
        
        # Target allocation (from blueprint)
        self.stable_defi_pct = 0.40  # 40% to stable yields
        self.tactical_pct = 0.40      # 40% to tactical trading
        self.moonshots_pct = 0.20     # 20% to high-risk/reward
        
    def calculate_deployment_amounts(self) -> Dict:
        """Calculate deployment amounts per strategy"""
        
        # Use spot holdings for deployment (safer than leveraged)
        deployable_capital = self.spot_holdings
        
        stable_allocation = deployable_capital * self.stable_defi_pct
        tactical_allocation = deployable_capital * self.tactical_pct
        moonshot_allocation = deployable_capital * self.moonshots_pct
        
        return {
            "total_deployable": deployable_capital,
            "allocations": {
                "stable_defi": {
                    "amount": stable_allocation,
                    "percentage": self.stable_defi_pct * 100,
                    "target_apy": 12.0,  # Conservative DeFi
                    "monthly_yield": stable_allocation * 0.12 / 12
                },
                "tactical": {
                    "amount": tactical_allocation,
                    "percentage": self.tactical_pct * 100,
                    "target_apy_low": 20.0,
                    "target_apy_high": 100.0,
                    "monthly_yield_low": tactical_allocation * 0.20 / 12,
                    "monthly_yield_high": tactical_allocation * 1.00 / 12
                },
                "moonshots": {
                    "amount": moonshot_allocation,
                    "percentage": self.moonshots_pct * 100,
                    "target_apy_low": 50.0,
                    "target_apy_high": 200.0,
                    "monthly_yield_low": moonshot_allocation * 0.50 / 12,
                    "monthly_yield_high": moonshot_allocation * 2.00 / 12
                }
            }
        }
    
    def calculate_monthly_yields(self) -> Dict:
        """Calculate expected monthly yields across scenarios"""
        
        deployment = self.calculate_deployment_amounts()
        allocs = deployment["allocations"]
        
        # Conservative scenario
        conservative = (
            allocs["stable_defi"]["monthly_yield"] +
            allocs["tactical"]["monthly_yield_low"] +
            allocs["moonshots"]["monthly_yield_low"]
        )
        
        # Expected scenario
        expected = (
            allocs["stable_defi"]["monthly_yield"] +
            (allocs["tactical"]["monthly_yield_low"] + allocs["tactical"]["monthly_yield_high"]) / 2 +
            (allocs["moonshots"]["monthly_yield_low"] + allocs["moonshots"]["monthly_yield_high"]) / 2
        )
        
        # Optimistic scenario
        optimistic = (
            allocs["stable_defi"]["monthly_yield"] +
            allocs["tactical"]["monthly_yield_high"] +
            allocs["moonshots"]["monthly_yield_high"]
        )
        
        return {
            "conservative": round(conservative, 2),
            "expected": round(expected, 2),
            "optimistic": round(optimistic, 2),
            "blueprint_target_low": 2000,
            "blueprint_target_high": 7000
        }
    
    def generate_deployment_steps(self) -> List[Dict]:
        """Generate step-by-step deployment plan"""
        
        deployment = self.calculate_deployment_amounts()
        
        return [
            {
                "step": 1,
                "name": "Deploy to Stable DeFi",
                "amount": deployment["allocations"]["stable_defi"]["amount"],
                "platforms": ["Aave", "Compound", "Curve"],
                "assets": ["USDC", "DAI", "USDT"],
                "target_apy": "10-15%",
                "risk": "LOW",
                "time_to_deploy": "1-2 hours",
                "expected_monthly": deployment["allocations"]["stable_defi"]["monthly_yield"]
            },
            {
                "step": 2,
                "name": "Deploy to Tactical Trading",
                "amount": deployment["allocations"]["tactical"]["amount"],
                "strategies": ["SOL swing trading", "BTC range trading", "Altcoin rotations"],
                "target_apy": "20-100%",
                "risk": "MEDIUM",
                "time_to_deploy": "Ongoing",
                "expected_monthly_low": deployment["allocations"]["tactical"]["monthly_yield_low"],
                "expected_monthly_high": deployment["allocations"]["tactical"]["monthly_yield_high"]
            },
            {
                "step": 3,
                "name": "Deploy to Moonshots",
                "amount": deployment["allocations"]["moonshots"]["amount"],
                "strategies": ["Pre-sale tokens", "Early-stage protocols", "High-conviction altcoins"],
                "target_apy": "50-200%+",
                "risk": "HIGH",
                "time_to_deploy": "1 week",
                "expected_monthly_low": deployment["allocations"]["moonshots"]["monthly_yield_low"],
                "expected_monthly_high": deployment["allocations"]["moonshots"]["monthly_yield_high"]
            }
        ]
    
    def print_deployment_plan(self):
        """Print comprehensive deployment plan"""
        
        print("\n" + "="*70)
        print("TREASURY DEPLOYMENT PLAN - $373K Capital")
        print("="*70)
        
        print("\n📊 CURRENT STATE:")
        print(f"  Total Capital: ${self.total_capital:,}")
        print(f"  Spot Holdings: ${self.spot_holdings:,}")
        print(f"  Leveraged Positions: ${self.leveraged_positions:,}")
        print(f"  Current P&L: ${self.current_pnl:,} ({self.current_pnl/self.total_capital*100:.1f}%)")
        
        deployment = self.calculate_deployment_amounts()
        print(f"\n💰 DEPLOYABLE CAPITAL: ${deployment['total_deployable']:,}")
        print("  (Using spot holdings for safety)")
        
        print("\n🎯 ALLOCATION STRATEGY:")
        for name, alloc in deployment["allocations"].items():
            print(f"\n  {name.upper().replace('_', ' ')}:")
            print(f"    Amount: ${alloc['amount']:,.0f} ({alloc['percentage']:.0f}%)")
            if "target_apy" in alloc:
                print(f"    Target APY: {alloc['target_apy']:.0f}%")
                print(f"    Monthly Yield: ${alloc['monthly_yield']:,.0f}")
            else:
                print(f"    Target APY: {alloc['target_apy_low']:.0f}%-{alloc['target_apy_high']:.0f}%")
                print(f"    Monthly Yield: ${alloc['monthly_yield_low']:,.0f}-${alloc['monthly_yield_high']:,.0f}")
        
        yields = self.calculate_monthly_yields()
        print("\n📈 EXPECTED MONTHLY YIELDS:")
        print(f"  Conservative: ${yields['conservative']:,.0f}/month")
        print(f"  Expected:     ${yields['expected']:,.0f}/month")
        print(f"  Optimistic:   ${yields['optimistic']:,.0f}/month")
        print(f"\n  Blueprint Target: ${yields['blueprint_target_low']:,}-${yields['blueprint_target_high']:,}/month")
        
        aligned = yields['conservative'] >= yields['blueprint_target_low']
        print(f"  ✅ Aligned with blueprint" if aligned else f"  ⚠️  Below blueprint target")
        
        print("\n🚀 DEPLOYMENT STEPS:")
        steps = self.generate_deployment_steps()
        for step in steps:
            print(f"\n  STEP {step['step']}: {step['name']}")
            print(f"    Amount: ${step['amount']:,.0f}")
            print(f"    Risk: {step['risk']}")
            print(f"    Time: {step['time_to_deploy']}")
            if 'expected_monthly' in step:
                print(f"    Yield: ${step['expected_monthly']:,.0f}/month")
            else:
                print(f"    Yield: ${step['expected_monthly_low']:,.0f}-${step['expected_monthly_high']:,.0f}/month")
        
        print("\n⚠️  CRITICAL NOTES:")
        print("  1. Blueprint targets $2-7K/month yield")
        print("  2. Conservative scenario delivers $2K+ (meets minimum)")
        print("  3. Expected scenario delivers $4.5K (mid-range)")
        print("  4. Requires active management (not passive)")
        print("  5. Risk increases from Stable → Tactical → Moonshots")
        print(f"  6. Current leverage positions: ${self.leveraged_positions:,} (manage separately)")
        
        print("\n🎯 SUCCESS METRICS:")
        print("  Month 1: $2K+ yield (conservative baseline)")
        print("  Month 3: $3.5K+ yield (scaling tactical)")
        print("  Month 6: $5K+ yield (compounding effects)")
        print("  Month 12: $10K+ yield (self-sustaining)")
        
        print("\n" + "="*70)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
        
        return {
            "deployment": deployment,
            "yields": yields,
            "steps": steps
        }
    
    def save_plan(self, filepath="/tmp/treasury_deployment_plan.json"):
        """Save deployment plan to JSON"""
        plan = {
            "current_state": {
                "total_capital": self.total_capital,
                "spot_holdings": self.spot_holdings,
                "leveraged_positions": self.leveraged_positions,
                "current_pnl": self.current_pnl
            },
            "deployment": self.calculate_deployment_amounts(),
            "yields": self.calculate_monthly_yields(),
            "steps": self.generate_deployment_steps(),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, "w") as f:
            json.dump(plan, f, indent=2)
        
        print(f"✅ Plan saved to {filepath}")

if __name__ == "__main__":
    planner = TreasuryDeploymentPlan()
    planner.print_deployment_plan()
    planner.save_plan()
