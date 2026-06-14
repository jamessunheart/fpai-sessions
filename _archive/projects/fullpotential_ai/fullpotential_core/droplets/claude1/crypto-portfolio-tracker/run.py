#!/usr/bin/env python3
"""
Crypto Portfolio Tracker - Start script
"""
import argparse
import uvicorn

def main():
    parser = argparse.ArgumentParser(description="Start the Crypto Portfolio Tracker")
    parser.add_argument("--port", type=int, default=8002, help="Port to run on (default: 8002)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    print(f"""
    ╔══════════════════════════════════════╗
    ║  💰 Crypto Portfolio Tracker        ║
    ║                                      ║
    ║  Dashboard: http://localhost:{args.port}/dashboard/money
    ║  API: http://localhost:{args.port}/api/treasury/positions
    ║                                      ║
    ║  Press CTRL+C to stop               ║
    ╚══════════════════════════════════════╝
    """)

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main()
