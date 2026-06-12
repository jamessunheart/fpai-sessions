"""
Zen Village - Accommodation Configuration
Updated to match current website property names and seasonal pricing
"""

ZONES = {
    "village_heart": {
        "name": "Village Heart",
        "emoji": "\U0001f33f",
        "description": "Central hub with communal spaces, fire pit, sauna, hot tub, movement areas, and event spaces."
    },
    "river_grove": {
        "name": "River Grove",
        "emoji": "\U0001f30a",
        "description": "Close to the river for early-morning presence, sensory immersion, and gentle water soundscapes."
    },
    "escape_ridge": {
        "name": "Escape Ridge",
        "emoji": "\U0001f304",
        "description": "Remote hillside retreats with panoramic views, coffee groves, and solitude. Recommended access via 4\u00d74 or quad."
    }
}

SEASON_CONFIG = {
    "high_months": [12, 1, 2, 3, 4],
    "green_months": [5, 6, 7, 8, 9, 10, 11],
    "green_discount": 0.15,
}

ACCOMMODATIONS = [
    {
        "id": "astro-alpha",
        "name": "Sky Lily Zome",
        "description": "Two-story zome with upstairs sleeping area and downstairs open living space. Like a lily pad in the sky.",
        "zone": "village_heart",
        "type": "zome",
        "bedrooms": 1,
        "bathrooms": 1,
        "max_guests": 4,
        "sleeps": "2-4",
        "nightly_rate": 130,
        "weekly_rate": 780,
        "monthly_rate": 2200,
        "green_nightly": 110,
        "green_weekly": 663,
        "green_monthly": 1870,
        "cleaning_fee": 40,
        "amenities": ["kitchen", "wifi", "unique_architecture"]
    },
    {
        "id": "astro-sol",
        "name": "Astro Sol Zome",
        "description": "Two-story zome with sun-drenched views, upstairs sleeping area, and open living space with kitchen.",
        "zone": "village_heart",
        "type": "zome",
        "bedrooms": 1,
        "bathrooms": 1,
        "max_guests": 4,
        "sleeps": "2-4",
        "nightly_rate": 130,
        "weekly_rate": 780,
        "monthly_rate": 2200,
        "green_nightly": 110,
        "green_weekly": 663,
        "green_monthly": 1870,
        "cleaning_fee": 40,
        "amenities": ["kitchen", "wifi", "unique_architecture", "sun_views"]
    },
    {
        "id": "green-casita",
        "name": "Green Casita",
        "description": "A cozy cabana nestled near the Singing Dome chapel. Intimate and peaceful, ideal for solo travelers or couples.",
        "zone": "village_heart",
        "type": "casita",
        "bedrooms": 1,
        "bathrooms": 1,
        "max_guests": 2,
        "sleeps": "1-2",
        "nightly_rate": 95,
        "weekly_rate": 570,
        "monthly_rate": 1600,
        "green_nightly": 81,
        "green_weekly": 484,
        "green_monthly": 1360,
        "cleaning_fee": 30,
        "amenities": ["chapel_adjacent", "wifi", "cozy"]
    },
    {
        "id": "riverlight",
        "name": "Riverlight Cabin",
        "description": "Cozy cabin by the river with sensory immersion and gentle water soundscapes.",
        "zone": "river_grove",
        "type": "cabin",
        "bedrooms": 1,
        "bathrooms": 1,
        "max_guests": 2,
        "sleeps": "1-2",
        "nightly_rate": 120,
        "weekly_rate": 720,
        "monthly_rate": 2000,
        "green_nightly": 102,
        "green_weekly": 612,
        "green_monthly": 1700,
        "cleaning_fee": 35,
        "amenities": ["river_view", "wifi", "quiet"]
    },
    {
        "id": "zen-casa",
        "name": "Zen Casa",
        "description": "Spacious 3-bedroom communal home with full kitchen, shared spaces, and garden views.",
        "zone": "village_heart",
        "type": "house",
        "bedrooms": 3,
        "bathrooms": 2,
        "max_guests": 6,
        "sleeps": "4-6",
        "nightly_rate": 180,
        "weekly_rate": 1080,
        "monthly_rate": 3200,
        "green_nightly": 153,
        "green_weekly": 918,
        "green_monthly": 2720,
        "cleaning_fee": 50,
        "amenities": ["kitchen", "wifi", "shared_spaces", "garden"]
    },
    {
        "id": "the-vista",
        "name": "El Nido",
        "description": "Cozy circular hillside cabin on Escape Ridge offering solitude and stunning views. Perfect for solo travelers, writers, or couples seeking deep retreat.",
        "zone": "escape_ridge",
        "type": "cabin",
        "bedrooms": 1,
        "bathrooms": 1,
        "max_guests": 2,
        "sleeps": "1-2",
        "nightly_rate": 115,
        "weekly_rate": 690,
        "monthly_rate": 1900,
        "green_nightly": 98,
        "green_weekly": 586,
        "green_monthly": 1615,
        "cleaning_fee": 35,
        "amenities": ["hillside", "solitude", "mountain_view", "cozy"]
    },
    {
        "id": "the-nido",
        "name": "La Vista",
        "description": "Circular hilltop cabin with queen bed perched on the hillside with breathtaking panoramic views over the valley. Spacious deck for sunrise meditation and stargazing.",
        "zone": "escape_ridge",
        "type": "cabin",
        "bedrooms": 1,
        "bathrooms": 1,
        "max_guests": 2,
        "sleeps": "2",
        "nightly_rate": 150,
        "weekly_rate": 900,
        "monthly_rate": 2400,
        "green_nightly": 128,
        "green_weekly": 765,
        "green_monthly": 2040,
        "cleaning_fee": 40,
        "amenities": ["panoramic_view", "deck", "queen_bed", "solitude", "coffee_groves"]
    },
    {
        "id": "camp-spring",
        "name": "Camp Spring",
        "description": "Bring-your-own-tent camping spot in the Village Heart near communal facilities.",
        "zone": "village_heart",
        "type": "camping",
        "bedrooms": 0,
        "bathrooms": 0,
        "max_guests": 4,
        "sleeps": "1-4",
        "nightly_rate": 20,
        "weekly_rate": 120,
        "monthly_rate": 350,
        "green_nightly": 17,
        "green_weekly": 102,
        "green_monthly": 298,
        "cleaning_fee": 0,
        "amenities": ["shared_facilities", "fire_pit", "nature"]
    },
    {
        "id": "communal-space",
        "name": "Communal Space / Main House",
        "description": "Main house kitchen and communal areas. Available for day events, group gatherings, and workshops.",
        "zone": "village_heart",
        "type": "event_space",
        "bedrooms": 0,
        "bathrooms": 2,
        "max_guests": 50,
        "sleeps": "0",
        "nightly_rate": 500,
        "weekly_rate": 2500,
        "monthly_rate": 8000,
        "green_nightly": 400,
        "green_weekly": 2000,
        "green_monthly": 6500,
        "cleaning_fee": 100,
        "amenities": ["kitchen", "large_group", "event_space", "wifi"]
    },
    {
        "id": "glamp-grove",
        "name": "Glamp Grove",
        "description": "Equipped glamping tent with comfortable bed and furnishings in the Village Heart.",
        "zone": "village_heart",
        "type": "glamping",
        "bedrooms": 1,
        "bathrooms": 0,
        "max_guests": 2,
        "sleeps": "1-2",
        "nightly_rate": 45,
        "weekly_rate": 270,
        "monthly_rate": 800,
        "green_nightly": 38,
        "green_weekly": 230,
        "green_monthly": 680,
        "cleaning_fee": 15,
        "amenities": ["furnished", "shared_facilities", "nature"]
    },
    {
        "id": "zen-palace",
        "name": "Zen Palace",
        "description": "Spacious 5-bedroom house surrounded by lush tropical gardens, palms, and mountain views. Glass-front living area with open-air flow. Ideal for groups, families, or retreats.",
        "zone": "village_heart",
        "type": "house",
        "bedrooms": 5,
        "bathrooms": 3,
        "max_guests": 10,
        "sleeps": "6-10",
        "nightly_rate": 500,
        "per_room_rate": 100,
        "weekly_rate": 3000,
        "monthly_rate": 9000,
        "green_nightly": 425,
        "green_weekly": 2550,
        "green_monthly": 7650,
        "cleaning_fee": 75,
        "amenities": ["full_kitchen", "wifi", "garden", "mountain_views", "glass_front", "tropical_gardens", "group_friendly"],
        "image": "/images/zen-palace.jpg"
    },
]

AIRBNB_MAPPINGS = {}


def get_current_season():
    """Return 'high' or 'green' based on current month"""
    from datetime import date
    month = date.today().month
    if month in SEASON_CONFIG["high_months"]:
        return "high"
    return "green"


def get_accommodation(accommodation_id: str) -> dict:
    for acc in ACCOMMODATIONS:
        if acc['id'] == accommodation_id:
            return acc
    return None


def get_accommodations_by_zone(zone: str) -> list:
    return [acc for acc in ACCOMMODATIONS if acc['zone'] == zone]


def get_all_accommodations() -> list:
    return ACCOMMODATIONS


def get_zones() -> dict:
    return ZONES
