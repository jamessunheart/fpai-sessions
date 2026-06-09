#!/usr/bin/env python3
"""
Fix seasonal pricing: Remove getter syntax, use direct calculation in updateCardPrices.
Also simplify the openPropertyModal to use highPrices/greenPrices directly.
"""
import re

INDEX = "/opt/fpai/apps/zen-village/frontend/public/index.html"
with open(INDEX, 'r') as f:
    html = f.read()

# 1. Remove all "get prices()" getter lines - they can cause issues
html = re.sub(
    r"\n\s*get prices\(\) \{ return getCurrentSeason\(\) === 'green' \? this\.greenPrices : this\.highPrices; \},?",
    "",
    html
)
print(f"Removed {len(re.findall('get prices', html))} remaining getter lines (should be 0)")

# 2. Fix updateCardPrices to read highPrices/greenPrices directly
old_update = """function updateCardPrices() {
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
}"""

new_update = """function getPropertyPrices(prop) {
  if (!prop) return null;
  var season = getCurrentSeason();
  if (season === 'green' && prop.greenPrices) return prop.greenPrices;
  if (prop.highPrices) return prop.highPrices;
  return { night: 0, week: 0, month: 0 };
}

function updateCardPrices() {
  var season = getCurrentSeason();
  var cards = document.querySelectorAll('.accommodation-card');
  
  cards.forEach(function(card) {
    var onclick = card.getAttribute('onclick');
    if (!onclick) return;
    var match = onclick.match(/openPropertyModal\\('([^']+)'\\)/);
    if (!match) return;
    var propId = match[1];
    var prop = propertyData[propId];
    if (!prop) return;
    
    var prices = getPropertyPrices(prop);
    var priceItems = card.querySelectorAll('.price-item .amount');
    if (priceItems.length >= 3) {
      priceItems[0].textContent = '$' + prices.night.toLocaleString();
      priceItems[1].textContent = '$' + prices.week.toLocaleString();
      priceItems[2].textContent = '$' + prices.month.toLocaleString();
    }
  });
  
  var indicator = document.getElementById('season-indicator');
  if (indicator) {
    indicator.className = 'season-indicator ' + season;
    if (season === 'green') {
      indicator.innerHTML = '🌿 <strong>Green Season Rates</strong> (May\\u2013Nov) \\u2014 Enjoy 15% off all accommodations!';
    } else {
      indicator.innerHTML = '☀️ <strong>High Season Rates</strong> (Dec\\u2013Apr) \\u2014 Peak season pricing in effect';
    }
  }
}"""

if old_update in html:
    html = html.replace(old_update, new_update)
    print("✅ Replaced updateCardPrices with direct pricing")
else:
    print("⚠️  Could not find exact updateCardPrices function, trying partial match")
    # Try to find and replace just the function
    idx = html.find('function updateCardPrices()')
    if idx >= 0:
        end_idx = html.find('\n}', idx)
        if end_idx > 0:
            end_idx += 2
            html = html[:idx] + new_update + html[end_idx:]
            print("✅ Replaced updateCardPrices via position")

# 3. Fix openPropertyModal to use getPropertyPrices
old_modal = """const prices = property.prices;
  document.getElementById('modal-price-night').textContent = '$' + prices.night;
  document.getElementById('modal-price-week').textContent = '$' + prices.week;
  document.getElementById('modal-price-month').textContent = '$' + prices.month;"""

new_modal = """var prices = getPropertyPrices(property);
  document.getElementById('modal-price-night').textContent = '$' + prices.night;
  document.getElementById('modal-price-week').textContent = '$' + prices.week;
  document.getElementById('modal-price-month').textContent = '$' + prices.month;"""

if old_modal in html:
    html = html.replace(old_modal, new_modal)
    print("✅ Updated openPropertyModal to use getPropertyPrices")

with open(INDEX, 'w') as f:
    f.write(html)

print("✅ All fixes applied")
