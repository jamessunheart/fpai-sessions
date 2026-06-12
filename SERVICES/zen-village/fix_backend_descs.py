#!/usr/bin/env python3
"""Fix backend config descriptions and details for El Nido / La Vista after name swap."""

config_path = '/opt/fpai/apps/zen-village/app/accommodations_config.py'
with open(config_path, 'r') as f:
    content = f.read()

# the-vista = El Nido (smaller, cozy cabin)
# Currently has La Vista's old description: "Hilltop cabin... panoramic views and bigger bed"
content = content.replace(
    '"id": "the-vista",\n        "name": "El Nido",\n        "description": "Hilltop cabin on Escape Ridge with panoramic views and bigger bed. Sleeps 2.",',
    '"id": "the-vista",\n        "name": "El Nido",\n        "description": "Cozy circular hillside cabin on Escape Ridge offering solitude and stunning views. Perfect for solo travelers, writers, or couples seeking deep retreat.",',
)

# Fix the-vista amenities (swap to El Nido amenities)
content = content.replace(
    '"sleeps": "1-2",\n        "nightly_rate": 115,\n        "weekly_rate": 690,\n        "monthly_rate": 1900,\n        "green_nightly": 98,\n        "green_weekly": 586,\n        "green_monthly": 1615,\n        "cleaning_fee": 45,\n        "amenities": ["panoramic_view", "deck", "solitude", "coffee_groves"]',
    '"sleeps": "1-2",\n        "nightly_rate": 115,\n        "weekly_rate": 690,\n        "monthly_rate": 1900,\n        "green_nightly": 98,\n        "green_weekly": 586,\n        "green_monthly": 1615,\n        "cleaning_fee": 35,\n        "amenities": ["hillside", "solitude", "mountain_view", "cozy"]',
)

# the-nido = La Vista (bigger cabin with queen bed, panoramic views)
# Currently has El Nido's old description: "Cozy... Single bed, solo travelers"
content = content.replace(
    '"id": "the-nido",\n        "name": "La Vista",\n        "description": "Cozy hilltop cabin on Escape Ridge. Single bed, ideal for solo travelers. Couples possible.",',
    '"id": "the-nido",\n        "name": "La Vista",\n        "description": "Circular hilltop cabin with queen bed perched on the hillside with breathtaking panoramic views over the valley. Spacious deck for sunrise meditation and stargazing.",',
)

# Fix the-nido sleeps and amenities (swap to La Vista amenities)
content = content.replace(
    '"sleeps": "1 (couples possible)",\n        "nightly_rate": 150,\n        "weekly_rate": 900,\n        "monthly_rate": 2400,\n        "green_nightly": 128,\n        "green_weekly": 765,\n        "green_monthly": 2040,\n        "cleaning_fee": 40,\n        "amenities": ["hillside", "solitude", "mountain_view"]',
    '"sleeps": "2",\n        "nightly_rate": 150,\n        "weekly_rate": 900,\n        "monthly_rate": 2400,\n        "green_nightly": 128,\n        "green_weekly": 765,\n        "green_monthly": 2040,\n        "cleaning_fee": 40,\n        "amenities": ["panoramic_view", "deck", "queen_bed", "solitude", "coffee_groves"]',
)

with open(config_path, 'w') as f:
    f.write(content)

print("Backend config fixed:")
print("  the-vista (El Nido): cozy cabin, sleeps 1-2, $115/nt, $35 cleaning")
print("  the-nido (La Vista): queen bed, panoramic views, sleeps 2, $150/nt, $40 cleaning")
