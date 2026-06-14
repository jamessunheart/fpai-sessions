#!/usr/bin/env python3
"""
Fix propertyData keys: camp-spring and glamp-grove have wrong data.
Also add proper data for jungle-platform and river-house as separate entries.
"""
import re

INDEX = "/opt/fpai/apps/zen-village/frontend/public/index.html"
with open(INDEX) as f:
    html = f.read()

# Fix camp-spring: currently shows Jungle Platform data, should show Camp Spring
old_camp = """'camp-spring': {
    name: 'Jungle Platform',
    zone: 'Village Heart',
    desc: 'An open-air platform surrounded by jungle. Bring your own tent or hammock and camp under the stars. Access to all village amenities including sauna and river.',
    prices: { night: 45, week: 270, month: 800 },
    images: [
      '/images/placeholder.svg'
    ]
  }"""

new_camp = """'camp-spring': {
    name: 'Camp Spring',
    zone: 'Village Heart',
    desc: 'Bring your own tent and camp on a natural spring-fed clearing surrounded by lush jungle. Enjoy full access to village amenities including sauna, hot tub, fire pit, and river. The most affordable way to experience Zen Village.',
    prices: { night: 20, week: 120, month: 350 },
    images: [
      '/images/accommodations/communal/1.jpg',
      '/images/accommodations/communal/2.jpg'
    ]
  }"""

if old_camp in html:
    html = html.replace(old_camp, new_camp)
    print("✅ Fixed camp-spring propertyData (was showing Jungle Platform)")
else:
    print("⚠️  camp-spring old data not found exactly, trying flexible match...")
    pattern = r"'camp-spring': \{[^}]*name: 'Jungle Platform'[^}]*\}[^}]*\}"
    m = re.search(pattern, html, re.DOTALL)
    if m:
        html = html.replace(m.group(0), new_camp.lstrip())
        print("✅ Fixed camp-spring via regex")
    else:
        print("❌ Could not find camp-spring entry to fix")

# Fix glamp-grove: currently shows River House data, should show Glamp Grove
old_glamp = """'glamp-grove': {
    name: 'River House',
    zone: 'River Grove',
    desc: 'A comfortable riverside home with modern amenities and direct river access. Perfect for those seeking comfort without sacrificing the nature experience.',
    prices: { night: 85, week: 510, month: 1500 },
    images: [
      '/images/placeholder.svg'
    ]
  }"""

new_glamp = """'glamp-grove': {
    name: 'Glamp Grove',
    zone: 'Village Heart',
    desc: 'A furnished glamping tent set among the trees with a comfortable bed, lighting, and a covered sitting area. The perfect blend of nature immersion and comfort. Access to all village amenities.',
    prices: { night: 45, week: 270, month: 800 },
    images: [
      '/images/accommodations/communal/3.jpg',
      '/images/accommodations/communal/4.jpg'
    ]
  }"""

if old_glamp in html:
    html = html.replace(old_glamp, new_glamp)
    print("✅ Fixed glamp-grove propertyData (was showing River House)")
else:
    print("⚠️  glamp-grove old data not found exactly, trying flexible match...")
    pattern = r"'glamp-grove': \{[^}]*name: 'River House'[^}]*\}[^}]*\}"
    m = re.search(pattern, html, re.DOTALL)
    if m:
        html = html.replace(m.group(0), new_glamp.lstrip())
        print("✅ Fixed glamp-grove via regex")
    else:
        print("❌ Could not find glamp-grove entry to fix")

with open(INDEX, 'w') as f:
    f.write(html)

# Verify
with open(INDEX) as f:
    html = f.read()

for key in ['camp-spring', 'glamp-grove']:
    idx = html.find(f"'{key}':")
    if idx >= 0:
        chunk = html[idx:idx+200]
        name_m = re.search(r"name: '([^']+)'", chunk)
        price_m = re.search(r"night: (\d+)", chunk)
        if name_m and price_m:
            print(f"  {key}: name='{name_m.group(1)}', night=${price_m.group(1)}")

print("\n✅ Gallery data fix complete")
