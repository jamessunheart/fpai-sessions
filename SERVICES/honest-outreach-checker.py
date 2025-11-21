#!/usr/bin/env python3
"""
Honest Outreach Checker
Session #2 - Autonomous Infrastructure

Validates all outreach messages against honesty principles before sending.
Ensures we always communicate with transparency and integrity.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Honesty Checklist (All must be present)
HONESTY_CHECKLIST = {
    "ai_disclosure": {
        "name": "AI Involvement Disclosed",
        "keywords": ["AI", "Claude", "AI helped", "AI-powered", "using Claude"],
        "required": True
    },
    "experimental_framing": {
        "name": "Experimental Framing",
        "keywords": ["experiment", "testing", "trying", "seeing if", "learning if"],
        "required": True
    },
    "stage_transparency": {
        "name": "Stage Transparency",
        "keywords": ["zero customers", "just launched", "early stage", "starting"],
        "required": True
    },
    "uncertainty_acknowledged": {
        "name": "Uncertainty Acknowledged",
        "keywords": ["might", "maybe", "don't know", "uncertain", "let's find out"],
        "required": True
    },
    "curiosity_invitation": {
        "name": "Curiosity Invitation",
        "keywords": ["curious", "feedback", "thoughts", "help test", "want to try"],
        "required": True
    },
    "commitment_to_learning": {
        "name": "Commitment to Report Back",
        "keywords": ["report back", "will share", "let you know", "update you"],
        "required": True
    }
}


def check_message_honesty(message: str) -> dict:
    """
    Check if message passes honesty requirements.

    Returns:
        dict: {
            "passed": bool,
            "score": int (0-100),
            "items_passed": int,
            "items_failed": int,
            "details": {...},
            "suggestions": [...]
        }
    """
    message_lower = message.lower()
    results = {}
    passed_count = 0
    failed_count = 0
    suggestions = []

    # Check each criterion
    for key, criterion in HONESTY_CHECKLIST.items():
        found = any(keyword.lower() in message_lower for keyword in criterion["keywords"])

        results[key] = {
            "name": criterion["name"],
            "passed": found,
            "required": criterion["required"]
        }

        if found:
            passed_count += 1
        else:
            failed_count += 1
            suggestions.append(
                f"Add {criterion['name']}: Use words like {', '.join(criterion['keywords'][:3])}"
            )

    # Calculate score
    score = int((passed_count / len(HONESTY_CHECKLIST)) * 100)
    overall_pass = failed_count == 0

    return {
        "passed": overall_pass,
        "score": score,
        "items_passed": passed_count,
        "items_failed": failed_count,
        "total_items": len(HONESTY_CHECKLIST),
        "details": results,
        "suggestions": suggestions,
        "timestamp": datetime.now().isoformat()
    }


def print_results(results: dict, message: str):
    """Pretty print honesty check results."""

    print("\n" + "="*70)
    print("🌟 HONESTY CHECK RESULTS")
    print("="*70)

    # Overall
    if results["passed"]:
        print(f"\n✅ PASSED - Message approved for sending")
        print(f"Score: {results['score']}/100")
    else:
        print(f"\n❌ FAILED - Rewrite needed before sending")
        print(f"Score: {results['score']}/100")
        print(f"Items passed: {results['items_passed']}/{results['total_items']}")

    # Details
    print("\n" + "-"*70)
    print("DETAILED CHECKLIST:")
    print("-"*70)

    for key, detail in results["details"].items():
        status = "✅" if detail["passed"] else "❌"
        required = "(REQUIRED)" if detail["required"] else "(optional)"
        print(f"{status} {detail['name']} {required}")

    # Suggestions if failed
    if not results["passed"]:
        print("\n" + "-"*70)
        print("💡 SUGGESTIONS TO FIX:")
        print("-"*70)
        for i, suggestion in enumerate(results["suggestions"], 1):
            print(f"{i}. {suggestion}")

    print("\n" + "="*70)
    print()


def save_check_result(message: str, results: dict, output_file: str = None):
    """Save honesty check results to file."""

    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"honesty_check_{timestamp}.json"

    data = {
        "message": message,
        "results": results,
        "checked_at": datetime.now().isoformat()
    }

    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"📝 Results saved to: {output_file}")


def main():
    """Main execution."""

    if len(sys.argv) < 2:
        print("Usage: python honest-outreach-checker.py <message_file>")
        print("   or: python honest-outreach-checker.py --test")
        sys.exit(1)

    if sys.argv[1] == "--test":
        # Test with example message
        test_message = """
        Testing if AI can match you to a financial advisor better than Google?

        Full transparency: This is an experiment using Claude AI.

        Zero customers so far - genuinely early stage.

        Might work, might not - that's what we're testing.

        Want to help test? Your feedback helps even if it doesn't work.

        Will report back in 30 days whether this worked or was a dead end.
        """

        print("\n🧪 TESTING WITH SAMPLE MESSAGE:")
        print(test_message)

        results = check_message_honesty(test_message)
        print_results(results, test_message)

    else:
        # Check actual message from file
        message_file = sys.argv[1]

        if not Path(message_file).exists():
            print(f"❌ Error: File not found: {message_file}")
            sys.exit(1)

        with open(message_file, 'r') as f:
            message = f.read()

        results = check_message_honesty(message)
        print_results(results, message)

        # Save results
        save_check_result(message, results)

        # Exit code: 0 if passed, 1 if failed
        sys.exit(0 if results["passed"] else 1)


if __name__ == "__main__":
    main()
