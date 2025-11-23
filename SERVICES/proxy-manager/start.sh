#!/bin/bash
set -e

# Start Uvicorn
# We assume Nginx is managed externally (e.g. host Nginx via volume mounts)
echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8100
