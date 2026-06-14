#!/usr/bin/env python3
"""
Quote Command Module
=====================

A sample module demonstrating the module system.
Returns an inspiring quote.
"""

import random

QUOTES = [
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ("Be the change you wish to see in the world.", "Mahatma Gandhi"),
    ("Stay hungry, stay foolish.", "Steve Jobs"),
    ("In the middle of difficulty lies opportunity.", "Albert Einstein"),
    ("The future belongs to those who believe in the beauty of their dreams.", "Eleanor Roosevelt"),
    ("It is during our darkest moments that we must focus to see the light.", "Aristotle"),
    ("The best time to plant a tree was 20 years ago. The second best time is now.", "Chinese Proverb"),
    ("Your time is limited, don't waste it living someone else's life.", "Steve Jobs"),
    ("The only impossible journey is the one you never begin.", "Tony Robbins"),
    ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Winston Churchill"),
    ("What you get by achieving your goals is not as important as what you become by achieving your goals.", "Zig Ziglar"),
    ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
    ("The mind is everything. What you think you become.", "Buddha"),
    ("Strive not to be a success, but rather to be of value.", "Albert Einstein"),
    ("The way to get started is to quit talking and begin doing.", "Walt Disney"),
]


def handle(args: str, context: dict) -> str:
    """
    Handle the /quote command.
    
    Args:
        args: Optional category (not used in this version)
        context: Dict with user_id, chat_id, command, module_name
    
    Returns:
        A formatted quote string
    """
    quote, author = random.choice(QUOTES)
    
    return f"✨ *Quote of the Moment*\n\n\"{quote}\"\n\n— _{author}_"


