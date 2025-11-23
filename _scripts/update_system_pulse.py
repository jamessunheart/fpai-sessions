#!/usr/bin/env python3
"""
System Pulse Aggregator
Synthesizes state from Revenue (Storefront), Labor (Missions), and Infra into a single heartbeat.
Writes to core/STATE/PULSE.json and DASHBOARD.md.
"""
import json
import os
import glob
from datetime import datetime
from pathlib import Path

# --- Configuration ---
ROOT_DIR = Path(__file__).parent.parent.absolute()
ORDERS_DB = ROOT_DIR / "opt/fpai/core/applications/website-com/data/orders.json"  # Path on server
MISSIONS_DIR = ROOT_DIR / "missions"
STATE_DIR = ROOT_DIR / "core/STATE"
PULSE_FILE = STATE_DIR / "PULSE.json"
TREASURY_FILE = STATE_DIR / "TREASURY.json"
DASHBOARD_FILE = ROOT_DIR / "DASHBOARD.md"

# Fallback for local testing if server path doesn't exist
if not ORDERS_DB.exists():
    ORDERS_DB = ROOT_DIR / "var/orders.json" # Fallback/Local

def get_revenue_stats():
    """Reads orders.json to calculate revenue metrics."""
    stats = {
        "total_revenue": 0.0,
        "order_count": 0,
        "last_order_at": None,
        "products_sold": {}
    }
    
    if not ORDERS_DB.exists():
        return stats

    try:
        with open(ORDERS_DB, 'r') as f:
            orders = json.load(f)
            
        paid_orders = [o for o in orders if o.get('status') in ['paid', 'delivered']]
        
        stats["order_count"] = len(paid_orders)
        # Assuming standardized pricing for now, or looking up price from product_id if complex.
        # For v1 accelerator, it's $97. Future: look up price map.
        stats["total_revenue"] = sum(97.0 for _ in paid_orders) 
        
        if paid_orders:
            stats["last_order_at"] = max(o.get('paidAt', '') for o in paid_orders)
            
        for o in paid_orders:
            pid = o.get('productId', 'unknown')
            stats["products_sold"][pid] = stats["products_sold"].get(pid, 0) + 1
            
    except Exception as e:
        print(f"Error reading revenue stats: {e}")
        
    return stats

def get_treasury_stats():
    """Reads TREASURY.json for financial health."""
    if not TREASURY_FILE.exists():
        return {"runway_months": 0, "total_liquidity": 0, "status": "Unknown"}
    
    try:
        with open(TREASURY_FILE, 'r') as f:
            data = json.load(f)
            return data.get("health", {"runway_months": 0, "total_liquidity": 0, "status": "Unknown"})
    except Exception as e:
        print(f"Error reading treasury stats: {e}")
        return {"runway_months": 0, "total_liquidity": 0, "status": "Error"}

def get_mission_stats():
    """Scans markdown files in missions/ to gauge labor velocity."""
    stats = {
        "open": 0,
        "in_progress": 0,
        "completed": 0,
        "total": 0,
        "high_security_pending": 0
    }
    
    if not MISSIONS_DIR.exists():
        return stats

    for filepath in MISSIONS_DIR.glob("*.md"):
        stats["total"] += 1
        try:
            content = filepath.read_text(encoding='utf-8')
            lower_content = content.lower()
            
            # Simple heuristic parsing
            if "status: completed" in lower_content or "status: done" in lower_content:
                stats["completed"] += 1
            elif "status: in progress" in lower_content or "status: claimed" in lower_content:
                stats["in_progress"] += 1
            else:
                stats["open"] += 1
                
            if "security level: 🔴 high" in lower_content and "status: completed" not in lower_content:
                stats["high_security_pending"] += 1
                
        except Exception as e:
            print(f"Error reading mission {filepath}: {e}")
            
    return stats

def update_dashboard(pulse):
    """Updates the human-readable DASHBOARD.md."""
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    dashboard_content = f"""# 🧠 FPAI SYSTEM DASHBOARD
**Last Updated:** {now_str}

## 📊 Vital Signs
| Metric | Value | Status |
| :--- | :--- | :--- |
| **Revenue** | `${pulse['revenue']['total_revenue']:.2f}` | {'🟢 Flowing' if pulse['revenue']['order_count'] > 0 else '⚪ Waiting'} |
| **Liquidity** | `${pulse['treasury']['total_liquidity']:.2f}` | {pulse['treasury']['status']} |
| **Runway** | `{pulse['treasury']['runway_months']} mo` | - |
| **Orders** | `{pulse['revenue']['order_count']}` | - |
| **Missions Open** | `{pulse['missions']['open']}` | {'🟡 Action Needed' if pulse['missions']['open'] > 5 else '🟢 Healthy'} |
| **Mission Velocity** | `{pulse['missions']['completed']} Completed` | - |

## 🚨 High Priority Actions
"""

    if pulse['missions']['high_security_pending'] > 0:
        dashboard_content += f"- 🔴 **{pulse['missions']['high_security_pending']} High Security Missions Pending** (Requires Architect Review)\n"
    
    if pulse['revenue']['order_count'] == 0:
        dashboard_content += "- 🟡 **Revenue System Idle**: Verify Storefront Traffic\n"
        
    if pulse['treasury']['runway_months'] < 3:
        dashboard_content += f"- 🔴 **Low Runway ({pulse['treasury']['runway_months']} mo)**: Focus on Revenue Immediate\n"

    dashboard_content += """
## 🛠 Active Systems
- **Storefront:** Active (fullpotential.com)
- **Mission Control:** Active (Internal)
- **Pulse:** Active (Heartbeat Monitor)
- **Treasury:** Active (Runway Tracking)

---
*Auto-generated by System Pulse*
"""
    
    with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
        f.write(dashboard_content)

def main():
    print("🩺 Measuring System Pulse...")
    
    pulse = {
        "timestamp": datetime.now().isoformat(),
        "revenue": get_revenue_stats(),
        "treasury": get_treasury_stats(),
        "missions": get_mission_stats(),
        "status": "nominal" # Default, logic can update this
    }
    
    # Ensure STATE dir exists
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write Machine State
    with open(PULSE_FILE, 'w', encoding='utf-8') as f:
        json.dump(pulse, f, indent=2)
        
    # Write Human State
    update_dashboard(pulse)
    
    print(f"✅ Pulse Updated. Revenue: ${pulse['revenue']['total_revenue']} | Runway: {pulse['treasury']['runway_months']} mo")

if __name__ == "__main__":
    main()
