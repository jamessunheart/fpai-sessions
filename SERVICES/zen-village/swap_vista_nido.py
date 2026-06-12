#!/usr/bin/env python3
"""
Swap La Vista and El Nido names/descriptions/prices in index.html,
and remove duplicate images from gallery arrays.
"""
import re

FILE = "/opt/fpai/apps/zen-village/frontend/public/index.html"

with open(FILE, "r") as f:
    html = f.read()

# ─────────────────────────────────────────────────────
# 1. SWAP THE JS PROPERTY DATA (name, desc, prices)
# ─────────────────────────────────────────────────────

# the-vista currently says "La Vista" → change to "El Nido"
# the-nido currently says "The Nest" → change to "La Vista"

# Swap name in JS objects
html = html.replace(
    "'the-vista': {\n    name: 'La Vista',\n    zone: 'Escape Ridge',\n    desc: 'A circular hilltop cabin with queen bed, perched on the hillside with breathtaking panoramic views over the valley. Features a spacious deck perfect for sunrise meditation and stargazing. 4x4 vehicle required.',\n    highPrices: { night: 150, week: 900, month: 2400 },\n    greenPrices: { night: 128, week: 765, month: 2040 },",
    "'the-vista': {\n    name: 'El Nido',\n    zone: 'Escape Ridge',\n    desc: 'A cozy circular hillside cabin with a single bed, offering solitude and stunning views. The perfect nest for solo travelers, writers, or couples seeking deep retreat. 4x4 vehicle required.',\n    highPrices: { night: 115, week: 690, month: 1900 },\n    greenPrices: { night: 98, week: 586, month: 1615 },"
)

html = html.replace(
    "'the-nido': {\n    name: 'The Nest',\n    zone: 'Escape Ridge',\n    desc: 'A cozy circular hillside cabin with a single bed, offering solitude and stunning views. The perfect nest for solo travelers, writers, or couples seeking deep retreat. 4x4 vehicle required.',\n    highPrices: { night: 115, week: 690, month: 1900 },\n    greenPrices: { night: 98, week: 586, month: 1615 },",
    "'the-nido': {\n    name: 'La Vista',\n    zone: 'Escape Ridge',\n    desc: 'A circular hilltop cabin with queen bed, perched on the hillside with breathtaking panoramic views over the valley. Features a spacious deck perfect for sunrise meditation and stargazing. 4x4 vehicle required.',\n    highPrices: { night: 150, week: 900, month: 2400 },\n    greenPrices: { night: 128, week: 765, month: 2040 },"
)

print("[OK] Swapped JS property data (names, descriptions, prices)")

# ─────────────────────────────────────────────────────
# 2. SWAP THE HTML CARDS
# ─────────────────────────────────────────────────────

# Card for the-vista: currently says "La Vista" → "El Nido"
html = html.replace(
    '''<div class="accommodation-card" onclick="openPropertyModal('the-vista')">
                    <div class="accommodation-image vista has-image">
                        🏔️
                        <span class="accommodation-badge">Panoramic Views</span>
                    </div>
                    <div class="accommodation-content">
                        <span class="zone-tag escape-ridge">Escape Ridge</span>
                        <h3 class="accommodation-name">La Vista</h3>
                        <p class="accommodation-tagline">Circular hilltop cabin · Sleeps 2 · Queen bed · Panoramic views · 4×4 required</p>
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
                        </div>''',
    '''<div class="accommodation-card" onclick="openPropertyModal('the-vista')">
                    <div class="accommodation-image vista has-image">
                        🪺
                        <span class="accommodation-badge">Hillside Cabin</span>
                    </div>
                    <div class="accommodation-content">
                        <span class="zone-tag escape-ridge">Escape Ridge</span>
                        <h3 class="accommodation-name">El Nido</h3>
                        <p class="accommodation-tagline">Circular hillside cabin · Sleeps 1 (couples welcome) · 4×4 required</p>
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
                        </div>'''
)

print("[OK] Swapped the-vista card: La Vista → El Nido")

# Card for the-nido: currently says "The Nest" → "La Vista"
html = html.replace(
    '''<div class="accommodation-card" onclick="openPropertyModal('the-nido')">
                    <div class="accommodation-image nido has-image">
                        🪺
                        <span class="accommodation-badge">Hillside Cabin</span>
                    </div>
                    <div class="accommodation-content">
                        <span class="zone-tag escape-ridge">Escape Ridge</span>
                        <h3 class="accommodation-name">The Nest</h3>
                        <p class="accommodation-tagline">Circular hillside cabin · Sleeps 1 (couples welcome) · 4×4 required</p>''',
    '''<div class="accommodation-card" onclick="openPropertyModal('the-nido')">
                    <div class="accommodation-image nido has-image">
                        🏔️
                        <span class="accommodation-badge">Panoramic Views</span>
                    </div>
                    <div class="accommodation-content">
                        <span class="zone-tag escape-ridge">Escape Ridge</span>
                        <h3 class="accommodation-name">La Vista</h3>
                        <p class="accommodation-tagline">Circular hilltop cabin · Sleeps 2 · Queen bed · Panoramic views · 4×4 required</p>'''
)

print("[OK] Swapped the-nido card: The Nest → La Vista")

# Now swap the pricing in the-nido card (currently $115/$690/$1,900 → $150/$900/$2,400)
# Find the pricing block after the-nido card's tagline
# The the-nido pricing section - need to find it after "La Vista" (the newly renamed card)
# Since the-nido card now says "La Vista", find pricing after that specific card
nido_card_pos = html.find("openPropertyModal('the-nido')")
if nido_card_pos > 0:
    # Find the pricing section after this card
    pricing_start = html.find('<div class="accommodation-pricing">', nido_card_pos)
    pricing_end = html.find('</div>\n                        </div>', pricing_start) + len('</div>\n                        </div>')
    old_pricing = html[pricing_start:pricing_end]

    # Check what prices are currently there
    if '$115' in old_pricing:
        new_pricing = old_pricing.replace('$115', '$150').replace('$690', '$900').replace('$1,900', '$2,400')
        html = html[:pricing_start] + new_pricing + html[pricing_end:]
        print("[OK] Updated the-nido card prices: $115/$690/$1,900 → $150/$900/$2,400")
    else:
        print("[SKIP] the-nido prices already look correct")

# ─────────────────────────────────────────────────────
# 3. UPDATE TEXT REFERENCES
# ─────────────────────────────────────────────────────

# "La Vista and The Nest both sit on Escape Ridge" → "El Nido and La Vista both sit on Escape Ridge"
html = html.replace(
    "La Vista and The Nest both sit on Escape Ridge",
    "El Nido and La Vista both sit on Escape Ridge"
)

# "4×4 is required for Escape Ridge cabins</strong> (La Vista & The Nest)"
html = html.replace(
    "(La Vista &amp; The Nest)",
    "(El Nido &amp; La Vista)"
)
html = html.replace(
    "(La Vista & The Nest)",
    "(El Nido & La Vista)"
)

# "Escape Ridge (La Vista & The Nest):"
html = html.replace(
    "Escape Ridge (La Vista &amp; The Nest):",
    "Escape Ridge (El Nido &amp; La Vista):"
)
html = html.replace(
    "Escape Ridge (La Vista & The Nest):",
    "Escape Ridge (El Nido & La Vista):"
)

print("[OK] Updated text references")

# ─────────────────────────────────────────────────────
# 4. REMOVE DUPLICATE IMAGES FROM GALLERY ARRAYS
# ─────────────────────────────────────────────────────
# The numbered files (1-14) are duplicates of subfolder files.
# main.avif = 1.avif = Exterior/xxx.avif (triple!)
# Keep numbered files, remove subfolder duplicates that match them.

# For the-vista: remove subfolder paths that are duplicates of numbered images
# Duplicates identified by md5:
# main.avif = 1.avif = Exterior/3a030245... → remove Exterior/3a030245 (keep main + 1)
# Actually main.avif = 1.avif, so also remove main.avif (keep 1.avif as first)
# Wait, the array starts with main.avif, then 1.avif... both identical.
# Let's remove main.avif and keep 1.avif at top. Then remove subfolder dupes.

vista_dupes_to_remove = [
    "      '/images/accommodations/the-vista/main.avif',\n",
    "      '/images/accommodations/the-vista/Bathroom/07cc87e6-3fd7-4863-9c64-b081a8143a6c.avif',\n",
    "      '/images/accommodations/the-vista/Addnl Photos/213fb231-2b95-40fc-9a87-bc48b50629d3.avif',\n",
    "      '/images/accommodations/the-vista/Exterior/3a030245-1a66-4178-b87a-14ce0502f456.avif',\n",
    "      '/images/accommodations/the-vista/Exterior/3ca1a90c-11cd-4660-8942-013aa1a78701.avif',\n",
    "      '/images/accommodations/the-vista/Addnl Photos/44f72091-b939-4bb7-a15d-598d48af9e59.avif'\n",
]

# Need to handle the last item (no trailing comma)
for dupe in vista_dupes_to_remove:
    if dupe in html:
        html = html.replace(dupe, "")

# Also handle last line variant (with/without comma)
html = html.replace(
    "      '/images/accommodations/the-vista/Addnl Photos/44f72091-b939-4bb7-a15d-598d48af9e59.avif'",
    ""
)

# Clean up any trailing comma before ]
html = re.sub(r",\s*\n\s*\n*\s*\]", "\n    ]", html)

print("[OK] Removed duplicate the-vista gallery images")

nido_dupes_to_remove = [
    "      '/images/accommodations/the-nido/main.avif',\n",
    "      '/images/accommodations/the-nido/Bedroom/07082c87-c76c-44fd-b2f1-ba14b6de15a4.avif',\n",
    "      '/images/accommodations/the-nido/Exterior/0d30c2b1-30a4-47d3-b8dd-442b027ea0c9.avif',\n",
    "      '/images/accommodations/the-nido/Additional Photos/3828a3ad-6d3c-4e27-8c93-197dbe790169.avif',\n",
    "      '/images/accommodations/the-nido/Additional Photos/432efc47-678d-4164-943b-333975c883e8.avif',\n",
    "      '/images/accommodations/the-nido/Exterior/436bc5b6-c05b-4a84-b482-c6c3e0a64ed7.avif'\n",
]

for dupe in nido_dupes_to_remove:
    if dupe in html:
        html = html.replace(dupe, "")

html = html.replace(
    "      '/images/accommodations/the-nido/Exterior/436bc5b6-c05b-4a84-b482-c6c3e0a64ed7.avif'",
    ""
)

# Clean up again
html = re.sub(r",\s*\n\s*\n*\s*\]", "\n    ]", html)

print("[OK] Removed duplicate the-nido gallery images")

# ─────────────────────────────────────────────────────
# 5. WRITE BACK
# ─────────────────────────────────────────────────────
with open(FILE, "w") as f:
    f.write(html)

print("\n✓ All changes written to", FILE)
