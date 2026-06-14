#!/usr/bin/env python3
"""
Comprehensive update:
1. Add seasonal pricing to index.html (auto-switches based on date)
   - High Season: Dec 1 - Apr 30 (full retail)
   - Green Season: May 1 - Nov 30 (15% off)
2. Cards show dynamic pricing with season badge
3. Gallery modals show dynamic pricing
4. Update partners page: 30% → 20% discount + seasonal pricing tables
5. Update booking.html with seasonal awareness
"""
import re
import math

INDEX = "/opt/fpai/apps/zen-village/frontend/public/index.html"
PARTNERS = "/opt/fpai/apps/zen-village/frontend/public/partners.html"
BOOKING = "/opt/fpai/apps/zen-village/frontend/public/booking.html"

# High season base prices (what's currently on the site)
PROPERTIES = {
    'sky-lily-zome':    {'key': 'astro-alpha', 'name': 'Sky Lily Zome',    'night': 130, 'week': 780, 'month': 2200},
    'astro-sol-zome':   {'key': 'astro-sol',   'name': 'Astro Sol Zome',   'night': 130, 'week': 780, 'month': 2200},
    'green-casita':     {'key': 'green-casita', 'name': 'Green Casita',     'night': 95,  'week': 570, 'month': 1600},
    'glamp-grove':      {'key': 'glamp-grove',  'name': 'Glamp Grove',      'night': 45,  'week': 270, 'month': 800},
    'camp-spring':      {'key': 'camp-spring',  'name': 'Camp Spring',      'night': 20,  'week': 120, 'month': 350},
    'riverlight':       {'key': 'riverlight',   'name': 'Riverlight Cabin', 'night': 120, 'week': 720, 'month': 2000},
    'zen-casa':         {'key': 'zen-casa',     'name': 'Zen Casa (3BR)',   'night': 180, 'week': 1080,'month': 3200},
    'la-vista':         {'key': 'the-vista',    'name': 'La Vista',         'night': 150, 'week': 900, 'month': 2400},
    'the-nest':         {'key': 'the-nido',     'name': 'The Nest',         'night': 115, 'week': 690, 'month': 1900},
}

GREEN_DISCOUNT = 0.15  # 15% off in green season
PARTNER_DISCOUNT = 0.20  # 20% partner discount (changed from 30%)

def green_price(base):
    return round(base * (1 - GREEN_DISCOUNT))

def partner_price(base):
    return round(base * (1 - PARTNER_DISCOUNT), 2)

def commission(base):
    return round(base * 0.10, 2)

def fmt(n):
    if n >= 1000:
        return f"${n:,.0f}" if n == int(n) else f"${n:,.2f}"
    return f"${n:.0f}" if n == int(n) else f"${n:.2f}"


# ============================================================
# 1. UPDATE index.html - Add seasonal pricing JavaScript
# ============================================================
with open(INDEX, 'r') as f:
    html = f.read()

# Add the seasonal pricing engine right before the propertyData declaration
SEASON_JS = """
// ===== SEASONAL PRICING ENGINE =====
const SEASON_CONFIG = {
  greenDiscount: 0.15,
  highSeasonMonths: [12, 1, 2, 3, 4],  // Dec-Apr
  greenSeasonMonths: [5, 6, 7, 8, 9, 10, 11]  // May-Nov
};

function getCurrentSeason() {
  const month = new Date().getMonth() + 1;
  return SEASON_CONFIG.highSeasonMonths.includes(month) ? 'high' : 'green';
}

function getSeasonLabel() {
  return getCurrentSeason() === 'high' ? 'High Season' : 'Green Season';
}

function getSeasonPrice(basePrice) {
  if (getCurrentSeason() === 'green') {
    return Math.round(basePrice * (1 - SEASON_CONFIG.greenDiscount));
  }
  return basePrice;
}

function formatPrice(n) {
  return n >= 1000 ? '$' + n.toLocaleString() : '$' + n;
}
// ===== END SEASONAL PRICING =====

"""

# Insert before propertyData
if '// ===== SEASONAL PRICING ENGINE =====' not in html:
    html = html.replace(
        "const propertyData = {",
        SEASON_JS + "const propertyData = {"
    )
    print("✅ Added seasonal pricing JS engine")
else:
    print("⚠️  Seasonal pricing JS already exists, skipping")

# Now update propertyData to include both high and green prices
# Add highPrices and greenPrices to each property
for slug, p in PROPERTIES.items():
    key = p['key']
    old_prices = f"prices: {{ night: {p['night']}, week: {p['week']}, month: {p['month']} }}"
    gn = green_price(p['night'])
    gw = green_price(p['week'])
    gm = green_price(p['month'])
    new_prices = (
        f"highPrices: {{ night: {p['night']}, week: {p['week']}, month: {p['month']} }},\n"
        f"    greenPrices: {{ night: {gn}, week: {gw}, month: {gm} }},\n"
        f"    get prices() {{ return getCurrentSeason() === 'green' ? this.greenPrices : this.highPrices; }}"
    )
    if old_prices in html:
        html = html.replace(old_prices, new_prices, 1)

print("✅ Updated propertyData with seasonal pricing (high + green)")

# Update the openPropertyModal function to show season info
old_modal_func = """document.getElementById('modal-price-night').textContent = '$' + property.prices.night;
  document.getElementById('modal-price-week').textContent = '$' + property.prices.week;
  document.getElementById('modal-price-month').textContent = '$' + property.prices.month;"""

new_modal_func = """const prices = property.prices;
  document.getElementById('modal-price-night').textContent = '$' + prices.night;
  document.getElementById('modal-price-week').textContent = '$' + prices.week;
  document.getElementById('modal-price-month').textContent = '$' + prices.month;
  
  // Show season badge
  const seasonEl = document.getElementById('modal-season-badge');
  if (seasonEl) {
    const season = getCurrentSeason();
    seasonEl.textContent = season === 'green' ? '🌿 Green Season — 15% Off' : '☀️ High Season Rates';
    seasonEl.className = 'season-badge ' + season;
  }"""

if old_modal_func in html:
    html = html.replace(old_modal_func, new_modal_func)
    print("✅ Updated modal to show season badge")

# Add season badge element to modal HTML
old_modal_pricing = '<div class="modal-pricing">'
new_modal_pricing = '<div id="modal-season-badge" class="season-badge"></div>\n      <div class="modal-pricing">'
if 'modal-season-badge' not in html:
    html = html.replace(old_modal_pricing, new_modal_pricing, 1)
    print("✅ Added season badge to modal")

# Add season badge CSS
season_css = """
/* Season Badge Styles */
.season-badge {
  display: inline-block;
  padding: 0.4rem 1rem;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: 1rem;
  text-align: center;
}
.season-badge.high {
  background: linear-gradient(135deg, #c4a35a, #d4956a);
  color: #1a2e1a;
}
.season-badge.green {
  background: linear-gradient(135deg, #4a6741, #7d9a6f);
  color: #faf9f5;
}
.season-indicator {
  text-align: center;
  margin-bottom: 2rem;
  padding: 0.8rem 1.5rem;
  border-radius: 12px;
  font-weight: 500;
  font-size: 0.95rem;
}
.season-indicator.high {
  background: linear-gradient(135deg, rgba(196,163,90,0.15), rgba(212,149,106,0.15));
  color: #8a6d2f;
  border: 1px solid rgba(196,163,90,0.3);
}
.season-indicator.green {
  background: linear-gradient(135deg, rgba(74,103,65,0.15), rgba(125,154,111,0.15));
  color: #3a5a30;
  border: 1px solid rgba(74,103,65,0.3);
}
"""

# Insert CSS before the closing </style> right before the script
style_end_idx = html.find('</style>\n\n<script>')
if style_end_idx > 0 and 'season-badge' not in html[:style_end_idx]:
    html = html[:style_end_idx] + season_css + html[style_end_idx:]
    print("✅ Added season badge CSS")

# Add a season indicator banner above the accommodations section
# and auto-update card prices on page load
CARD_UPDATE_JS = """

// Auto-update card prices based on current season
function updateCardPrices() {
  const season = getCurrentSeason();
  const cards = document.querySelectorAll('.accommodation-card');
  
  cards.forEach(card => {
    const onclick = card.getAttribute('onclick');
    if (!onclick) return;
    const match = onclick.match(/openPropertyModal\\('([^']+)'\\)/);
    if (!match) return;
    const propId = match[1];
    const prop = propertyData[propId];
    if (!prop) return;
    
    const prices = prop.prices;
    const priceItems = card.querySelectorAll('.price-item .amount');
    if (priceItems.length >= 3) {
      priceItems[0].textContent = '$' + prices.night.toLocaleString();
      priceItems[1].textContent = '$' + prices.week.toLocaleString();
      priceItems[2].textContent = '$' + prices.month.toLocaleString();
    }
  });
  
  // Update season indicator
  const indicator = document.getElementById('season-indicator');
  if (indicator) {
    indicator.className = 'season-indicator ' + season;
    if (season === 'green') {
      indicator.innerHTML = '🌿 <strong>Green Season Rates</strong> (May–Nov) — Enjoy 15% off all accommodations!';
    } else {
      indicator.innerHTML = '☀️ <strong>High Season Rates</strong> (Dec–Apr) — Peak season pricing in effect';
    }
  }
}

// Run on page load
document.addEventListener('DOMContentLoaded', updateCardPrices);
"""

# Add card update JS before the closing </script>
# Find the last </script> in the main script block
if 'updateCardPrices' not in html:
    # Insert before the route switching function
    html = html.replace(
        "// Getting Here - Route tab switching",
        CARD_UPDATE_JS + "\n        // Getting Here - Route tab switching"
    )
    print("✅ Added auto card price update JS")

# Add season indicator div above the accommodations grid
season_indicator_html = '        <div id="season-indicator" class="season-indicator"></div>\n'
if 'season-indicator' not in html:
    # Insert just before the first zone section
    html = html.replace(
        '<!-- Village Heart Zone -->',
        season_indicator_html + '        <!-- Village Heart Zone -->'
    )
    print("✅ Added season indicator banner")

with open(INDEX, 'w') as f:
    f.write(html)
print("✅ Saved index.html\n")


# ============================================================
# 2. UPDATE partners.html - 20% discount + seasonal tables
# ============================================================
with open(PARTNERS, 'r') as f:
    p_html = f.read()

# Update the header banner: 30% → 20%
p_html = p_html.replace(
    "<div style=\"font-size: 2.5rem; font-weight: 700;\">30%</div>",
    "<div style=\"font-size: 2.5rem; font-weight: 700;\">20%</div>"
)
p_html = p_html.replace(
    "Commission is 10% of the <strong>base rate</strong> (before discount). Paid after guest completes their stay.",
    "Commission is 10% of the <strong>base rate</strong> (before discount). Paid after guest completes their stay. Rates vary by season — High Season (Dec–Apr) and Green Season (May–Nov, 15% lower base)."
)
print("✅ Updated partner header: 30% → 20%")

# Replace the entire Cabins & Structures pricing table
# First, define the new table data
cabins = [
    ('La Vista',         'Escape Ridge • Circular hilltop cabin', 150, 900, 2400),
    ('Sky Lily Zome',    'Village Heart • Zome',                  130, 780, 2200),
    ('Astro Sol Zome',   'Village Heart • Zome',                  130, 780, 2200),
    ('Riverlight Cabin', 'River Grove • Riverside',               120, 720, 2000),
    ('The Nest',         'Escape Ridge • Circular hillside cabin', 115, 690, 1900),
    ('Green Casita',     'Village Heart • Near Singing Dome',      95,  570, 1600),
    ('Zen Casa (3BR)',   'River Grove • Spacious home',           180, 1080, 3200),
]

camping = [
    ('Glamp Grove',  'Equipped glamping tent', True,   45, 270, 800),
    ('Camp Spring',  'Bring your own tent',    False,  20, 120, 350),
]

def build_cabin_rows(properties, discount=0.20):
    rows = ""
    for name, zone, n, w, m in properties:
        # High season partner prices
        hp_n = round(n * (1 - discount), 2)
        hp_w = round(w * (1 - discount), 2)
        hp_m = round(m * (1 - discount), 2)
        # Green season base
        gn = green_price(n)
        gw = green_price(w)
        gm = green_price(m)
        # Green season partner prices
        gp_n = round(gn * (1 - discount), 2)
        gp_w = round(gw * (1 - discount), 2)
        gp_m = round(gm * (1 - discount), 2)
        # Commission (10% of base, varies by season)
        c_n_h = round(n * 0.10, 2)
        c_w_h = round(w * 0.10, 2)
        c_m_h = round(m * 0.10, 2)
        c_n_g = round(gn * 0.10, 2)
        c_w_g = round(gw * 0.10, 2)
        c_m_g = round(gm * 0.10, 2)
        
        def f(v):
            if v == int(v): return f"${int(v)}"
            return f"${v:.2f}"
        def fc(v):
            if v >= 1000: return f"${v:,.0f}" if v == int(v) else f"${v:,.2f}"
            return f(v)
        
        rows += f"""                        <tr>
                            <td><span class="acc-name">{name}</span><span class="acc-zone">{zone}</span></td>
                            <td class="guest-price">{fc(hp_n)}</td>
                            <td class="earn-price">{f(c_n_h)}</td>
                            <td class="guest-price">{fc(gp_n)}</td>
                            <td class="earn-price">{f(c_n_g)}</td>
                            <td class="guest-price">{fc(hp_w)}</td>
                            <td class="earn-price">{f(c_w_h)}</td>
                            <td class="guest-price">{fc(gp_w)}</td>
                            <td class="earn-price">{f(c_w_g)}</td>
                        </tr>
"""
    return rows

# Build the new pricing section
new_pricing_section = """            <!-- Cabins & Structures -->
            <div class="pricing-card">
                <h3>🏡 Cabins & Structures — Nightly Rates</h3>
                <p class="subtitle">20% partner discount applied — Guest pays discounted rate, you earn 10% commission on BASE rate</p>
                
                <table class="partner-table">
                    <thead>
                        <tr>
                            <th rowspan="2" style="vertical-align: bottom;">Accommodation</th>
                            <th colspan="2" style="border-bottom: 1px solid rgba(255,255,255,0.2);">☀️ High Season<br><small>Dec–Apr</small></th>
                            <th colspan="2" style="border-bottom: 1px solid rgba(255,255,255,0.2);">🌿 Green Season<br><small>May–Nov</small></th>
                        </tr>
                        <tr>
                            <th>Guest Pays</th>
                            <th class="earn-col">You Earn</th>
                            <th>Guest Pays</th>
                            <th class="earn-col">You Earn</th>
                        </tr>
                    </thead>
                    <tbody>
"""

for name, zone, n, w, m in cabins:
    gn = green_price(n)
    hp = round(n * 0.80, 2)
    gp = round(gn * 0.80, 2)
    c_h = round(n * 0.10, 2)
    c_g = round(gn * 0.10, 2)
    
    def f(v):
        if v == int(v): return f"${int(v)}"
        return f"${v:.2f}"
    
    new_pricing_section += f"""                        <tr>
                            <td><span class="acc-name">{name}</span><span class="acc-zone">{zone}</span></td>
                            <td class="guest-price">{f(hp)}/nt</td>
                            <td class="earn-price">{f(c_h)}/nt</td>
                            <td class="guest-price">{f(gp)}/nt</td>
                            <td class="earn-price">{f(c_g)}/nt</td>
                        </tr>
"""

new_pricing_section += """                    </tbody>
                </table>
                
                <div style="margin-top: 1.5rem; display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div style="background: var(--zen-cloud); border-radius: 12px; padding: 1.25rem;">
                        <h4 style="font-size: 0.95rem; color: var(--zen-forest-deep); margin-bottom: 0.75rem;">☀️ High Season Weekly/Monthly</h4>
                        <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
"""

for name, zone, n, w, m in cabins:
    wp = round(w * 0.80)
    mp = round(m * 0.80)
    new_pricing_section += f'                            <tr><td style="padding: 0.3rem 0; font-weight: 500;">{name}</td><td style="text-align:right">${wp:,}/wk</td><td style="text-align:right">${mp:,}/mo</td></tr>\n'

new_pricing_section += """                        </table>
                    </div>
                    <div style="background: var(--zen-cloud); border-radius: 12px; padding: 1.25rem;">
                        <h4 style="font-size: 0.95rem; color: var(--zen-forest-deep); margin-bottom: 0.75rem;">🌿 Green Season Weekly/Monthly</h4>
                        <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
"""

for name, zone, n, w, m in cabins:
    gw = green_price(w)
    gm = green_price(m)
    gwp = round(gw * 0.80)
    gmp = round(gm * 0.80)
    new_pricing_section += f'                            <tr><td style="padding: 0.3rem 0; font-weight: 500;">{name}</td><td style="text-align:right">${gwp:,}/wk</td><td style="text-align:right">${gmp:,}/mo</td></tr>\n'

new_pricing_section += """                        </table>
                    </div>
                </div>
            </div>"""

# Replace the old Cabins & Structures section
old_section_start = '            <!-- Cabins & Structures -->'
old_section_end = '            <!-- Camping Options -->'
start_idx = p_html.find(old_section_start)
end_idx = p_html.find(old_section_end)
if start_idx >= 0 and end_idx >= 0:
    p_html = p_html[:start_idx] + new_pricing_section + "\n            \n            " + p_html[end_idx:]
    print("✅ Replaced cabins pricing table with seasonal version")

# Update camping section: 30% → 20%
p_html = p_html.replace(
    '<span style="background: var(--zen-gold); color: var(--zen-forest-deep); padding: 0.2rem 0.5rem; border-radius: 8px; font-size: 0.75rem; font-weight: 600;">30% OFF</span>',
    '<span style="background: var(--zen-gold); color: var(--zen-forest-deep); padding: 0.2rem 0.5rem; border-radius: 8px; font-size: 0.75rem; font-weight: 600;">20% OFF</span>'
)

# Update camping prices for Glamp Grove (20% discount instead of 30%)
# Old: $31.50 (45*0.7), new: $36 (45*0.8)
p_html = p_html.replace('$31.50', '$36')
p_html = p_html.replace('$4.50', '$4.50')  # Commission stays same
p_html = p_html.replace('$189', '$216')  # Weekly: 270*0.8
p_html = p_html.replace('$27', '$27')  # Weekly commission stays
p_html = p_html.replace('$560', '$640')  # Monthly: 800*0.8
p_html = p_html.replace('$80', '$80')  # Monthly commission stays

print("✅ Updated camping prices: 30% → 20%")

# Update subtitle text
p_html = p_html.replace(
    '30% partner discount applied',
    '20% partner discount applied'
)
p_html = p_html.replace(
    "30% partner discount",
    "20% partner discount"
)
p_html = p_html.replace(
    "Guest completes payment with the 30% partner discount applied.",
    "Guest completes payment with the 20% partner discount applied."
)
p_html = p_html.replace(
    "you'll get 30% off",
    "you'll get 20% off"
)
p_html = p_html.replace(
    "30% discount available for guests",
    "20% discount available for guests"
)
p_html = p_html.replace(
    "30% discount",
    "20% discount"
)
print("✅ Updated all 30% references to 20%")

# Update example bookings with new 20% discount math
# Sky Lily Zome: 5 nights, high season: $130 * 0.8 = $104/night, total $520, commission 5*$13 = $65
old_example1 = """<div class="example-box">
                        <div class="label">5 nights @ Sky Lily Zome</div>
                        <div class="amount">Guest: $455</div>
                        <div class="calc">5 × $91/night</div>
                    </div>
                    <div class="example-box earn">
                        <div class="label">You earn</div>
                        <div class="amount">$65</div>
                        <div class="calc">5 × $13/night</div>
                    </div>"""

new_example1 = """<div class="example-box">
                        <div class="label">5 nights @ Sky Lily Zome (High Season)</div>
                        <div class="amount">Guest: $520</div>
                        <div class="calc">5 × $104/night</div>
                    </div>
                    <div class="example-box earn">
                        <div class="label">You earn</div>
                        <div class="amount">$65</div>
                        <div class="calc">5 × $13/night</div>
                    </div>"""

p_html = p_html.replace(old_example1, new_example1)

# La Vista: 1 week, high season: $900 * 0.8 = $720, commission $90
old_example2 = """<div class="example-box">
                        <div class="label">1 week @ La Vista</div>
                        <div class="amount">Guest: $630</div>
                        <div class="calc">Weekly rate</div>
                    </div>
                    <div class="example-box earn">
                        <div class="label">You earn</div>
                        <div class="amount">$90</div>
                        <div class="calc">10% of $900 base</div>
                    </div>"""

new_example2 = """<div class="example-box">
                        <div class="label">1 week @ La Vista (High Season)</div>
                        <div class="amount">Guest: $720</div>
                        <div class="calc">Weekly rate (20% off $900)</div>
                    </div>
                    <div class="example-box earn">
                        <div class="label">You earn</div>
                        <div class="amount">$90</div>
                        <div class="calc">10% of $900 base</div>
                    </div>"""

p_html = p_html.replace(old_example2, new_example2)

# Green Casita: 1 month, green season: base $1360 (1600*0.85), partner: $1360*0.8=$1088, commission $136
old_example3 = """<div class="example-box">
                        <div class="label">1 month @ Green Casita</div>
                        <div class="amount">Guest: $1,120</div>
                        <div class="calc">Monthly rate</div>
                    </div>
                    <div class="example-box earn">
                        <div class="label">You earn</div>
                        <div class="amount">$160</div>
                        <div class="calc">10% of $1,600 base</div>
                    </div>"""

new_example3 = """<div class="example-box">
                        <div class="label">1 month @ Green Casita (Green Season)</div>
                        <div class="amount">Guest: $1,088</div>
                        <div class="calc">Monthly rate (20% off $1,360 green base)</div>
                    </div>
                    <div class="example-box earn">
                        <div class="label">You earn</div>
                        <div class="amount">$136</div>
                        <div class="calc">10% of $1,360 green base</div>
                    </div>"""

p_html = p_html.replace(old_example3, new_example3)

# Add seasonal info note at top of pricing section
season_note = """
            <div style="background: linear-gradient(135deg, rgba(74,103,65,0.1), rgba(196,163,90,0.1)); border-radius: 16px; padding: 1.5rem; margin-bottom: 2rem; border: 1px solid rgba(74,103,65,0.2);">
                <div style="display: flex; gap: 2rem; justify-content: center; flex-wrap: wrap; text-align: center;">
                    <div>
                        <div style="font-size: 1.2rem; font-weight: 600;">☀️ High Season</div>
                        <div style="font-size: 0.9rem; color: var(--zen-forest);">December – April</div>
                        <div style="font-size: 0.85rem; color: var(--zen-moss);">Full base rates</div>
                    </div>
                    <div style="font-size: 1.5rem; align-self: center; color: var(--zen-moss);">|</div>
                    <div>
                        <div style="font-size: 1.2rem; font-weight: 600;">🌿 Green Season</div>
                        <div style="font-size: 0.9rem; color: var(--zen-forest);">May – November</div>
                        <div style="font-size: 0.85rem; color: var(--zen-moss);">15% lower base rates</div>
                    </div>
                </div>
                <p style="text-align: center; margin-top: 1rem; font-size: 0.85rem; color: var(--zen-forest);">Partner discount of 20% is applied on top of the seasonal base rate. Your 10% commission is always based on the seasonal base.</p>
            </div>
"""

if 'High Season' not in p_html.split('Partner Pricing')[0] or True:
    # Insert before the cabins section
    insert_point = p_html.find('<!-- Cabins & Structures')
    if insert_point < 0:
        insert_point = p_html.find('🏡 Cabins')
        if insert_point > 0:
            insert_point = p_html.rfind('<div', 0, insert_point)
    if insert_point > 0:
        p_html = p_html[:insert_point] + season_note + "\n            " + p_html[insert_point:]
        print("✅ Added seasonal info card to partners page")

with open(PARTNERS, 'w') as f:
    f.write(p_html)
print("✅ Saved partners.html\n")


# ============================================================
# 3. UPDATE booking.html - seasonal awareness
# ============================================================
if os.path.exists(BOOKING):
    with open(BOOKING, 'r') as f:
        b_html = f.read()
    
    # Add seasonal pricing JS to booking page
    booking_season_js = """
<script>
// Seasonal Pricing
const SEASON_CONFIG = {
  greenDiscount: 0.15,
  highSeasonMonths: [12, 1, 2, 3, 4],
  greenSeasonMonths: [5, 6, 7, 8, 9, 10, 11]
};

function getCurrentSeason() {
  const month = new Date().getMonth() + 1;
  return SEASON_CONFIG.highSeasonMonths.includes(month) ? 'high' : 'green';
}

document.addEventListener('DOMContentLoaded', function() {
  const season = getCurrentSeason();
  const banner = document.createElement('div');
  banner.style.cssText = 'text-align:center;padding:0.75rem;font-weight:500;font-size:0.9rem;';
  if (season === 'green') {
    banner.style.background = 'linear-gradient(135deg, rgba(74,103,65,0.15), rgba(125,154,111,0.15))';
    banner.style.color = '#3a5a30';
    banner.innerHTML = '🌿 <strong>Green Season Rates</strong> (May–Nov) — 15% off all accommodations!';
  } else {
    banner.style.background = 'linear-gradient(135deg, rgba(196,163,90,0.15), rgba(212,149,106,0.15))';
    banner.style.color = '#8a6d2f';
    banner.innerHTML = '☀️ <strong>High Season Rates</strong> (Dec–Apr) in effect';
  }
  const main = document.querySelector('main') || document.querySelector('.booking-content');
  if (main) main.insertBefore(banner, main.firstChild);
});
</script>
"""
    
    if 'getCurrentSeason' not in b_html:
        b_html = b_html.replace('</body>', booking_season_js + '\n</body>')
        print("✅ Added seasonal awareness to booking.html")
    
    # Update any 30% references
    b_html = b_html.replace('30% partner discount', '20% partner discount')
    b_html = b_html.replace('30% off', '20% off')
    
    with open(BOOKING, 'w') as f:
        f.write(b_html)
    print("✅ Saved booking.html")
else:
    print("⚠️  booking.html not found, skipping")

import os
print("\n✅ ALL UPDATES COMPLETE")
print("   - Seasonal pricing engine added to main site")  
print("   - Cards auto-update based on current date")
print("   - Gallery modals show season badge + correct prices")
print("   - Partners page: 20% discount + seasonal tables")
print("   - Booking page: seasonal awareness banner")
