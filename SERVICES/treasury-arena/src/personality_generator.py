"""
Personality Generator - Assigns unique names and traits to treasury agents
Makes the arena more game-like with distinct agent personalities
"""

import random
from typing import Dict, Any


# Agent name pools by strategy type
DEFI_NAMES = [
    "Yield Yoda", "APY Annie", "Harvest Harry", "Compound Carl",
    "Liquidity Lucy", "Stake Steve", "Farm Phil", "Pool Paula",
    "Vault Victor", "Lend Larry", "Protocol Pete", "Optimize Olivia"
]

TACTICAL_NAMES = [
    "Trade Tom", "Chart Charlie", "Signal Sam", "Momentum Mary",
    "Profit Pete", "Market Mike", "Technical Tina", "Swing Sarah",
    "Position Paul", "Timing Tim", "Trend Tracy", "Alpha Alex"
]

# Avatar options by strategy
DEFI_AVATARS = ["🌾", "🚜", "🌻", "🌱", "🍯", "🐝", "🌿", "🌳", "🌲", "🌴"]
TACTICAL_AVATARS = ["📈", "📊", "💹", "⚡", "🎯", "🔥", "⚔️", "🏹", "🎲", "🎰"]

# Personality traits
RISK_PROFILES = ["conservative", "moderate", "aggressive", "balanced"]
AGGRESSION_LEVELS = ["passive", "balanced", "aggressive", "ultra-aggressive"]
TRADING_STYLES = [
    "patient and methodical",
    "quick and decisive",
    "analytical and precise",
    "opportunistic and flexible",
    "bold and daring",
    "cautious and careful"
]

# Used names tracking to ensure uniqueness
_used_names = set()


def generate_personality(strategy_type: str) -> Dict[str, Any]:
    """
    Generate a unique personality for an agent

    Args:
        strategy_type: "DeFi-Yield-Farmer" or "Tactical-Trader"

    Returns:
        Dictionary with name, avatar, and personality traits
    """

    # Select name pool based on strategy
    if strategy_type == "DeFi-Yield-Farmer":
        name_pool = DEFI_NAMES
        avatar_pool = DEFI_AVATARS
    else:  # Tactical-Trader
        name_pool = TACTICAL_NAMES
        avatar_pool = TACTICAL_AVATARS

    # Get unique name (not previously used)
    available_names = [n for n in name_pool if n not in _used_names]
    if not available_names:
        # If all names used, reset and allow reuse
        _used_names.clear()
        available_names = name_pool

    name = random.choice(available_names)
    _used_names.add(name)

    # Random avatar
    avatar = random.choice(avatar_pool)

    # Generate personality traits
    risk_tolerance = random.choice(RISK_PROFILES)
    aggression = random.choice(AGGRESSION_LEVELS)
    trading_style = random.choice(TRADING_STYLES)

    # Strategy-specific descriptions
    if strategy_type == "DeFi-Yield-Farmer":
        description = f"A {risk_tolerance} yield hunter who is {trading_style}. "
        description += f"Focuses on maximizing stable returns through protocol optimization."
    else:
        description = f"A {risk_tolerance} tactical trader who is {trading_style}. "
        description += f"Uses technical analysis and market timing to capture alpha."

    return {
        'name': name,
        'avatar': avatar,
        'personality': {
            'risk_tolerance': risk_tolerance,
            'aggression': aggression,
            'trading_style': trading_style,
            'description': description
        }
    }


def reset_used_names():
    """Reset the used names tracker (useful for testing)"""
    global _used_names
    _used_names.clear()
