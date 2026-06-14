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
        "name": "La Vista",
        "description": "Hilltop cabin on Escape Ridge with panoramic views and bigger bed. Sleeps 2.",
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
        "cleaning_fee": 45,
        "amenities": ["panoramic_view", "deck", "solitude", "coffee_groves"]
    },
    {
        "id": "the-nido",
        "name": "The Nest",
        "description": "Cozy hilltop cabin on Escape Ridge. Single bed, ideal for solo travelers. Couples possible.",
        "zone": "escape_ridge",
        "type": "cabin",
        "bedrooms": 1,
        "bathrooms": 1,
        "max_guests": 2,
        "sleeps": "1 (couples possible)",
        "nightly_rate": 115,
        "weekly_rate": 690,
        "monthly_rate": 1900,
        "green_nightly": 98,
        "green_weekly": 586,
        "green_monthly": 1615,
        "cleaning_fee": 35,
        "amenities": ["hillside", "solitude", "mountain_view"]
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
    }
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
