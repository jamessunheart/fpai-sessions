#!/usr/bin/env python3
"""
Affirmation Module
==================

Daily affirmations aligned with Full Potential principles:
- Love at the core
- Truth as foundation
- Coherence over chaos
- Growth through service
"""

import random
from datetime import datetime

# Affirmations organized by theme
AFFIRMATIONS = {
    "love": [
        "I lead with love in every decision.",
        "Love is my compass; it guides me true.",
        "I receive love as freely as I give it.",
        "My heart is open to infinite possibilities.",
        "Love flows through me to everyone I meet.",
        "I am worthy of deep, authentic love.",
        "Love is the source of my strength.",
    ],
    "truth": [
        "I speak my truth with courage and compassion.",
        "Truth illuminates my path forward.",
        "I trust myself to recognize what is real.",
        "My commitment to truth sets me free.",
        "I seek understanding over being right.",
        "Truth is my foundation; nothing can shake it.",
        "I honor truth even when it's uncomfortable.",
    ],
    "coherence": [
        "I am aligned in thought, word, and action.",
        "My inner peace creates outer harmony.",
        "I choose coherence over chaos.",
        "My clarity grows stronger each day.",
        "I move through complexity with ease.",
        "My mind, body, and spirit work as one.",
        "I am centered in the midst of change.",
    ],
    "growth": [
        "Every challenge is an opportunity to grow.",
        "I embrace the unknown with curiosity.",
        "My potential unfolds with each new day.",
        "I learn, adapt, and evolve constantly.",
        "Growth is my natural state of being.",
        "I celebrate progress, not perfection.",
        "Each step forward matters.",
    ],
    "service": [
        "My work creates value for others.",
        "I serve from overflow, not depletion.",
        "My gifts are meant to be shared.",
        "I lift others as I rise.",
        "Service is the expression of my purpose.",
        "I make a difference simply by being me.",
        "The world needs exactly what I have to offer.",
    ],
    "abundance": [
        "Abundance flows to me and through me.",
        "I am open to receive all good things.",
        "There is enough for everyone, including me.",
        "My prosperity benefits all around me.",
        "I trust the universe to provide.",
        "Wealth is a tool for positive change.",
        "I create value; value returns to me.",
    ],
}

# Themes mapped to time of day
TIME_THEMES = {
    "morning": ["love", "growth", "coherence"],     # 5am-12pm
    "afternoon": ["truth", "service", "abundance"], # 12pm-6pm
    "evening": ["coherence", "love", "truth"],      # 6pm-10pm
    "night": ["love", "coherence", "growth"],       # 10pm-5am
}


def _get_time_period() -> str:
    """Get current time period."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 22:
        return "evening"
    else:
        return "night"


def _get_themed_affirmation(theme: str = None) -> tuple:
    """Get an affirmation, optionally by theme."""
    if theme and theme.lower() in AFFIRMATIONS:
        chosen_theme = theme.lower()
    else:
        # Use time-appropriate themes
        period = _get_time_period()
        chosen_theme = random.choice(TIME_THEMES[period])
    
    affirmation = random.choice(AFFIRMATIONS[chosen_theme])
    return affirmation, chosen_theme


def handle(args: str, context: dict) -> str:
    """
    Handle the /affirm command.
    
    Args:
        args: Optional theme (love, truth, coherence, growth, service, abundance)
        context: Command context
    
    Returns:
        An affirmation to inspire
    """
    theme_arg = args.strip().lower() if args else None
    
    # Help text
    if theme_arg == "help":
        themes = ", ".join(AFFIRMATIONS.keys())
        return (
            "✨ **Affirmations**\n\n"
            f"Get a random affirmation:\n`/affirm`\n\n"
            f"Choose a theme:\n`/affirm <theme>`\n\n"
            f"**Themes:** {themes}\n\n"
            "_Affirmations are time-aware - morning themes differ from evening._"
        )
    
    # List all themes
    if theme_arg == "themes":
        response = "✨ **Affirmation Themes**\n\n"
        for theme, affirms in AFFIRMATIONS.items():
            emoji = {
                "love": "💖",
                "truth": "🔮",
                "coherence": "🎯",
                "growth": "🌱",
                "service": "🤝",
                "abundance": "💫"
            }.get(theme, "✨")
            response += f"{emoji} **{theme.title()}** ({len(affirms)} affirmations)\n"
        response += "\n_Use `/affirm <theme>` for a specific theme_"
        return response
    
    # Get affirmation
    affirmation, theme = _get_themed_affirmation(theme_arg)
    
    # Theme emoji
    emoji = {
        "love": "💖",
        "truth": "🔮",
        "coherence": "🎯",
        "growth": "🌱",
        "service": "🤝",
        "abundance": "💫"
    }.get(theme, "✨")
    
    period = _get_time_period()
    greeting = {
        "morning": "Good morning",
        "afternoon": "Good afternoon",
        "evening": "Good evening",
        "night": "Rest well"
    }.get(period, "Hello")
    
    return (
        f"{emoji} **{greeting}**\n\n"
        f"_{affirmation}_\n\n"
        f"Theme: **{theme.title()}**\n\n"
        f"_Say it out loud. Let it sink in._"
    )


