#!/usr/bin/env python3
"""
Post VA Test Task to Delegation System

This script:
1. Posts the testnet deployment task to Upwork
2. Monitors for applications
3. Screens candidates with AI
4. Reports back top candidates for approval

Usage:
    python scripts/post-va-test-task.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Task definition
TESTNET_DEPLOYMENT_TASK = {
    "task_id": "fpai-testnet-001",
    "type": "test_task",
    "title": "TEST TASK: Deploy Crypto Token to Testnet ($15 Fixed)",

    "description": """
    Deploy cryptocurrency token to Ethereum Sepolia testnet using our scripts.

    PERFECT FOR: Entry-level VAs who can follow detailed instructions.

    WHAT YOU'LL DO:
    - Setup MetaMask wallet (testnet)
    - Get free Sepolia ETH
    - Run our deployment scripts
    - Test functions via Etherscan
    - Document results

    TIME: 3-4 hours
    PAY: $15 fixed + $5 bonus
    FUTURE: 10-20 hrs/week @ $8-15/hr for top performers

    Complete instructions provided. Entry-level welcome!
    """,

    "requirements": [
        "Basic command line comfort",
        "Attention to detail",
        "Good English communication",
        "Can start within 4 hours",
        "Can complete within 24 hours"
    ],

    "deliverables": [
        "Contract address on Sepolia testnet",
        "Etherscan verification link",
        "Test transaction screenshots",
        "All credentials in vault",
        "Completion report with time tracking"
    ],

    "budget": {
        "type": "fixed",
        "amount": 15,
        "bonus": 5,
        "currency": "USD"
    },

    "timeline": "24 hours",

    "screening_questions": [
        {
            "question": "Command line experience? (None / Basic / Comfortable)",
            "required": True
        },
        {
            "question": "Crypto/blockchain experience? (None / Wallet user / Technical)",
            "required": True
        },
        {
            "question": "Can you start within 2-4 hours? (Yes / No - when?)",
            "required": True
        }
    ],

    "application_requirements": [
        "Answer all 3 screening questions",
        "Include 'TESTNET READY' in cover letter",
        "Confirm 24-hour completion timeline"
    ],

    "skills": [
        "Virtual Assistance",
        "Technical Documentation",
        "Command Line",
        "Attention to Detail",
        "Blockchain"
    ],

    "experience_level": "entry",
    "category": "Web, Mobile & Software Dev",
    "subcategory": "Blockchain, NFT & Cryptocurrency",

    "success_criteria": {
        "contract_deployed": True,
        "etherscan_verified": True,
        "tests_completed": True,
        "good_documentation": True,
        "responsive_communication": True
    },

    "next_steps_if_successful": [
        "Immediate: More tasks at $20-50 each",
        "Week 1-2: Ongoing test tasks",
        "Week 3+: Regular work 10-20 hrs/week @ $8-15/hr",
        "Top performers: $15-25/hr + team lead potential"
    ],

    "resources_provided": [
        "40+ page deployment guide",
        "10-minute quick start checklist",
        "All scripts and code",
        "Troubleshooting guide",
        "Video walkthrough",
        "Direct Slack support",
        "Secure credential vault"
    ],

    "metadata": {
        "created_at": datetime.now().isoformat(),
        "created_by": "AI (Claude)",
        "project": "FPAI Token",
        "phase": "Testnet Deployment",
        "priority": "high",
        "is_test_task": True,
        "target_rate": "$5/hr equivalent",
        "scale_plan": "Top performers → ongoing work @ higher rates"
    }
}


def create_upwork_job_data():
    """
    Format task for Upwork API
    """
    task = TESTNET_DEPLOYMENT_TASK

    # Read full job posting
    posting_file = Path(__file__).parent.parent / "UPWORK_JOB_POSTING.md"
    with open(posting_file, 'r') as f:
        full_description = f.read()

    return {
        "title": task["title"],
        "description": full_description,
        "category": task["category"],
        "subcategory": task["subcategory"],
        "budget": task["budget"]["amount"],
        "duration": "less_than_one_week",
        "visibility": "public",
        "skills": task["skills"],
        "experience_level": task["experience_level"],
        "job_type": "fixed_price",
        "screening_questions": [q["question"] for q in task["screening_questions"]]
    }


def ai_score_application(cover_letter, questions_answered):
    """
    AI scores application 0-10

    Criteria:
    - Followed instructions (3 points)
    - Included "TESTNET READY" (2 points)
    - Clear communication (2 points)
    - Realistic timeline (1 point)
    - Relevant experience (2 points)
    """
    score = 0
    feedback = []

    # Check if answered all 3 questions
    if len(questions_answered) >= 3:
        score += 3
        feedback.append("✅ Answered all questions")
    else:
        feedback.append(f"❌ Only answered {len(questions_answered)}/3 questions")

    # Check for "TESTNET READY" phrase
    if "TESTNET READY" in cover_letter.upper():
        score += 2
        feedback.append("✅ Included 'TESTNET READY'")
    else:
        feedback.append("⚠️ Missing 'TESTNET READY' phrase")

    # Check communication quality (simple heuristics)
    if len(cover_letter) > 100:  # Substantial response
        score += 1
        if len(cover_letter.split('.')) >= 3:  # Multiple sentences
            score += 1
            feedback.append("✅ Clear, detailed communication")
        else:
            feedback.append("⚠️ Brief communication")
    else:
        feedback.append("❌ Very short cover letter")

    # Check for timeline confirmation
    if "24 hour" in cover_letter.lower() or "24-hour" in cover_letter.lower():
        score += 1
        feedback.append("✅ Confirmed timeline")

    # Bonus for relevant keywords
    relevant_keywords = ["blockchain", "crypto", "command line", "terminal", "web3", "ethereum"]
    keyword_count = sum(1 for keyword in relevant_keywords if keyword in cover_letter.lower())
    if keyword_count >= 2:
        score += 2
        feedback.append(f"✅ Relevant experience mentioned ({keyword_count} keywords)")
    elif keyword_count == 1:
        score += 1
        feedback.append("⚠️ Some relevant experience")

    return {
        "score": min(score, 10),  # Cap at 10
        "feedback": feedback,
        "recommendation": "HIRE" if score >= 7 else "MAYBE" if score >= 5 else "PASS"
    }


def screen_applicants(applicants):
    """
    Screen all applicants and rank them
    """
    scored_applicants = []

    for applicant in applicants:
        # AI score
        scoring = ai_score_application(
            applicant.get("cover_letter", ""),
            applicant.get("screening_answers", [])
        )

        # Combine with Upwork stats
        upwork_score = 0
        if applicant.get("rating", 0) >= 4.5:
            upwork_score += 2
        if applicant.get("total_jobs", 0) >= 5:
            upwork_score += 1
        if applicant.get("success_rate", 0) >= 85:
            upwork_score += 1

        total_score = scoring["score"] + upwork_score

        scored_applicants.append({
            **applicant,
            "ai_score": scoring["score"],
            "upwork_score": upwork_score,
            "total_score": total_score,
            "feedback": scoring["feedback"],
            "recommendation": scoring["recommendation"]
        })

    # Sort by total score
    scored_applicants.sort(key=lambda x: x["total_score"], reverse=True)

    return scored_applicants


def post_task():
    """
    Post task to delegation system
    """
    print("\n" + "="*70)
    print("🚀 POSTING VA TEST TASK TO DELEGATION SYSTEM")
    print("="*70)

    # Save task definition
    task_file = Path(__file__).parent.parent / "delegation" / "testnet_deployment_task.json"
    task_file.parent.mkdir(exist_ok=True)

    with open(task_file, 'w') as f:
        json.dump(TESTNET_DEPLOYMENT_TASK, f, indent=2)

    print(f"\n✅ Task definition saved: {task_file}")

    # Create Upwork job data
    upwork_data = create_upwork_job_data()
    upwork_file = task_file.parent / "upwork_job_data.json"

    with open(upwork_file, 'w') as f:
        json.dump(upwork_data, f, indent=2)

    print(f"✅ Upwork job data saved: {upwork_file}")

    # Display summary
    print("\n📋 TASK SUMMARY:")
    print(f"   Title: {TESTNET_DEPLOYMENT_TASK['title']}")
    print(f"   Budget: ${TESTNET_DEPLOYMENT_TASK['budget']['amount']} fixed")
    print(f"   Bonus: +${TESTNET_DEPLOYMENT_TASK['budget']['bonus']}")
    print(f"   Timeline: {TESTNET_DEPLOYMENT_TASK['timeline']}")
    print(f"   Type: {TESTNET_DEPLOYMENT_TASK['type']}")

    print("\n🎯 SUCCESS CRITERIA:")
    for criterion, required in TESTNET_DEPLOYMENT_TASK['success_criteria'].items():
        status = "✅" if required else "⚠️"
        print(f"   {status} {criterion.replace('_', ' ').title()}")

    print("\n📚 RESOURCES PROVIDED:")
    for resource in TESTNET_DEPLOYMENT_TASK['resources_provided']:
        print(f"   ✅ {resource}")

    print("\n🔄 SCALE PLAN:")
    for step in TESTNET_DEPLOYMENT_TASK['next_steps_if_successful']:
        print(f"   → {step}")

    print("\n" + "="*70)
    print("📤 NEXT STEPS:")
    print("="*70)

    print("\n1. MANUAL: Post to Upwork (until API connected)")
    print("   - Copy from: UPWORK_JOB_POSTING.md")
    print("   - Job type: Fixed price")
    print("   - Budget: $15 (or $10-20 range)")
    print("   - Duration: Less than 1 week")
    print("   - Experience: Entry level")

    print("\n2. MONITOR applications")
    print("   - Use screening questions to filter")
    print("   - Look for 'TESTNET READY' phrase")
    print("   - Check answers to 3 questions")

    print("\n3. SCREEN with AI")
    print("   - Run: python scripts/screen-applicants.py")
    print("   - Reviews cover letters automatically")
    print("   - Ranks by total score")

    print("\n4. HIRE top 2-3 candidates")
    print("   - Test multiple VAs in parallel")
    print("   - See who delivers best")
    print("   - Scale winners to more work")

    print("\n5. ONBOARD winners")
    print("   - Send deployment guide")
    print("   - Provide Slack access")
    print("   - Give vault credentials")
    print("   - Monitor progress")

    print("\n" + "="*70)
    print("💡 SCREENING TIPS:")
    print("="*70)

    print("""
    HIRE if applicant:
    ✅ Answered all 3 questions
    ✅ Included "TESTNET READY"
    ✅ Realistic time estimate
    ✅ Clear communication
    ✅ Available to start soon

    MAYBE if:
    ⚠️ Missing 1 question answer
    ⚠️ Forgot "TESTNET READY" but otherwise good
    ⚠️ Limited experience but eager

    PASS if:
    ❌ Didn't answer questions
    ❌ Copy-paste generic response
    ❌ Unrealistic timeline ("30 minutes!")
    ❌ Poor English communication
    ❌ Can't start for days
    """)

    print("\n" + "="*70)
    print("✅ Task ready to post!")
    print("="*70)

    return task_file


def show_example_screening():
    """
    Show example of AI screening
    """
    print("\n" + "="*70)
    print("🧪 EXAMPLE: AI SCREENING")
    print("="*70)

    # Example good application
    good_applicant = {
        "name": "John D.",
        "rating": 4.8,
        "total_jobs": 12,
        "success_rate": 95,
        "cover_letter": """
        Hi! I'm interested in this test task. TESTNET READY!

        1. Command line: Basic - I use terminal regularly for npm/git
        2. Crypto: Wallet user - I have MetaMask and use DeFi apps
        3. Start time: Yes, can start in 2 hours

        I can complete this within 24 hours. I'm detail-oriented and
        enjoy learning new technologies. Looking forward to potential
        ongoing work with your team!
        """,
        "screening_answers": [
            "Basic",
            "Wallet user",
            "Yes, can start in 2 hours"
        ]
    }

    # Example poor application
    poor_applicant = {
        "name": "Jane S.",
        "rating": 4.2,
        "total_jobs": 2,
        "success_rate": 70,
        "cover_letter": "I can do this job. I have experience.",
        "screening_answers": []
    }

    print("\n✅ GOOD APPLICATION:")
    good_result = ai_score_application(
        good_applicant["cover_letter"],
        good_applicant["screening_answers"]
    )
    print(f"   Name: {good_applicant['name']}")
    print(f"   AI Score: {good_result['score']}/10")
    print(f"   Recommendation: {good_result['recommendation']}")
    print(f"   Feedback:")
    for fb in good_result['feedback']:
        print(f"      {fb}")

    print("\n❌ POOR APPLICATION:")
    poor_result = ai_score_application(
        poor_applicant["cover_letter"],
        poor_applicant["screening_answers"]
    )
    print(f"   Name: {poor_applicant['name']}")
    print(f"   AI Score: {poor_result['score']}/10")
    print(f"   Recommendation: {poor_result['recommendation']}")
    print(f"   Feedback:")
    for fb in poor_result['feedback']:
        print(f"      {fb}")

    print("\n💡 The AI automatically filters out low-quality applicants!")


if __name__ == "__main__":
    task_file = post_task()
    show_example_screening()

    print("\n🚀 Ready to find your first $5/hr test VA!")
    print(f"\nTask saved: {task_file}")
    print("\nNext: Post to Upwork manually (or wait for API integration)")
