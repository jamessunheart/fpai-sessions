#!/usr/bin/env python3
"""
Update accommodation cards in index.html:
1. Rename Astro Alpha → Sky Lily Cabin
2. Remove Hearth House (communal, not for rent)
3. Update card prices to match gallery modal pricing
4. Sync card names with gallery names (Vista→Cloud Cabin, Nido→Summit Cabin)
"""

FILE = "/opt/fpai/apps/zen-village/frontend/public/index.html"

with open(FILE, "r") as f:
    html = f.read()

changes = 0

# ============================================================
# 1. Remove The Hearth House card (communal, not for rent)
# ============================================================
old_hearth = """                <!-- The Hearth House -->
                <div class="accommodation-card" onclick="openPropertyModal('hearth-house')" style="cursor:pointer">
                    <div class="accommodation-image hearth has-image">
                        🏠
                        <span class="accommodation-badge">Communal Home</span>
                    </div>
                    <div class="accommodation-content">
                        <span class="zone-tag village-heart">Village Heart</span>
                        <h3 class="accommodation-name">The Hearth House</h3>
                        <p class="accommodation-tagline">Communal home · Sleeps 6 · 3 bedrooms</p>
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
                        </div>
                        <div class="accommodation-cta">
                            <a href="#" onclick="openBookingModal('Stay'); return false;" class="btn btn-primary">Book This Space</a>
                        </div>
                    </div>
                </div>
                """

if old_hearth in html:
    html = html.replace(old_hearth, "                ")
    changes += 1
    print("✅ Removed Hearth House card")
else:
    print("⚠️  Hearth House card not found (may have different whitespace)")

# ============================================================
# 2. Rename Astro Alpha → Sky Lily Cabin (card)
# ============================================================
old_alpha_card = """                <!-- Astro Alpha -->
                <div class="accommodation-card" onclick="openPropertyModal('astro-alpha')" style="cursor:pointer">
                    <div class="accommodation-image astro has-image">
                        🌟
                        <span class="accommodation-badge">Two-Story Zome</span>
                    </div>
                    <div class="accommodation-content">
                        <span class="zone-tag village-heart">Village Heart</span>
                        <h3 class="accommodation-name">Astro Alpha</h3>
                        <p class="accommodation-tagline">Two-story zome · Sleeps 2-4 · Queen bed upstairs</p>
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
                        </div>
                        <div class="accommodation-cta">
                            <a href="#" onclick="openBookingModal('Stay'); return false;" class="btn btn-primary">Book This Space</a>
                        </div>
                    </div>
                </div>"""

new_alpha_card = """                <!-- Sky Lily Cabin -->
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
                        </div>
                        <div class="accommodation-cta">
                            <a href="#" onclick="openBookingModal('Stay'); return false;" class="btn btn-primary">Book This Space</a>
                        </div>
                    </div>
                </div>"""

if old_alpha_card in html:
    html = html.replace(old_alpha_card, new_alpha_card)
    changes += 1
    print("✅ Renamed Astro Alpha → Sky Lily Cabin (card)")
else:
    print("⚠️  Astro Alpha card not found")

# ============================================================
# 3. Update Astro Sol card prices ($130 → $55)
# ============================================================
old_sol_card = """                <!-- Astro Sol -->
                <div class="accommodation-card" onclick="openPropertyModal('astro-sol')" style="cursor:pointer">
                    <div class="accommodation-image astro has-image">
                        ☀️
                        <span class="accommodation-badge">Two-Story Zome</span>
                    </div>
                    <div class="accommodation-content">
                        <span class="zone-tag village-heart">Village Heart</span>
                        <h3 class="accommodation-name">Astro Sol</h3>
                        <p class="accommodation-tagline">Two-story zome · Sleeps 2-4 · Queen bed upstairs</p>
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
                        </div>
                        <div class="accommodation-cta">
                            <a href="#" onclick="openBookingModal('Stay'); return false;" class="btn btn-primary">Book This Space</a>
                        </div>
                    </div>
                </div>"""

new_sol_card = """                <!-- Astro Sol -->
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
                        </div>
                        <div class="accommodation-cta">
                            <a href="#" onclick="openBookingModal('Stay'); return false;" class="btn btn-primary">Book This Space</a>
                        </div>
                    </div>
                </div>"""

if old_sol_card in html:
    html = html.replace(old_sol_card, new_sol_card)
    changes += 1
    print("✅ Updated Astro Sol card (prices $130→$55)")
else:
    print("⚠️  Astro Sol card not found")

# ============================================================
# 4. Update Riverlight Cabin prices ($120 → $65)
# ============================================================
old_river_prices = """                        <h3 class="accommodation-name">Riverlight Cabin</h3>
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

new_river_prices = """                        <h3 class="accommodation-name">Riverlight Cabin</h3>
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

if old_river_prices in html:
    html = html.replace(old_river_prices, new_river_prices)
    changes += 1
    print("✅ Updated Riverlight prices ($120→$65)")
else:
    print("⚠️  Riverlight prices not found")

# ============================================================
# 5. Update Zen Casa prices ($180 → $195)
# ============================================================
old_zen_prices = """                        <h3 class="accommodation-name">Zen Casa</h3>
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

new_zen_prices = """                        <h3 class="accommodation-name">Zen Casa</h3>
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

if old_zen_prices in html:
    html = html.replace(old_zen_prices, new_zen_prices)
    changes += 1
    print("✅ Updated Zen Casa prices ($180→$195)")
else:
    print("⚠️  Zen Casa prices not found")

# ============================================================
# 6. Update The Vista → Cloud Cabin ($150 → $75)
# ============================================================
old_vista = """                        <h3 class="accommodation-name">The Vista</h3>
                        <p class="accommodation-tagline">Hilltop cabin · Sleeps 2 · Panoramic deck · 4×4 needed</p>
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

new_vista = """                        <h3 class="accommodation-name">Cloud Cabin</h3>
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

if old_vista in html:
    html = html.replace(old_vista, new_vista)
    changes += 1
    print("✅ Updated The Vista → Cloud Cabin ($150→$75)")
else:
    print("⚠️  The Vista prices not found")

# ============================================================
# 7. Update The Nido → Summit Cabin ($115 → $75)
# ============================================================
old_nido = """                        <h3 class="accommodation-name">The Nido</h3>
                        <p class="accommodation-tagline">Hillside cabin · Sleeps 2 · Deep solitude · 4×4 needed</p>
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

new_nido = """                        <h3 class="accommodation-name">Summit Cabin</h3>
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

if old_nido in html:
    html = html.replace(old_nido, new_nido)
    changes += 1
    print("✅ Updated The Nido → Summit Cabin ($115→$75)")
else:
    print("⚠️  The Nido prices not found")

# ============================================================
# 8. Update Zomes callout text
# ============================================================
old_callout = """Astro Alpha and Astro Sol are not standard cabins"""
new_callout = """Sky Lily Cabin and Astro Sol are not standard cabins"""
if old_callout in html:
    html = html.replace(old_callout, new_callout)
    changes += 1
    print("✅ Updated zomes callout text")

# ============================================================
# 9. Update Escape Ridge callout for new names
# ============================================================
old_ridge = "The Vista and The Nido both sit on Escape Ridge"
new_ridge = "Cloud Cabin and Summit Cabin both sit on Escape Ridge"
if old_ridge in html:
    html = html.replace(old_ridge, new_ridge)
    changes += 1
    print("✅ Updated Escape Ridge callout")

old_ridge2 = "The Vista & The Nido"
new_ridge2 = "Cloud Cabin & Summit Cabin"
html = html.replace(old_ridge2, new_ridge2)

# ============================================================
# 10. Update propertyData JS for Sky Lily name
# ============================================================
old_alpha_js = "name: 'Astro Alpha',"
new_alpha_js = "name: 'Sky Lily Cabin',"
if old_alpha_js in html:
    html = html.replace(old_alpha_js, new_alpha_js)
    changes += 1
    print("✅ Updated propertyData name: Astro Alpha → Sky Lily Cabin")

old_alpha_desc = "desc: 'A unique geodesic dome with panoramic views and immersive nature experience. Sleep under the stars in this architectural wonder.',"
new_alpha_desc = "desc: 'A unique geodesic dome shaped like a lily pad floating in the sky. Panoramic views, immersive nature, and an experience unlike any other.',"
if old_alpha_desc in html:
    html = html.replace(old_alpha_desc, new_alpha_desc)
    print("  Updated Sky Lily description")

# Write
with open(FILE, "w") as f:
    f.write(html)

print(f"\n✅ Done! {changes} changes applied to index.html")
