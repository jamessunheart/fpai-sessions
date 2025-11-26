#!/usr/bin/env python3
import requests
import json
import os
from pathlib import Path

# --- Config ---
ROOT_DIR = Path("/opt/fpai")
STATE_DIR = ROOT_DIR / "core/STATE"
ASSEMBLY_FILE_MD = STATE_DIR / "ASSEMBLY_LINE.md"
ASSEMBLY_FILE_JSON = STATE_DIR / "ASSEMBLY.json"

STOREFRONT_URL = "https://fullpotential.com/accelerator-kit"
CHECKOUT_API = "http://127.0.0.1:3001/api/health"
ENV_FILE = "/etc/fpai/env/fpai-website-com.env"

def check_fulfillment_config():
    """Checks if SMTP is configured in the env file."""
    try:
        with open(ENV_FILE, "r") as f:
            content = f.read()
            if "SMTP_URL=" in content and "smtps://" in content:
                return "🟢 Ready"
            return "🔴 Blocked (Missing SMTP)"
    except:
        return "⚪ Unknown (Access Denied)"

def main():
    # 1. Initialize State
    stations = {
        "traffic": {"status": "⚪ Unknown", "metric": "0 visits", "blocker": "No Probe"},
        "storefront": {"status": "⚪ Pending", "metric": "HTTP Status", "blocker": None},
        "checkout": {"status": "⚪ Pending", "metric": "API Health", "blocker": None},
        "fulfillment": {"status": "⚪ Pending", "metric": "Config Check", "blocker": None},
        "retention": {"status": "⚪ Unknown", "metric": "No Telemetry", "blocker": "No Probe"}
    }

    # 2. Audit Storefront
    try:
        r = requests.get(STOREFRONT_URL, timeout=5)
        if r.status_code == 200:
            stations["storefront"]["status"] = "🟢 Active"
        else:
            stations["storefront"]["status"] = f"🔴 Error {r.status_code}"
            stations["storefront"]["blocker"] = f"HTTP {r.status_code}"
    except Exception as e:
        stations["storefront"]["status"] = "🔴 Unreachable"
        stations["storefront"]["blocker"] = str(e)

    # 3. Audit Checkout
    try:
        r = requests.get(CHECKOUT_API, timeout=2)
        if r.status_code == 200:
            stations["checkout"]["status"] = "🟢 Ready"
        else:
            stations["checkout"]["status"] = "🔴 API Error"
            stations["checkout"]["blocker"] = "API Health Fail"
    except Exception as e:
        stations["checkout"]["status"] = "🔴 Service Down"
        stations["checkout"]["blocker"] = str(e)

    # 4. Audit Fulfillment
    stations["fulfillment"]["status"] = check_fulfillment_config()
    if "Blocked" in stations["fulfillment"]["status"]:
        stations["fulfillment"]["blocker"] = "Missing SMTP Credentials"

    # 5. Write Machine State (JSON)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(ASSEMBLY_FILE_JSON, "w") as f:
        json.dump(stations, f, indent=2)

    # 6. Write Human State (Markdown)
    md_content = f"""# 🏭 FPAI ASSEMBLY LINE STATUS

> **Last Audit:** {json.dumps(stations, indent=2)}

## 1. TRAFFIC (Inbound)
- **Status:** {stations['traffic']['status']}
- **Blocker:** {stations['traffic']['blocker'] or 'None'}

## 2. STOREFRONT (Conversion)
- **Status:** {stations['storefront']['status']}
- **URL:** {STOREFRONT_URL}
- **Blocker:** {stations['storefront']['blocker'] or 'None'}

## 3. CHECKOUT (Transaction)
- **Status:** {stations['checkout']['status']}
- **Blocker:** {stations['checkout']['blocker'] or 'None'}

## 4. FULFILLMENT (Delivery)
- **Status:** {stations['fulfillment']['status']}
- **Blocker:** {stations['fulfillment']['blocker'] or 'None'}

## 5. RETENTION (Experience)
- **Status:** {stations['retention']['status']}
- **Blocker:** {stations['retention']['blocker'] or 'None'}
"""
    with open(ASSEMBLY_FILE_MD, "w") as f:
        f.write(md_content)
    
    print("Audit complete. JSON State updated.")

if __name__ == "__main__":
    main()
