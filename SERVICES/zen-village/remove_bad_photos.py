#!/usr/bin/env python3
"""Remove blurry and duplicate photos from gallery arrays in index.html."""

FILE = "/opt/fpai/apps/zen-village/frontend/public/index.html"

with open(FILE, "r") as f:
    html = f.read()

removals = [
    # Blurry
    ("the-vista/10.avif", "blurry (12KB, score 140)"),
    # zen-casa duplicates
    ("zen-casa/main.avif", "duplicate of zen-casa/2.avif"),
    ("zen-casa/18.avif", "duplicate of zen-casa/2.avif"),
    ("zen-casa/20.avif", "duplicate of zen-casa/19.avif"),
    # green-casita duplicate
    ("green-casita/main.avif", "duplicate of green-casita/2.avif"),
    # riverlight duplicate
    ("riverlight/main.avif", "duplicate of riverlight/2.avif"),
]

for img, reason in removals:
    path = f"/images/accommodations/{img}"
    
    # Try with trailing comma+newline first
    old1 = f"      '{path}',\n"
    old2 = f"      '{path}'\n"
    
    if old1 in html:
        html = html.replace(old1, "")
        print(f"  REMOVED: {img} ({reason})")
    elif old2 in html:
        html = html.replace(old2, "")
        print(f"  REMOVED: {img} ({reason})")
    else:
        print(f"  NOT FOUND in gallery: {img}")

# Clean up any trailing commas before ]
import re
html = re.sub(r",\s*\n\s*\]", "\n    ]", html)

with open(FILE, "w") as f:
    f.write(html)

print(f"\nDone. {len(removals)} images removed from gallery arrays.")
