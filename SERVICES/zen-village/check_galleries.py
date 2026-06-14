#!/usr/bin/env python3
import re

with open('/opt/fpai/apps/zen-village/frontend/public/index.html') as f:
    html = f.read()

for key in ['camp-spring', 'glamp-grove', 'jungle-platform', 'river-house']:
    pattern = "'" + key + "': {"
    idx = html.find(pattern)
    if idx >= 0:
        chunk = html[idx:idx+600]
        print(f"--- {key} ---")
        print(chunk[:500])
        print()
    else:
        print(f"{key}: NOT FOUND in propertyData")
