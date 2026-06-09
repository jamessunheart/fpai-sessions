import os
import sys

# Ensure the concierge/ root is importable as the first entry on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
