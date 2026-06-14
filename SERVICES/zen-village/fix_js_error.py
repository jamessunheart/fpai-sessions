#!/usr/bin/env python3
"""Fix the orphaned hearth-house entry at the start of propertyData that causes JS syntax error."""

INDEX = "/opt/fpai/apps/zen-village/frontend/public/index.html"
with open(INDEX, 'r') as f:
    html = f.read()

# The problem: propertyData starts with an orphaned images array
# instead of a proper key: { ... } entry
old = """const propertyData = {
    images: [
      '/images/accommodations/hearth-house/main.avif',
      '/images/accommodations/hearth-house/1.avif',
      '/images/accommodations/hearth-house/2.avif',
      '/images/accommodations/hearth-house/3.avif',
      '/images/accommodations/hearth-house/4.webp',
      '/images/accommodations/hearth-house/5.webp',
      '/images/accommodations/hearth-house/6.avif',
      '/images/accommodations/hearth-house/7.avif',
      '/images/accommodations/hearth-house/8.avif',
      '/images/accommodations/hearth-house/9.avif',
      '/images/accommodations/hearth-house/10.avif',
      '/images/accommodations/hearth-house/11.avif',
      '/images/accommodations/hearth-house/12.avif',
      '/images/accommodations/hearth-house/13.avif',
      '/images/accommodations/hearth-house/14.avif'
    ]
  },
  'green-casita': {"""

new = """const propertyData = {
  'green-casita': {"""

if old in html:
    html = html.replace(old, new)
    print("✅ Removed orphaned hearth-house entry from propertyData")
else:
    print("❌ Could not find the orphaned hearth-house entry")

with open(INDEX, 'w') as f:
    f.write(html)

# Verify no more hearth-house in propertyData
idx = html.find('const propertyData')
if idx >= 0:
    chunk = html[idx:idx+200]
    if 'hearth-house' in chunk:
        print("⚠️  hearth-house still in propertyData start")
    else:
        print("✅ propertyData starts cleanly with green-casita")

# Also check for any remaining syntax issues
import re
pd_start = html.find('const propertyData = {')
if pd_start >= 0:
    depth = 0
    i = html.find('{', pd_start)
    count = 0
    while i < len(html) and count < 100000:
        if html[i] == '{': depth += 1
        elif html[i] == '}': depth -= 1
        if depth == 0:
            print(f"✅ propertyData closes properly at position {i}")
            break
        i += 1
        count += 1

print("✅ JS error fix complete")
