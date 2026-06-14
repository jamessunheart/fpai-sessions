#!/usr/bin/env python3
"""Fix partner page and booking page after name swap."""

# ── Fix partners.html ──
pt = '/opt/fpai/apps/zen-village/frontend/public/partners.html'
with open(pt, 'r') as f:
    content = f.read()

# Nightly rates: El Nido currently shows old La Vista prices, and vice versa
# El Nido (smaller cabin): $115/nt → 20% off = $92/nt high, $98/nt → $78.40 green
# La Vista (bigger cabin): $150/nt → 20% off = $120/nt high, $128/nt → $102.40 green

content = content.replace(
    '<span class="acc-name">El Nido</span><span class="acc-zone">Escape Ridge \u2022 Cozy hillside cabin</span></td>\n                            <td class="guest-price">$120/nt</td>\n                            <td class="earn-price">$15/nt</td>\n                            <td class="guest-price">$102.40/nt</td>\n                            <td class="earn-price">$12.80/nt</td>',
    '<span class="acc-name">El Nido</span><span class="acc-zone">Escape Ridge \u2022 Cozy hillside cabin</span></td>\n                            <td class="guest-price">$92/nt</td>\n                            <td class="earn-price">$11.50/nt</td>\n                            <td class="guest-price">$78.40/nt</td>\n                            <td class="earn-price">$9.80/nt</td>'
)

content = content.replace(
    '<span class="acc-name">La Vista</span><span class="acc-zone">Escape Ridge \u2022 Hilltop cabin with panoramic views</span></td>\n                            <td class="guest-price">$92/nt</td>\n                            <td class="earn-price">$11.50/nt</td>\n                            <td class="guest-price">$78.40/nt</td>\n                            <td class="earn-price">$9.80/nt</td>',
    '<span class="acc-name">La Vista</span><span class="acc-zone">Escape Ridge \u2022 Hilltop cabin with panoramic views</span></td>\n                            <td class="guest-price">$120/nt</td>\n                            <td class="earn-price">$15/nt</td>\n                            <td class="guest-price">$102.40/nt</td>\n                            <td class="earn-price">$12.80/nt</td>'
)

print("[OK] Fixed nightly partner rates")

# Weekly/Monthly tables: there are two La Vista entries, second should be El Nido
# High season: El Nido = $552/wk, $1,520/mo
# Green season: El Nido = $469/wk, $1,292/mo

# High season table
hs_start = content.find('High Season Weekly/Monthly')
hs_end = content.find('</table>', hs_start) + len('</table>')
hs_block = content[hs_start:hs_end]

first_la = hs_block.find('La Vista')
if first_la >= 0:
    second_la = hs_block.find('La Vista', first_la + 10)
    if second_la >= 0:
        tr_start = hs_block.rfind('<tr>', 0, second_la)
        tr_end = hs_block.find('</tr>', second_la) + 5
        old_row = hs_block[tr_start:tr_end]
        new_row = '<tr><td style="padding: 0.3rem 0; font-weight: 500;">El Nido</td><td style="text-align:right">$552/wk</td><td style="text-align:right">$1,520/mo</td></tr>'
        new_hs_block = hs_block[:tr_start] + new_row + hs_block[tr_end:]
        content = content.replace(hs_block, new_hs_block, 1)
        print("[OK] Fixed high season weekly/monthly: second La Vista → El Nido")

# Green season table
gs_start = content.find('Green Season Weekly/Monthly')
gs_end = content.find('</table>', gs_start) + len('</table>')
gs_block = content[gs_start:gs_end]

first_la = gs_block.find('La Vista')
if first_la >= 0:
    second_la = gs_block.find('La Vista', first_la + 10)
    if second_la >= 0:
        tr_start = gs_block.rfind('<tr>', 0, second_la)
        tr_end = gs_block.find('</tr>', second_la) + 5
        old_row = gs_block[tr_start:tr_end]
        new_row = '<tr><td style="padding: 0.3rem 0; font-weight: 500;">El Nido</td><td style="text-align:right">$469/wk</td><td style="text-align:right">$1,292/mo</td></tr>'
        new_gs_block = gs_block[:tr_start] + new_row + gs_block[tr_end:]
        content = content.replace(gs_block, new_gs_block, 1)
        print("[OK] Fixed green season weekly/monthly: second La Vista → El Nido")

with open(pt, 'w') as f:
    f.write(content)

print("partners.html saved")

# ── Fix booking.html ──
bk = '/opt/fpai/apps/zen-village/frontend/public/booking.html'
with open(bk, 'r') as f:
    content = f.read()

content = content.replace(
    'El Nido \\u2014 $150/night',
    'El Nido \\u2014 $115/night'
)

with open(bk, 'w') as f:
    f.write(content)

print("booking.html saved (El Nido → $115/night)")
