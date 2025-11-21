#!/usr/bin/env python3
"""
Messaging PR Filter - Fact checks and filters for public perception
Catches messaging that might not build trust or align with bigger mission

Run AFTER honesty validator, BEFORE sending to public
"""

from typing import List, Tuple, Dict

# RED FLAGS - Things that shouldn't be in public messaging
PERCEPTION_RED_FLAGS = {
    "personal_material_goals": [
        "mercedes", "luxury car", "buy a car", "my car",
        "personal goal", "I want to", "getting rich"
    ],
    "focus_on_self_not_mission": [
        "I will get", "benefits me", "my benefit", "for myself"
    ],
    "unverified_claims": [
        "first ever", "only one", "never been done", "revolutionary"
    ],
    "religious_appropriation": [
        "using church for", "church loophole", "church hack"
    ],
    "unclear_value_prop": [
        "worthy recipient" # Too vague - who decides? seems arbitrary
    ]
}

# MISSION-ALIGNED LANGUAGE - What should be emphasized instead
MISSION_ALIGNED = {
    "community_benefit": [
        "community members", "collective", "together", "shared",
        "fair distribution", "meaningful allocation"
    ],
    "exploration_learning": [
        "testing if", "exploring whether", "learning how",
        "experiment", "discovery", "understanding"
    ],
    "ai_human_collaboration": [
        "AI + human", "together with AI", "collaborative",
        "co-creation", "partnership"
    ],
    "transparency": [
        "on-chain", "verifiable", "transparent", "open",
        "fully visible", "public"
    ]
}

def check_public_perception(message: str) -> Tuple[bool, List[str], List[str]]:
    """
    Check if message might create negative perception

    Returns:
        (is_mission_aligned, perception_warnings, suggestions)
    """
    warnings = []
    suggestions = []

    message_lower = message.lower()

    # Check for perception red flags
    for category, flags in PERCEPTION_RED_FLAGS.items():
        found_flags = [flag for flag in flags if flag in message_lower]
        if found_flags:
            warnings.append(f"⚠️  {category.replace('_', ' ').title()}: {', '.join(found_flags)}")

            # Category-specific suggestions
            if category == "personal_material_goals":
                suggestions.append(
                    "Remove specific personal material goals. "
                    "Focus on community benefit and fair resource distribution instead."
                )
            elif category == "focus_on_self_not_mission":
                suggestions.append(
                    "Shift focus from personal benefit to collective learning and exploration."
                )
            elif category == "unverified_claims":
                suggestions.append(
                    "Replace absolute claims with honest uncertainty: "
                    "'First church treasury I know of on Solana (might be wrong?)'"
                )
            elif category == "religious_appropriation":
                suggestions.append(
                    "Frame as genuine spiritual/technological integration, "
                    "not exploiting church status."
                )
            elif category == "unclear_value_prop":
                suggestions.append(
                    "Replace vague terms like 'worthy recipient' with clear criteria: "
                    "'community members', 'fair allocation based on contribution', etc."
                )

    # Check for mission-aligned language (positive signals)
    mission_score = 0
    for category, terms in MISSION_ALIGNED.items():
        if any(term in message_lower for term in terms):
            mission_score += 1

    # Need at least 2 mission-aligned categories present
    if mission_score < 2:
        warnings.append(
            "⚠️  Message lacks clear mission alignment. "
            "Add more focus on: community benefit, learning together, AI+human collaboration, or transparency."
        )
        suggestions.append(
            "Emphasize the MISSION more: "
            "Exploring AI + human collaboration, building something meaningful TOGETHER, "
            "fair resource distribution, transparent experimentation."
        )

    is_aligned = len(warnings) == 0 and mission_score >= 2

    return is_aligned, warnings, suggestions

def filter_message(message: str) -> Dict:
    """
    Run PR filter on message and return report
    """
    is_aligned, warnings, suggestions = check_public_perception(message)

    report = {
        "mission_aligned": is_aligned,
        "perception_warnings": warnings,
        "suggestions": suggestions,
        "message_preview": message[:200] + "..." if len(message) > 200 else message
    }

    return report

def print_pr_report(report: Dict):
    """Pretty print PR filter report"""
    print("\n" + "="*70)
    print("🎯 MESSAGING PR FILTER REPORT")
    print("="*70)

    if report["mission_aligned"]:
        print("✅ MISSION-ALIGNED - Message builds trust and focuses on collective benefit")
    else:
        print("⚠️  NEEDS REVISION - Message might not build trust or align with mission")

    print(f"\nPreview:\n{report['message_preview']}")

    if report["perception_warnings"]:
        print("\n⚠️  PERCEPTION WARNINGS:")
        for warning in report["perception_warnings"]:
            print(f"  {warning}")

    if report["suggestions"]:
        print("\n💡 SUGGESTIONS:")
        for suggestion in report["suggestions"]:
            print(f"  • {suggestion}")

    print("="*70 + "\n")

# Example usage and tests
if __name__ == "__main__":
    print("🎯 MESSAGING PR FILTER - Testing Messages\n")

    # Test 1: Message with personal material goals (BAD)
    personal_goal_message = """
    Send 1 SOL to our church treasury.

    Goal: Buy a Mercedes ($78K) and AI will decide who gets it.

    You get 2X value in tokens. I get to manifest material abundance.
    """

    print("TEST 1: Personal Material Goals (Should Fail)")
    report1 = filter_message(personal_goal_message)
    print_pr_report(report1)

    # Test 2: Mission-aligned message (GOOD)
    mission_message = """
    Wild experiment: Testing if a church treasury on Solana + AI can create
    fair resource distribution.

    The idea:
    • Community members contribute 1 SOL/month
    • AI (Claude) helps allocate resources fairly and transparently
    • Everything is on-chain and verifiable
    • We're exploring together whether AI + human collaboration can work

    Could fail spectacularly - that's the experiment.

    Testing if community + AI can build something meaningful together.
    """

    print("\nTEST 2: Mission-Aligned Message (Should Pass)")
    report2 = filter_message(mission_message)
    print_pr_report(report2)

    # Test 3: Vague "worthy recipient" language (WARNING)
    vague_message = """
    AI will decide who the worthy recipient is for material blessings.

    This is revolutionary and has never been done before!
    """

    print("\nTEST 3: Vague/Unverified Claims (Should Warn)")
    report3 = filter_message(vague_message)
    print_pr_report(report3)

    print("\n" + "="*70)
    print("✅ PR Filter ready to use!")
    print("="*70)
    print("\nUsage: Run AFTER honesty validator, BEFORE sending")
    print("  1. honesty_validator.py (checks transparency)")
    print("  2. messaging_pr_filter.py (checks public perception)")
    print("  3. Only send if BOTH pass")
    print("="*70 + "\n")
