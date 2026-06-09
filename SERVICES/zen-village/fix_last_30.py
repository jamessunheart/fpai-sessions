#!/usr/bin/env python3
"""Fix the last remaining 30% reference in the partner script section."""

PARTNERS = "/opt/fpai/apps/zen-village/frontend/public/partners.html"
with open(PARTNERS, 'r') as f:
    p = f.read()

# Fix the partner script: update 30% -> 20% and improve the wording
old_script = (
    '<p>"Zen Village is a conscious retreat with intentional spaces '
    '\u2014 from communal homes to river cabins and hillside solitude. '
    "If you book through me, you'll get <strong>30% off</strong> the regular rates. "
    "I'll make sure everything is arranged smoothly.\"</p>"
)

new_script = (
    '<p>"Zen Village is a 45-acre conscious retreat in the mountains of Costa Rica '
    '\u2014 unique zomes, riverside cabins, hilltop hideaways, and communal spaces. '
    "If you book through me, you'll get <strong>20% off</strong> the listed rates. "
    "They also have seasonal pricing so Green Season (May\u2013Nov) is even more affordable. "
    "I'll make sure everything is arranged smoothly.\"</p>"
)

if old_script in p:
    p = p.replace(old_script, new_script)
    print("Fixed partner script: 30% -> 20% + seasonal mention")
else:
    print("Exact match not found, trying broader fix...")
    # Broader replacement
    p = p.replace(
        "30% off</strong> the regular rates",
        "20% off</strong> the listed rates. They also have seasonal pricing so Green Season (May\u2013Nov) is even more affordable"
    )
    print("Fixed via broader replace")

# Final check: no more 30% anywhere
count = p.count('30%')
print(f"Remaining 30% references: {count}")
if count > 0:
    import re
    for i, line in enumerate(p.split('\n'), 1):
        if '30%' in line:
            print(f"  Line {i}: {line.strip()[:120]}")

with open(PARTNERS, 'w') as f:
    f.write(p)
print("Saved partners.html")
