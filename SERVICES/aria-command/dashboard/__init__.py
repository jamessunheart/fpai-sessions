#!/usr/bin/env python3
"""
Dashboard Module
================
One interface for James to see everything.

Components:
- app.py: FastAPI routes and main UI
"""
from .app import router as dashboard_router, get_dashboard_data

__all__ = ['dashboard_router', 'get_dashboard_data']








