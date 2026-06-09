#!/usr/bin/env python3
"""
ALIGNMENT ECONOMICS / BANK OF BLESSINGS
=========================================

Value optimized for circulation, not accumulation.
Debt engineered to self-resolve through participation and time.
Forgiveness emerges as a mechanical outcome, not charity.

Start the server:
    python main.py

Or with uvicorn:
    uvicorn api.server:app --port 8760 --reload
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.server import app
from ledger.storage import init_db
import uvicorn


def main():
    # Initialize database
    init_db()
    
    # Get port from environment
    port = int(os.getenv("AE_PORT", "8760"))
    
    print("=" * 60)
    print("  ALIGNMENT ECONOMICS / BANK OF BLESSINGS")
    print("=" * 60)
    print()
    print("  Principles:")
    print("    1. Circulation over accumulation")
    print("    2. Forgiveness by design")
    print("    3. Coherence first, yield last")
    print()
    print(f"  API: http://localhost:{port}")
    print(f"  Dashboard: http://localhost:{port}/dashboard")
    print(f"  Health: http://localhost:{port}/health")
    print(f"  Checklist: http://localhost:{port}/checklist")
    print()
    print("=" * 60)
    
    # Serve static dashboard
    from fastapi.staticfiles import StaticFiles
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard")
    app.mount("/dashboard", StaticFiles(directory=dashboard_path, html=True), name="dashboard")
    
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()


