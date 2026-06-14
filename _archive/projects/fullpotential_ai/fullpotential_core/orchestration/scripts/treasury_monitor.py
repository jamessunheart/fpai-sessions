#!/usr/bin/env python3
"""
Treasury Monitor - Real-time tracking and alerts
Monitors your treasury for liquidation risk, yield tracking, and opportunities
"""

import json
import time
import requests
from datetime import datetime
from pathlib import Path

class TreasuryMonitor:
    """Monitor treasury positions and generate alerts"""

    def __init__(self):
        self.data_file = Path("treasury_data.json")
        self.report_file = Path("TREASURY_MONITOR_REPORT.md")
        self.alert_threshold = {
            "liquidation_distance_pct": 30.0,  # Alert if within 30% of liquidation
            "pnl_drop_pct": 10.0,  # Alert if P&L drops more than 10%
        }

    def load_treasury_data(self):
        """Load current treasury state"""
        if not self.data_file.exists():
            return None

        with open(self.data_file, 'r') as f:
            return json.load(f)

    def calculate_metrics(self, data):
        """Calculate key treasury metrics"""
        if not data:
            return None

        metrics = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_capital": data["summary"]["total"]["capital"],
            "total_pnl": data["summary"]["total"]["pnl"],
            "pnl_percent": data["summary"]["total"]["pnl_percent"],
            "margin_deployed": data["summary"]["leveraged"]["margin_deployed"],
            "liquidation_risks": [],
            "opportunities": [],
            "alerts": []
        }

        # Analyze liquidation risks
        for position in data.get("liquidation_report", []):
            risk = {
                "asset": position["asset"],
                "current_price": position["current_price"],
                "liquidation_price": position["liquidation_price"],
                "distance_pct": float(position["distance_percent"].strip('%')),
                "risk_level": position["risk_level"],
                "margin_at_risk": position["margin_at_risk"]
            }

            metrics["liquidation_risks"].append(risk)

            # Generate alert if high risk
            if risk["distance_pct"] < self.alert_threshold["liquidation_distance_pct"]:
                alert = {
                    "type": "LIQUIDATION_WARNING",
                    "severity": "HIGH",
                    "message": f"{risk['asset']} position is {risk['distance_pct']:.1f}% from liquidation",
                    "action": "Consider closing position or adding margin",
                    "margin_at_risk": f"${risk['margin_at_risk']:,.0f}"
                }
                metrics["alerts"].append(alert)

        # P&L alert
        if metrics["pnl_percent"] < -self.alert_threshold["pnl_drop_pct"]:
            alert = {
                "type": "PNL_DROP",
                "severity": "MEDIUM",
                "message": f"Portfolio down {metrics['pnl_percent']:.1f}%",
                "action": "Review strategy, consider de-risking",
                "pnl": f"${metrics['total_pnl']:,.0f}"
            }
            metrics["alerts"].append(alert)

        # Opportunity: Idle capital
        idle_capital = data["summary"]["spot"].get("total_value", 0)
        if idle_capital > 10000:
            opportunity = {
                "type": "IDLE_CAPITAL",
                "amount": idle_capital,
                "potential_yield": idle_capital * 0.065 / 12,  # 6.5% APY monthly
                "action": "Deploy to Aave USDC for 6.5% APY"
            }
            metrics["opportunities"].append(opportunity)

        return metrics

    def generate_report(self, metrics):
        """Generate markdown report"""
        if not metrics:
            return "No treasury data available"

        report = f"""# 📊 TREASURY MONITOR REPORT
**Generated:** {metrics['timestamp']}
**Auto-refresh:** Every 5 minutes

---

## 💰 TREASURY SUMMARY

**Total Capital:** ${metrics['total_capital']:,.2f}
**P&L:** ${metrics['total_pnl']:,.2f} ({metrics['pnl_percent']:.2f}%)
**Leveraged Margin:** ${metrics['margin_deployed']:,.0f}

---

## 🚨 ALERTS ({len(metrics['alerts'])})

"""

        if metrics['alerts']:
            for alert in metrics['alerts']:
                severity_emoji = {
                    "HIGH": "🔴",
                    "MEDIUM": "🟡",
                    "LOW": "🟢"
                }
                emoji = severity_emoji.get(alert['severity'], "⚪️")

                report += f"""
### {emoji} {alert['type']} ({alert['severity']} SEVERITY)

**Message:** {alert['message']}
**Action:** {alert['action']}
"""
                if 'margin_at_risk' in alert:
                    report += f"**Margin at Risk:** {alert['margin_at_risk']}\n"
                if 'pnl' in alert:
                    report += f"**Current P&L:** {alert['pnl']}\n"

                report += "\n"
        else:
            report += "✅ No alerts - Treasury is healthy\n\n"

        report += "---\n\n## ⚠️ LIQUIDATION RISKS\n\n"

        if metrics['liquidation_risks']:
            for risk in metrics['liquidation_risks']:
                risk_emoji = {
                    "HIGH": "🔴",
                    "MEDIUM": "🟡",
                    "LOW": "🟢"
                }
                emoji = risk_emoji.get(risk['risk_level'], "⚪️")

                report += f"""
### {emoji} {risk['asset']} - {risk['risk_level']} RISK

- **Current Price:** ${risk['current_price']:,.2f}
- **Liquidation Price:** ${risk['liquidation_price']:,.2f}
- **Distance:** {risk['distance_pct']:.1f}%
- **Margin at Risk:** ${risk['margin_at_risk']:,.0f}

"""
        else:
            report += "✅ No liquidation risks - No leveraged positions\n\n"

        report += "---\n\n## 💡 OPPORTUNITIES\n\n"

        if metrics['opportunities']:
            for opp in metrics['opportunities']:
                report += f"""
### {opp['type']}

- **Amount:** ${opp['amount']:,.2f}
- **Potential Monthly Yield:** ${opp['potential_yield']:,.2f}
- **Action:** {opp['action']}

"""
        else:
            report += "✅ All capital deployed efficiently\n\n"

        report += f"""---

## 📈 RECOMMENDATIONS

"""

        # Generate recommendations based on current state
        if metrics['alerts']:
            report += """
### 🔴 URGENT: Address High-Risk Positions

Your treasury has high-risk positions. Consider:

1. **Close leveraged positions** to eliminate liquidation risk
2. **Deploy to Aave USDC** for safe 6.5% APY
3. **Run:** `./treasury_rebalance.sh` for one-click safety deployment

**Benefit:** Eliminate risk + earn $1,600+/month passive income

"""
        elif metrics['margin_deployed'] > 0:
            report += """
### 🟡 MEDIUM: De-Risk Leveraged Positions

You have leveraged positions with moderate risk. Consider:

1. **Reduce leverage** to 1.5x or lower
2. **Set stop-losses** to protect capital
3. **Monitor liquidation distances** daily

**Alternative:** Close leverage, deploy to Aave for guaranteed yield

"""
        else:
            report += """
### 🟢 OPTIMAL: Treasury is Safe

Your treasury is in a safe state. Next steps:

1. **Monitor Aave yields** for optimization
2. **Track monthly income** in treasury_data.json
3. **Focus on revenue generation** (I MATCH, other services)

"""

        report += """
---

## 🔧 QUICK ACTIONS

**Check detailed status:**
```bash
cat TREASURY_SAFETY_DASHBOARD.md
```

**Execute safety rebalance:**
```bash
./treasury_rebalance.sh
```

**Update treasury data:**
```bash
# Manually update treasury_data.json with current positions
python3 treasury_monitor.py
```

---

🌐⚡💎 **Auto-generated by Treasury Monitor**
**Next update:** In 5 minutes
"""

        return report

    def save_report(self, report):
        """Save report to file"""
        with open(self.report_file, 'w') as f:
            f.write(report)
        print(f"✅ Report saved to {self.report_file}")

    def print_summary(self, metrics):
        """Print quick summary to terminal"""
        if not metrics:
            print("❌ No treasury data available")
            return

        print("\n" + "="*60)
        print("📊 TREASURY MONITOR - QUICK SUMMARY")
        print("="*60)
        print(f"\n💰 Capital: ${metrics['total_capital']:,.0f}")
        print(f"📈 P&L: ${metrics['total_pnl']:,.0f} ({metrics['pnl_percent']:.1f}%)")
        print(f"⚡ Leveraged: ${metrics['margin_deployed']:,.0f}")

        if metrics['alerts']:
            print(f"\n🚨 ALERTS: {len(metrics['alerts'])}")
            for alert in metrics['alerts']:
                print(f"   {alert['severity']}: {alert['message']}")
        else:
            print("\n✅ No alerts - Treasury healthy")

        if metrics['liquidation_risks']:
            print(f"\n⚠️  LIQUIDATION RISKS: {len(metrics['liquidation_risks'])}")
            for risk in metrics['liquidation_risks']:
                print(f"   {risk['asset']}: {risk['distance_pct']:.1f}% from liquidation ({risk['risk_level']} risk)")

        if metrics['opportunities']:
            print(f"\n💡 OPPORTUNITIES: {len(metrics['opportunities'])}")
            for opp in metrics['opportunities']:
                print(f"   {opp['type']}: ${opp['amount']:,.0f} → ${opp['potential_yield']:,.0f}/month")

        print("\n" + "="*60)
        print("📄 Full report: TREASURY_MONITOR_REPORT.md")
        print("="*60 + "\n")

    def monitor(self, interval=300, continuous=False):
        """
        Monitor treasury continuously

        Args:
            interval: Seconds between checks (default 300 = 5 minutes)
            continuous: If True, run forever. If False, run once.
        """
        while True:
            try:
                # Load current data
                data = self.load_treasury_data()

                # Calculate metrics
                metrics = self.calculate_metrics(data)

                # Generate report
                report = self.generate_report(metrics)
                self.save_report(report)

                # Print summary
                self.print_summary(metrics)

                if not continuous:
                    break

                # Wait for next check
                print(f"⏰ Next check in {interval} seconds...")
                time.sleep(interval)

            except KeyboardInterrupt:
                print("\n\n👋 Treasury monitor stopped")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                if not continuous:
                    break
                time.sleep(interval)

if __name__ == "__main__":
    import sys

    monitor = TreasuryMonitor()

    # Check if continuous mode requested
    continuous = "--watch" in sys.argv or "-w" in sys.argv

    if continuous:
        print("🔄 Starting continuous treasury monitoring...")
        print("   Press Ctrl+C to stop\n")
        monitor.monitor(interval=300, continuous=True)
    else:
        print("📊 Running one-time treasury check...\n")
        monitor.monitor(interval=300, continuous=False)
        print("\n💡 TIP: Run with --watch to monitor continuously")
