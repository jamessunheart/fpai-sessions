#!/usr/bin/env python3
"""Ensure updateCardPrices runs even if DOMContentLoaded already fired."""

INDEX = "/opt/fpai/apps/zen-village/frontend/public/index.html"
with open(INDEX, 'r') as f:
    html = f.read()

old = "document.addEventListener('DOMContentLoaded', updateCardPrices);"
new = """document.addEventListener('DOMContentLoaded', updateCardPrices);
if (document.readyState !== 'loading') { updateCardPrices(); }"""

if 'readyState' not in html:
    html = html.replace(old, new)
    print("Added readyState fallback")
else:
    print("Already has readyState check")

with open(INDEX, 'w') as f:
    f.write(html)
print("Done")
