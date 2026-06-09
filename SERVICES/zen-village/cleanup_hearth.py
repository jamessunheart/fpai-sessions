#!/usr/bin/env python3
"""Remove hearth-house from propertyData JS since it's not for rent."""
import re

FILE = "/opt/fpai/apps/zen-village/frontend/public/index.html"
with open(FILE, "r") as f:
    html = f.read()

# Remove hearth-house entry from propertyData
pattern = r"  'hearth-house': \{.*?\},\n"
match = re.search(pattern, html, re.DOTALL)
if match:
    html = html[:match.start()] + html[match.end():]
    print(f"Removed hearth-house from propertyData ({match.end()-match.start()} chars)")
else:
    print("hearth-house entry not found in propertyData")

with open(FILE, "w") as f:
    f.write(html)

# Verify
count = html.count("hearth-house") + html.count("Hearth House")
print(f"Remaining hearth references: {count} (CSS background only)")
