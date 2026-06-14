#!/usr/bin/env python3
"""
Final cleanup:
1. The Nest: Sleeps 1 (couples welcome), single bed
2. La Vista: Sleeps 2, queen bed
3. Partners page: update all old names, remove Hearth House row
4. Update example bookings on partners page
"""
import re

# ============================================================
# 1. Fix index.html - The Nest and La Vista taglines
# ============================================================
INDEX = "/opt/fpai/apps/zen-village/frontend/public/index.html"
with open(INDEX, "r") as f:
    html = f.read()

# The Nest card tagline
html = html.replace(
    "Circular hillside cabin · Sleeps 2 · Deep solitude · 4×4 required",
    "Circular hillside cabin · Sleeps 1 (couples welcome) · 4×4 required")

# The Nest JS description
html = html.replace(
    "desc: 'A cozy circular hillside cabin offering solitude and stunning views. The perfect nest for writers, artists, or anyone seeking deep retreat. 4x4 vehicle required.',",
    "desc: 'A cozy circular hillside cabin with a single bed, offering solitude and stunning views. The perfect nest for solo travelers, writers, or couples seeking deep retreat. 4x4 vehicle required.',")

# La Vista card tagline
html = html.replace(
    "Circular hilltop cabin · Sleeps 2 · Panoramic views · 4×4 required",
    "Circular hilltop cabin · Sleeps 2 · Queen bed · Panoramic views · 4×4 required")

# La Vista JS description
html = html.replace(
    "desc: 'A circular hilltop cabin perched on the hillside with breathtaking panoramic views over the valley. Features a spacious deck perfect for sunrise meditation and evening stargazing. 4x4 vehicle required.',",
    "desc: 'A circular hilltop cabin with queen bed, perched on the hillside with breathtaking panoramic views over the valley. Features a spacious deck perfect for sunrise meditation and stargazing. 4x4 vehicle required.',")

with open(INDEX, "w") as f:
    f.write(html)
print("✅ Updated index.html: The Nest (sleeps 1, couples welcome) + La Vista (sleeps 2, queen bed)")


# ============================================================
# 2. Fix partners.html - all name updates + remove Hearth House
# ============================================================
PARTNERS = "/opt/fpai/apps/zen-village/frontend/public/partners.html"
with open(PARTNERS, "r") as f:
    p = f.read()

# Rename properties
p = p.replace("Astro Alpha", "Sky Lily Zome")
p = p.replace("Astro Sol</span>", "Astro Sol Zome</span>")
# Be careful not to double-replace if "Astro Sol Zome" already exists
p = p.replace("Astro Sol Zome Zome", "Astro Sol Zome")

p = p.replace("The Vista", "La Vista")
p = p.replace("The Nido", "The Nest")

# Fix zone descriptions for renamed properties
p = p.replace("Two-story zome", "Zome")

# Remove The Hearth House row from partner table
hearth_row = """                        <tr>
                            <td><span class="acc-name">The Hearth House</span><span class="acc-zone">Village Heart • Communal home</span></td>
                            <td class="guest-price">$91</td>
                            <td class="earn-price">$13</td>
                            <td class="guest-price">$546</td>
                            <td class="earn-price">$78</td>
                            <td class="guest-price">$1,540</td>
                            <td class="earn-price">$220</td>
                        </tr>"""
if hearth_row in p:
    p = p.replace(hearth_row, "")
    print("✅ Removed Hearth House from partners table")
else:
    print("⚠️  Hearth House row not found in partners page (may already be removed)")

# Update example booking to use Sky Lily Zome instead of Astro Alpha
p = p.replace("5 nights @ Sky Lily Zome", "5 nights @ Sky Lily Zome")  # already renamed above
p = p.replace("1 week @ La Vista", "1 week @ La Vista")  # already renamed above

# Fix any "The Nest" zone description
p = p.replace("Escape Ridge • Hillside cabin", "Escape Ridge • Circular hillside cabin")
p = p.replace("Escape Ridge • Panoramic views", "Escape Ridge • Circular hilltop cabin")

with open(PARTNERS, "w") as f:
    f.write(p)

# Verify partners page
for old_name in ["Astro Alpha", "The Vista", "The Nido", "Hearth House"]:
    count = p.count(old_name)
    if count > 0:
        print(f"  ⚠️  '{old_name}' still appears {count} times in partners.html")
    else:
        print(f"  ✅ '{old_name}' removed from partners.html")

for new_name in ["Sky Lily Zome", "Astro Sol Zome", "La Vista", "The Nest"]:
    count = p.count(new_name)
    print(f"  '{new_name}': {count} occurrences")

print("\n✅ Partners page updated")
