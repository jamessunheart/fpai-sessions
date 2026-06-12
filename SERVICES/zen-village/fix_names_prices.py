#!/usr/bin/env python3
"""
Fix property names, prices, and descriptions:
1. Sky Lily Cabin → Sky Lily Zome (badge: Zome, not Geodesic Dome)
2. Astro Sol → Astro Sol Zome (badge: Zome)
3. Cloud Cabin → La Vista (circular hilltop cabin)
4. Summit Cabin → The Nest (El Nido = The Nest)
5. Revert all prices to original values (before my incorrect changes)
6. Fix "geodesic dome" → "zome" in descriptions
"""

FILE = "/opt/fpai/apps/zen-village/frontend/public/index.html"

with open(FILE, "r") as f:
    html = f.read()

changes = 0

# ============================================================
# 1. Sky Lily: fix badge, tagline, prices back to $130
# ============================================================
old = """                <!-- Sky Lily Cabin -->
                <div class="accommodation-card" onclick="openPropertyModal('astro-alpha')" style="cursor:pointer">
                    <div class="accommodation-image astro has-image">
                        🪷
                        <span class="accommodation-badge">Geodesic Dome</span>
                    </div>
                    <div class="accommodation-content">
                        <span class="zone-tag village-heart">Village Heart</span>
                        <h3 class="accommodation-name">Sky Lily Cabin</h3>
                        <p class="accommodation-tagline">Geodesic dome · Sleeps 2 · Like a lily pad in the sky</p>
                        <div class="accommodation-pricing">
                            <div class="price-item">
                                <div class="label">Nightly</div>
                                <div class="amount">$55</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Weekly</div>
                                <div class="amount">$330</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Monthly</div>
                                <div class="amount">$1,000</div>
                            </div>
                        </div>"""

new = """                <!-- Sky Lily Zome -->
                <div class="accommodation-card" onclick="openPropertyModal('astro-alpha')" style="cursor:pointer">
                    <div class="accommodation-image astro has-image">
                        🪷
                        <span class="accommodation-badge">Zome</span>
                    </div>
                    <div class="accommodation-content">
                        <span class="zone-tag village-heart">Village Heart</span>
                        <h3 class="accommodation-name">Sky Lily Zome</h3>
                        <p class="accommodation-tagline">Two-story zome · Sleeps 2-4 · Like a lily pad in the sky</p>
                        <div class="accommodation-pricing">
                            <div class="price-item">
                                <div class="label">Nightly</div>
                                <div class="amount">$130</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Weekly</div>
                                <div class="amount">$780</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Monthly</div>
                                <div class="amount">$2,200</div>
                            </div>
                        </div>"""

if old in html:
    html = html.replace(old, new)
    changes += 1
    print("✅ Sky Lily: Cabin→Zome, badge→Zome, prices→$130/night")
else:
    print("⚠️  Sky Lily card not found")

# ============================================================
# 2. Astro Sol: fix badge, tagline, prices back to $130
# ============================================================
old = """                <!-- Astro Sol -->
                <div class="accommodation-card" onclick="openPropertyModal('astro-sol')" style="cursor:pointer">
                    <div class="accommodation-image astro has-image">
                        ☀️
                        <span class="accommodation-badge">Geodesic Dome</span>
                    </div>
                    <div class="accommodation-content">
                        <span class="zone-tag village-heart">Village Heart</span>
                        <h3 class="accommodation-name">Astro Sol</h3>
                        <p class="accommodation-tagline">Geodesic dome · Sleeps 2 · Sun-drenched views</p>
                        <div class="accommodation-pricing">
                            <div class="price-item">
                                <div class="label">Nightly</div>
                                <div class="amount">$55</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Weekly</div>
                                <div class="amount">$330</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Monthly</div>
                                <div class="amount">$1,000</div>
                            </div>
                        </div>"""

new = """                <!-- Astro Sol Zome -->
                <div class="accommodation-card" onclick="openPropertyModal('astro-sol')" style="cursor:pointer">
                    <div class="accommodation-image astro has-image">
                        ☀️
                        <span class="accommodation-badge">Zome</span>
                    </div>
                    <div class="accommodation-content">
                        <span class="zone-tag village-heart">Village Heart</span>
                        <h3 class="accommodation-name">Astro Sol Zome</h3>
                        <p class="accommodation-tagline">Two-story zome · Sleeps 2-4 · Sun-drenched views</p>
                        <div class="accommodation-pricing">
                            <div class="price-item">
                                <div class="label">Nightly</div>
                                <div class="amount">$130</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Weekly</div>
                                <div class="amount">$780</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Monthly</div>
                                <div class="amount">$2,200</div>
                            </div>
                        </div>"""

if old in html:
    html = html.replace(old, new)
    changes += 1
    print("✅ Astro Sol: →Astro Sol Zome, badge→Zome, prices→$130/night")
else:
    print("⚠️  Astro Sol card not found")

# ============================================================
# 3. Riverlight: revert price $65 → $120
# ============================================================
old = """                        <h3 class="accommodation-name">Riverlight Cabin</h3>
                        <p class="accommodation-tagline">Riverside cabin · Sleeps 2 · Wood & nature</p>
                        <div class="accommodation-pricing">
                            <div class="price-item">
                                <div class="label">Nightly</div>
                                <div class="amount">$65</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Weekly</div>
                                <div class="amount">$390</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Monthly</div>
                                <div class="amount">$1,200</div>
                            </div>
                        </div>"""

new = """                        <h3 class="accommodation-name">Riverlight Cabin</h3>
                        <p class="accommodation-tagline">Riverside cabin · Sleeps 2 · Wood & nature</p>
                        <div class="accommodation-pricing">
                            <div class="price-item">
                                <div class="label">Nightly</div>
                                <div class="amount">$120</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Weekly</div>
                                <div class="amount">$720</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Monthly</div>
                                <div class="amount">$2,000</div>
                            </div>
                        </div>"""

if old in html:
    html = html.replace(old, new)
    changes += 1
    print("✅ Riverlight: $65→$120/night (reverted)")
else:
    print("⚠️  Riverlight prices not found")

# ============================================================
# 4. Zen Casa: revert $195 → $180
# ============================================================
old = """                        <h3 class="accommodation-name">Zen Casa</h3>
                        <p class="accommodation-tagline">Spacious home · Sleeps 6 · 3 bedrooms</p>
                        <div class="accommodation-pricing">
                            <div class="price-item">
                                <div class="label">Nightly</div>
                                <div class="amount">$195</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Weekly</div>
                                <div class="amount">$1,170</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Monthly</div>
                                <div class="amount">$3,500</div>
                            </div>
                        </div>"""

new = """                        <h3 class="accommodation-name">Zen Casa</h3>
                        <p class="accommodation-tagline">Spacious home · Sleeps 6 · 3 bedrooms</p>
                        <div class="accommodation-pricing">
                            <div class="price-item">
                                <div class="label">Nightly</div>
                                <div class="amount">$180</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Weekly</div>
                                <div class="amount">$1,080</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Monthly</div>
                                <div class="amount">$3,200</div>
                            </div>
                        </div>"""

if old in html:
    html = html.replace(old, new)
    changes += 1
    print("✅ Zen Casa: $195→$180/night (reverted)")
else:
    print("⚠️  Zen Casa prices not found")

# ============================================================
# 5. Cloud Cabin → La Vista, revert $75 → $150
# ============================================================
old = """                        <h3 class="accommodation-name">Cloud Cabin</h3>
                        <p class="accommodation-tagline">Hilltop cabin · Sleeps 2 · Panoramic views · 4×4 required</p>
                        <div class="accommodation-pricing">
                            <div class="price-item">
                                <div class="label">Nightly</div>
                                <div class="amount">$75</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Weekly</div>
                                <div class="amount">$450</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Monthly</div>
                                <div class="amount">$1,400</div>
                            </div>
                        </div>"""

new = """                        <h3 class="accommodation-name">La Vista</h3>
                        <p class="accommodation-tagline">Circular hilltop cabin · Sleeps 2 · Panoramic views · 4×4 required</p>
                        <div class="accommodation-pricing">
                            <div class="price-item">
                                <div class="label">Nightly</div>
                                <div class="amount">$150</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Weekly</div>
                                <div class="amount">$900</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Monthly</div>
                                <div class="amount">$2,400</div>
                            </div>
                        </div>"""

if old in html:
    html = html.replace(old, new)
    changes += 1
    print("✅ Cloud Cabin → La Vista, $75→$150/night (reverted)")
else:
    print("⚠️  Cloud Cabin/Vista card not found")

# ============================================================
# 6. Summit Cabin → The Nest, revert $75 → $115
# ============================================================
old = """                        <h3 class="accommodation-name">Summit Cabin</h3>
                        <p class="accommodation-tagline">Hillside cabin · Sleeps 2 · Deep solitude · 4×4 required</p>
                        <div class="accommodation-pricing">
                            <div class="price-item">
                                <div class="label">Nightly</div>
                                <div class="amount">$75</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Weekly</div>
                                <div class="amount">$450</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Monthly</div>
                                <div class="amount">$1,400</div>
                            </div>
                        </div>"""

new = """                        <h3 class="accommodation-name">The Nest</h3>
                        <p class="accommodation-tagline">Circular hillside cabin · Sleeps 2 · Deep solitude · 4×4 required</p>
                        <div class="accommodation-pricing">
                            <div class="price-item">
                                <div class="label">Nightly</div>
                                <div class="amount">$115</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Weekly</div>
                                <div class="amount">$690</div>
                            </div>
                            <div class="price-item">
                                <div class="label">Monthly</div>
                                <div class="amount">$1,900</div>
                            </div>
                        </div>"""

if old in html:
    html = html.replace(old, new)
    changes += 1
    print("✅ Summit Cabin → The Nest, $75→$115/night (reverted)")
else:
    print("⚠️  Summit Cabin/Nest card not found")

# ============================================================
# 7. Fix callout texts
# ============================================================
# Zomes callout
old_c = "Sky Lily Cabin and Astro Sol are not standard cabins"
new_c = "Sky Lily Zome and Astro Sol Zome are not standard cabins"
if old_c in html:
    html = html.replace(old_c, new_c)
    changes += 1
    print("✅ Updated zomes callout")

# Escape Ridge callout - Cloud/Summit → La Vista/The Nest
old_r = "Cloud Cabin and Summit Cabin both sit on Escape Ridge"
new_r = "La Vista and The Nest both sit on Escape Ridge"
if old_r in html:
    html = html.replace(old_r, new_r)
    changes += 1
    print("✅ Updated Escape Ridge callout")

# All remaining Cloud Cabin & Summit Cabin refs in callouts/FAQ
html = html.replace("Cloud Cabin & Summit Cabin", "La Vista & The Nest")
html = html.replace("Cloud Cabin &amp; Summit Cabin", "La Vista &amp; The Nest")

# ============================================================
# 8. Update propertyData JS names + prices + descriptions
# ============================================================
# Sky Lily
html = html.replace("name: 'Sky Lily Cabin',", "name: 'Sky Lily Zome',")
html = html.replace(
    "desc: 'A unique geodesic dome shaped like a lily pad floating in the sky. Panoramic views, immersive nature, and an experience unlike any other.',",
    "desc: 'A unique two-story zome shaped like a lily pad floating in the sky. Panoramic views, immersive nature, and an experience unlike any other.',")
old_prices = "prices: { night: 55, week: 330, month: 1000 },"
# This appears twice (alpha and sol), need to handle carefully
# Replace in context of astro-alpha
html = html.replace(
    "name: 'Sky Lily Zome',\n    zone: 'Village Heart',\n    desc: 'A unique two-story zome shaped like a lily pad floating in the sky. Panoramic views, immersive nature, and an experience unlike any other.',\n    prices: { night: 55, week: 330, month: 1000 },",
    "name: 'Sky Lily Zome',\n    zone: 'Village Heart',\n    desc: 'A unique two-story zome shaped like a lily pad floating in the sky. Panoramic views, immersive nature, and an experience unlike any other.',\n    prices: { night: 130, week: 780, month: 2200 },")

# Astro Sol
html = html.replace("name: 'Astro Sol',", "name: 'Astro Sol Zome',")
html = html.replace(
    "desc: 'Sister to Astro Alpha, this geodesic dome offers the same magical design with its own unique character and views.',",
    "desc: 'Sister zome to Sky Lily, Astro Sol offers the same magical two-story design with its own unique character and sun-drenched views.',")
html = html.replace(
    "name: 'Astro Sol Zome',\n    zone: 'Village Heart',\n    desc: 'Sister zome to Sky Lily, Astro Sol offers the same magical two-story design with its own unique character and sun-drenched views.',\n    prices: { night: 55, week: 330, month: 1000 },",
    "name: 'Astro Sol Zome',\n    zone: 'Village Heart',\n    desc: 'Sister zome to Sky Lily, Astro Sol offers the same magical two-story design with its own unique character and sun-drenched views.',\n    prices: { night: 130, week: 780, month: 2200 },")

# La Vista (was Cloud Cabin)
html = html.replace("name: 'Cloud Cabin (Hilltop)',", "name: 'La Vista',")
html = html.replace(
    "desc: 'Perched on the hillside with breathtaking panoramic views over the valley. Features a spacious deck perfect for sunrise meditation and evening stargazing. 4x4 vehicle required for hilltop access.',",
    "desc: 'A circular hilltop cabin perched on the hillside with breathtaking panoramic views over the valley. Features a spacious deck perfect for sunrise meditation and evening stargazing. 4x4 vehicle required.',")
html = html.replace("prices: { night: 75, week: 450, month: 1400 },", "prices: { night: 150, week: 900, month: 2400 },", 1)

# The Nest (was Summit Cabin)
html = html.replace("name: 'Summit Cabin (Hilltop)',", "name: 'The Nest',")
html = html.replace(
    "desc: 'A cozy hillside cabin offering solitude and stunning views. The perfect nest for writers, artists, or anyone seeking deep retreat. 4x4 vehicle required for hilltop access.',",
    "desc: 'A cozy circular hillside cabin offering solitude and stunning views. The perfect nest for writers, artists, or anyone seeking deep retreat. 4x4 vehicle required.',")
# The Nest prices - find the remaining $75 one
html = html.replace(
    "name: 'The Nest',\n    zone: 'Escape Ridge',\n    desc: 'A cozy circular hillside cabin offering solitude and stunning views. The perfect nest for writers, artists, or anyone seeking deep retreat. 4x4 vehicle required.',\n    prices: { night: 75, week: 450, month: 1400 },",
    "name: 'The Nest',\n    zone: 'Escape Ridge',\n    desc: 'A cozy circular hillside cabin offering solitude and stunning views. The perfect nest for writers, artists, or anyone seeking deep retreat. 4x4 vehicle required.',\n    prices: { night: 115, week: 690, month: 1900 },")

# Riverlight prices in JS
html = html.replace("prices: { night: 65, week: 390, month: 1200 },", "prices: { night: 120, week: 720, month: 2000 },")

# Zen Casa prices in JS
html = html.replace("prices: { night: 195, week: 1170, month: 3500 },", "prices: { night: 180, week: 1080, month: 3200 },")

print("✅ Updated all propertyData JS names, descriptions, and prices")
changes += 1

# ============================================================
# Write
# ============================================================
with open(FILE, "w") as f:
    f.write(html)

print(f"\n✅ Done! {changes} groups of changes applied")

# Verify
for term in ["Sky Lily Zome", "Astro Sol Zome", "La Vista", "The Nest", "$130", "$150", "$115", "$120", "$180"]:
    count = html.count(term)
    print(f"  '{term}': {count} occurrences")
