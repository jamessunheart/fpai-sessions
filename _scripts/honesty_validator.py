#!/usr/bin/env python3
"""
Honesty Validator - Checks agent messaging for compliance with honesty principles
Run this before any agent sends messages to humans
"""

import re
from typing import Dict, List, Tuple

# HONESTY PRINCIPLES - Must be present in messaging
REQUIRED_ELEMENTS = {
    "ai_disclosure": [
        "ai", "claude", "artificial intelligence", "ai helped", "ai-assisted", "ai-"
    ],
    "experimental_framing": [
        "experiment", "testing", "exploring", "trying", "learning", "seeing if"
    ],
    "uncertainty_acknowledgment": [
        "might", "maybe", "could", "not sure", "finding out", "let's see",
        "might fail", "might work", "that's what we're testing"
    ],
    "stage_transparency": [
        "early stage", "zero", "just launched", "just starting",
        "first", "testing", "in development"
    ]
}

# RED FLAGS - Should NOT be present
RED_FLAGS = [
    "guaranteed", "proven", "always works", "never fails",
    "revolutionary", "game-changing", "disrupting",
    "limited spots", "act now", "don't miss out",
    "thousands of users", "proven results" # when they don't exist
]

def check_honesty_compliance(message: str, message_type: str = "general") -> Tuple[bool, List[str], List[str]]:
    """
    Check if a message complies with honesty principles

    Returns:
        (is_compliant, warnings, suggestions)
    """
    warnings = []
    suggestions = []

    message_lower = message.lower()

    # Check for AI disclosure
    has_ai_disclosure = any(term in message_lower for term in REQUIRED_ELEMENTS["ai_disclosure"])
    if not has_ai_disclosure:
        warnings.append("❌ Missing AI disclosure")
        suggestions.append("Add: 'AI (Claude) helped write this' or similar")

    # Check for experimental framing
    has_experimental = any(term in message_lower for term in REQUIRED_ELEMENTS["experimental_framing"])
    if not has_experimental:
        warnings.append("⚠️  Not framed as experiment/test")
        suggestions.append("Add: 'Testing if...', 'Experimenting with...', or similar")

    # Check for uncertainty acknowledgment
    has_uncertainty = any(term in message_lower for term in REQUIRED_ELEMENTS["uncertainty_acknowledgment"])
    if not has_uncertainty:
        warnings.append("⚠️  No uncertainty acknowledged")
        suggestions.append("Add: 'Might work, might not', 'Let's find out together', or similar")

    # Check for stage transparency
    has_stage = any(term in message_lower for term in REQUIRED_ELEMENTS["stage_transparency"])
    if not has_stage:
        warnings.append("⚠️  Current stage not clear")
        suggestions.append("Add: 'Early stage', 'Zero users yet', or similar")

    # Check for red flags
    found_red_flags = [flag for flag in RED_FLAGS if flag in message_lower]
    if found_red_flags:
        for flag in found_red_flags:
            warnings.append(f"🚨 RED FLAG: '{flag}' - avoid hype language")
        suggestions.append("Replace with honest, experimental language")

    # Determine compliance - relaxed: AI disclosure + experimental OR (stage transparency + no red flags)
    is_compliant = (
        has_ai_disclosure and
        (has_experimental or has_stage) and
        len(found_red_flags) == 0
    )

    return is_compliant, warnings, suggestions

def validate_message(message: str, message_type: str = "general", auto_fix: bool = False) -> Dict:
    """
    Validate a message and return detailed report
    """
    is_compliant, warnings, suggestions = check_honesty_compliance(message, message_type)

    report = {
        "compliant": is_compliant,
        "message_type": message_type,
        "warnings": warnings,
        "suggestions": suggestions,
        "message_preview": message[:200] + "..." if len(message) > 200 else message
    }

    return report

def print_validation_report(report: Dict):
    """Pretty print validation report"""
    print("\n" + "="*70)
    print("🔍 HONESTY VALIDATION REPORT")
    print("="*70)

    if report["compliant"]:
        print("✅ COMPLIANT - Message follows honesty principles")
    else:
        print("❌ NOT COMPLIANT - Message needs revision")

    print(f"\nMessage Type: {report['message_type']}")
    print(f"\nPreview:\n{report['message_preview']}")

    if report["warnings"]:
        print("\n⚠️  WARNINGS:")
        for warning in report["warnings"]:
            print(f"  {warning}")

    if report["suggestions"]:
        print("\n💡 SUGGESTIONS:")
        for suggestion in report["suggestions"]:
            print(f"  • {suggestion}")

    print("="*70 + "\n")

# Example usage and tests
if __name__ == "__main__":
    print("🌟 HONESTY VALIDATOR - Testing Messages\n")

    # Test 1: Good honest message
    honest_message = """
    Full transparency: I'm running an experiment with AI (Claude) to test if we can match
    financial advisors to clients better than traditional lead gen.

    Current status: Zero revenue, early stage, genuinely testing if this adds value.

    Might work, might not - that's what we're learning. Want to explore together?

    P.S. - Yes, Claude AI helped write this message.
    """

    print("TEST 1: Honest Message")
    report1 = validate_message(honest_message, "linkedin")
    print_validation_report(report1)

    # Test 2: Bad hyped message
    hyped_message = """
    Revolutionary AI platform guaranteed to 10x your results!

    Join thousands of successful users. Proven results. Limited spots available - act now!

    Don't miss this game-changing opportunity.
    """

    print("\nTEST 2: Hyped Message (Should Fail)")
    report2 = validate_message(hyped_message, "reddit")
    print_validation_report(report2)

    # Test 3: Missing AI disclosure
    missing_ai = """
    Testing a new matching platform. Early stage, zero revenue yet.

    Might work, might not - let's find out together.
    """

    print("\nTEST 3: Missing AI Disclosure")
    report3 = validate_message(missing_ai, "email")
    print_validation_report(report3)

    print("\n" + "="*70)
    print("✅ Validator ready to use!")
    print("="*70)
    print("\nUsage in agents:")
    print("  from honesty_validator import validate_message")
    print("  report = validate_message(your_message)")
    print("  if not report['compliant']:")
    print("      print('⚠️  Message needs revision!')")
    print("="*70 + "\n")
