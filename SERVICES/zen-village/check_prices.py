#!/usr/bin/env python3
"""Check card prices vs propertyData prices for consistency."""
import re

INDEX = "/opt/fpai/apps/zen-village/frontend/public/index.html"
with open(INDEX) as f:
    html = f.read()

print("=== CARD PRICES (what visitors see on cards) ===")
chunks = html.split('accommodation-card')
for c in chunks[1:]:
    name = re.search(r'accommodation-name">([^<]+)', c)
    price = re.search(r'\$(\d+)', c)
    tagline = re.search(r'accommodation-tagline">([^<]+)', c)
    if name:
        p = price.group(1) if price else '?'
        t = tagline.group(1) if tagline else ''
        print(f"  {name.group(1):20s} ${p}/night  |  {t}")

print("\n=== GALLERY/MODAL PRICES (propertyData JS) ===")
matches = re.findall(r"name: '([^']+)'.*?prices: \{ night: (\d+), week: (\d+), month: (\d+) \}", html, re.DOTALL)
for name, night, week, month in matches:
    print(f"  {name:20s} ${night}/night, ${week}/week, ${month}/month")

print("\n=== IMAGE COUNTS (gallery modal) ===")
matches = re.findall(r"name: '([^']+)'.*?images: \[([^\]]+)\]", html, re.DOTALL)
for name, imgs in matches:
    count = len([x.strip() for x in imgs.split(',') if x.strip()])
    print(f"  {name:20s} {count} photos")

print("\n=== IMAGE FILES ON SERVER ===")
import os
base = "/opt/fpai/apps/zen-village/frontend/public/images/accommodations"
if os.path.isdir(base):
    for d in sorted(os.listdir(base)):
        dp = os.path.join(base, d)
        if os.path.isdir(dp):
            files = [f for f in os.listdir(dp) if not f.startswith('.')]
            print(f"  {d:25s} {len(files)} files")
