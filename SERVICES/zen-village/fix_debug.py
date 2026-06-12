#!/usr/bin/env python3
"""Add console.log debugging and try-catch to trace the issue."""

INDEX = "/opt/fpai/apps/zen-village/frontend/public/index.html"
with open(INDEX, 'r') as f:
    html = f.read()

# Add debugging to updateCardPrices
old = "function updateCardPrices() {"
new = """function updateCardPrices() {
  console.log('[ZV] updateCardPrices called, season:', getCurrentSeason());
  try {"""

if old in html:
    html = html.replace(old, new, 1)

# Close try-catch at end of function
old2 = """  var indicator = document.getElementById('season-indicator');
  if (indicator) {
    indicator.className = 'season-indicator ' + season;
    if (season === 'green') {
      indicator.innerHTML = '🌿 <strong>Green Season Rates</strong> (May\\u2013Nov) \\u2014 Enjoy 15% off all accommodations!';
    } else {
      indicator.innerHTML = '☀️ <strong>High Season Rates</strong> (Dec\\u2013Apr) \\u2014 Peak season pricing in effect';
    }
  }
}"""

new2 = """  var indicator = document.getElementById('season-indicator');
  console.log('[ZV] indicator element:', indicator);
  if (indicator) {
    indicator.className = 'season-indicator ' + season;
    if (season === 'green') {
      indicator.innerHTML = '🌿 <strong>Green Season Rates</strong> (May–Nov) — Enjoy 15% off all accommodations!';
    } else {
      indicator.innerHTML = '☀️ <strong>High Season Rates</strong> (Dec–Apr) — Peak season pricing in effect';
    }
    console.log('[ZV] indicator updated:', indicator.innerHTML);
  }
  } catch(e) { console.error('[ZV] updateCardPrices error:', e); }
}"""

if old2 in html:
    html = html.replace(old2, new2)
    print("✅ Added debugging to updateCardPrices")
else:
    print("⚠️  Could not find exact match for old2, trying without unicode")
    # The unicode chars might be the issue - try with actual chars
    old3 = html[html.find("var indicator = document.getElementById('season-indicator')"):html.find("}\n\n// Run on page load")+1]
    if old3:
        print(f"Found block: {old3[:100]}...")

with open(INDEX, 'w') as f:
    f.write(html)
print("Done")
