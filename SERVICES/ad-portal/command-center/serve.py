#!/usr/bin/env python3
"""
Simple HTTP server for the Ad Portal Command Center

Run this on the server to serve the task dashboard:
    python3 serve.py

Then access at: http://198.54.123.234:8802
"""
import http.server
import socketserver
import os

PORT = 8802
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def main():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"""
╔════════════════════════════════════════════════════════════════╗
║          AD PORTAL COMMAND CENTER                              ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  🚀 Server running at: http://localhost:{PORT}                  ║
║                                                                ║
║  For remote access:                                            ║
║  http://198.54.123.234:{PORT}                                   ║
║                                                                ║
║  Press Ctrl+C to stop                                          ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
        """)
        httpd.serve_forever()

if __name__ == "__main__":
    main()


