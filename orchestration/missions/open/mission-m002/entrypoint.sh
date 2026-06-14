#!/bin/bash
set -e

# 1. Run Migrations (If using Alembic later)
# echo "Running database migrations..."
# alembic upgrade head

# 2. Start Application
echo "Starting Mission Control Backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers

