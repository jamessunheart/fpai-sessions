#!/usr/bin/env python3
"""
AI Mission Triage System
=========================
Filters all missions through AI first to determine:
1. Can AI complete this autonomously? → AI works on it
2. Can AI do 80%+ of the work? → AI does work, human reviews
3. Does it require human judgment/access? → Goes to human queue

This ensures maximum AI leverage before human involvement.

Usage:
    python ai_mission_triage.py --scan           # Scan all missions
    python ai_mission_triage.py --triage M001   # Triage specific mission
    python ai_mission_triage.py --auto-assign   # Auto-assign to AI workers
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parents[1]
MISSIONS_DIR = ROOT_DIR / "docs" / "coordination" / "missions"
SPECS_DIR = ROOT_DIR / "fullpotential_ai" / "fullpotential_core" / "orchestration" / "missions" / "specs"
TRIAGE_DIR = ROOT_DIR / "orchestration" / "triage"
TRIAGE_DIR.mkdir(parents=True, exist_ok=True)

# Load environment
from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")


class MissionCategory(Enum):
    """Mission categories based on AI capability"""
    AI_AUTONOMOUS = "ai_autonomous"      # AI can complete 100% alone
    AI_PRIMARY = "ai_primary"            # AI does 80%+, human reviews
    AI_ASSISTED = "ai_assisted"          # AI does 50%, human completes
    HUMAN_PRIMARY = "human_primary"      # Human does most, AI assists
    HUMAN_ONLY = "human_only"            # Requires human (credentials, judgment)


class BlockerType(Enum):
    """Types of blockers that require human intervention"""
    CREDENTIALS = "credentials"          # API keys, passwords, access tokens
    PHYSICAL_ACTION = "physical_action"  # Real-world actions
    EXTERNAL_ACCOUNT = "external_account"  # Third-party account access
    SUBJECTIVE_JUDGMENT = "subjective_judgment"  # Creative/strategic decisions
    APPROVAL_REQUIRED = "approval_required"  # Needs sign-off
    FINANCIAL = "financial"              # Money movement
    LEGAL = "legal"                      # Legal implications
    UNKNOWN_DEPENDENCY = "unknown_dependency"  # Missing information


@dataclass
class TriageResult:
    """Result of triaging a mission"""
    mission_id: str
    title: str
    category: str
    ai_completion_estimate: float  # 0.0 to 1.0
    blockers: List[Dict[str, str]]
    ai_tasks: List[str]
    human_tasks: List[str]
    recommended_action: str
    estimated_ai_time_minutes: int
    estimated_human_time_minutes: int
    priority_score: float  # Higher = should do sooner
    reasoning: str
    triaged_at: str


# AI capability assessment rules
AI_CAPABILITIES = {
    "can_do": [
        "write code", "modify code", "refactor code",
        "create documentation", "update documentation",
        "write tests", "run tests",
        "analyze codebase", "search codebase",
        "create configurations", "edit configurations",
        "generate content", "edit content",
        "create templates", "modify templates",
        "database schema design", "SQL queries",
        "API design", "API implementation",
        "file operations", "directory operations",
        "git operations", "version control",
        "debugging", "error analysis",
        "performance analysis", "optimization",
        "security review", "code review",
    ],
    "cannot_do": [
        "access credentials", "manage passwords",
        "login to accounts", "authenticate",
        "make purchases", "financial transactions",
        "send real emails", "make phone calls",
        "physical actions", "hardware operations",
        "access private APIs without keys",
        "deploy to production without approval",
        "make legal decisions",
        "creative direction without guidance",
        "strategic business decisions",
        "interact with external services requiring auth",
    ]
}


def load_all_missions() -> List[Dict[str, Any]]:
    """Load all mission files from the missions directory"""
    missions = []
    
    # Load JSON missions
    for mission_file in MISSIONS_DIR.glob("*.json"):
        try:
            with open(mission_file) as f:
                mission = json.load(f)
                mission["_source_file"] = str(mission_file)
                missions.append(mission)
        except Exception as e:
            print(f"⚠️ Error loading {mission_file}: {e}")
    
    # Load spec-based missions
    for spec_file in SPECS_DIR.glob("M*_SPEC.md"):
        try:
            content = spec_file.read_text()
            mission_id = spec_file.stem.replace("_SPEC", "")
            missions.append({
                "mission_id": mission_id,
                "title": extract_title_from_spec(content),
                "type": "spec",
                "status": "available",
                "_source_file": str(spec_file),
                "_content": content
            })
        except Exception as e:
            print(f"⚠️ Error loading {spec_file}: {e}")
    
    return missions


def extract_title_from_spec(content: str) -> str:
    """Extract title from markdown spec"""
    for line in content.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return "Unknown Mission"


def analyze_mission_for_ai(mission: Dict[str, Any]) -> TriageResult:
    """Analyze a mission to determine AI vs human work split"""
    mission_id = mission.get("mission_id", "unknown")
    title = mission.get("title", "Unknown")
    
    # Extract all text content for analysis
    content_parts = []
    
    # From JSON missions
    if "instructions" in mission:
        content_parts.append(json.dumps(mission.get("instructions", {})))
    if "what_to_build" in mission:
        content_parts.append(json.dumps(mission.get("what_to_build", {})))
    if "build_steps" in mission:
        content_parts.append(json.dumps(mission.get("build_steps", [])))
    if "success_criteria" in mission:
        content_parts.append(json.dumps(mission.get("success_criteria", {})))
    
    # From spec-based missions
    if "_content" in mission:
        content_parts.append(mission["_content"])
    
    full_content = "\n".join(content_parts).lower()
    
    # Analyze blockers
    blockers = []
    
    # Check for credential requirements
    credential_keywords = ["api key", "api_key", "password", "secret", "token", "credential", 
                          "sendgrid", "stripe", "binance", "wordpress_app_password"]
    for kw in credential_keywords:
        if kw in full_content:
            blockers.append({
                "type": BlockerType.CREDENTIALS.value,
                "reason": f"Requires {kw}",
                "human_action": f"Provide or configure {kw}"
            })
    
    # Check for external account access
    account_keywords = ["login", "authenticate", "sign in", "account access", "wordpress admin"]
    for kw in account_keywords:
        if kw in full_content:
            blockers.append({
                "type": BlockerType.EXTERNAL_ACCOUNT.value,
                "reason": f"Requires {kw}",
                "human_action": f"Perform {kw} action"
            })
    
    # Check for financial actions
    financial_keywords = ["payment", "transaction", "purchase", "billing", "invoice"]
    for kw in financial_keywords:
        if kw in full_content:
            blockers.append({
                "type": BlockerType.FINANCIAL.value,
                "reason": f"Involves {kw}",
                "human_action": f"Approve/execute {kw}"
            })
    
    # Identify AI tasks
    ai_tasks = []
    ai_keywords = {
        "write code": ["fastapi", "python", "javascript", "typescript", "code", "implement", "build"],
        "create documentation": ["readme", "documentation", "docs", "spec"],
        "write tests": ["test", "pytest", "unittest", "testing"],
        "create templates": ["template", "jinja", "html"],
        "database design": ["schema", "database", "postgres", "sql", "redis"],
        "api implementation": ["api", "endpoint", "rest", "graphql"],
        "configuration": ["config", "settings", "env", "yaml", "json"],
    }
    
    for task, keywords in ai_keywords.items():
        for kw in keywords:
            if kw in full_content:
                ai_tasks.append(task)
                break
    
    ai_tasks = list(set(ai_tasks))  # Dedupe
    
    # Identify human tasks
    human_tasks = [b["human_action"] for b in blockers]
    
    # Calculate AI completion estimate
    total_work_items = len(ai_tasks) + len(blockers)
    if total_work_items == 0:
        ai_estimate = 0.5  # Unknown
    else:
        ai_estimate = len(ai_tasks) / total_work_items
    
    # Adjust based on blocker severity
    critical_blockers = [b for b in blockers if b["type"] in [
        BlockerType.CREDENTIALS.value, 
        BlockerType.FINANCIAL.value
    ]]
    if critical_blockers:
        ai_estimate = min(ai_estimate, 0.8)  # Cap at 80% if credentials needed
    
    # Determine category
    if ai_estimate >= 0.95 and not blockers:
        category = MissionCategory.AI_AUTONOMOUS.value
        recommended_action = "Assign to AI worker for autonomous completion"
    elif ai_estimate >= 0.8:
        category = MissionCategory.AI_PRIMARY.value
        recommended_action = "AI completes work, human provides credentials/approval"
    elif ai_estimate >= 0.5:
        category = MissionCategory.AI_ASSISTED.value
        recommended_action = "AI prepares work, human completes remaining tasks"
    elif ai_estimate >= 0.2:
        category = MissionCategory.HUMAN_PRIMARY.value
        recommended_action = "Human leads, AI assists with specific tasks"
    else:
        category = MissionCategory.HUMAN_ONLY.value
        recommended_action = "Assign to human contributor"
    
    # Estimate times
    base_time = mission.get("estimated_time_hours", 4) * 60  # Convert to minutes
    ai_time = int(base_time * ai_estimate * 0.3)  # AI is faster
    human_time = int(base_time * (1 - ai_estimate))
    
    # Priority score (higher = do sooner)
    priority_map = {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.3}
    base_priority = priority_map.get(mission.get("priority", "medium"), 0.5)
    # Boost priority for AI-completable missions (quick wins)
    priority_score = base_priority + (ai_estimate * 0.3)
    
    # Build reasoning
    reasoning = f"Mission '{title}' can be {int(ai_estimate * 100)}% completed by AI. "
    if ai_tasks:
        reasoning += f"AI can: {', '.join(ai_tasks[:3])}. "
    if blockers:
        reasoning += f"Blockers: {len(blockers)} items require human action. "
    reasoning += f"Recommended: {recommended_action}"
    
    return TriageResult(
        mission_id=mission_id,
        title=title,
        category=category,
        ai_completion_estimate=round(ai_estimate, 2),
        blockers=blockers,
        ai_tasks=ai_tasks,
        human_tasks=human_tasks,
        recommended_action=recommended_action,
        estimated_ai_time_minutes=ai_time,
        estimated_human_time_minutes=human_time,
        priority_score=round(priority_score, 2),
        reasoning=reasoning,
        triaged_at=datetime.now().isoformat()
    )


def triage_all_missions() -> List[TriageResult]:
    """Triage all available missions"""
    missions = load_all_missions()
    results = []
    
    print(f"\n🔍 Triaging {len(missions)} missions...\n")
    
    for mission in missions:
        result = analyze_mission_for_ai(mission)
        results.append(result)
        
        # Print summary
        emoji = {
            MissionCategory.AI_AUTONOMOUS.value: "🤖",
            MissionCategory.AI_PRIMARY.value: "🤖👤",
            MissionCategory.AI_ASSISTED.value: "👤🤖",
            MissionCategory.HUMAN_PRIMARY.value: "👤",
            MissionCategory.HUMAN_ONLY.value: "👤❌",
        }.get(result.category, "❓")
        
        print(f"{emoji} {result.mission_id}: {result.title[:40]}...")
        print(f"   AI: {int(result.ai_completion_estimate * 100)}% | Category: {result.category}")
        print(f"   Time: AI {result.estimated_ai_time_minutes}min + Human {result.estimated_human_time_minutes}min")
        if result.blockers:
            print(f"   Blockers: {len(result.blockers)}")
        print()
    
    return results


def save_triage_report(results: List[TriageResult]) -> Path:
    """Save triage results to a report file"""
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_missions": len(results),
        "summary": {
            "ai_autonomous": len([r for r in results if r.category == MissionCategory.AI_AUTONOMOUS.value]),
            "ai_primary": len([r for r in results if r.category == MissionCategory.AI_PRIMARY.value]),
            "ai_assisted": len([r for r in results if r.category == MissionCategory.AI_ASSISTED.value]),
            "human_primary": len([r for r in results if r.category == MissionCategory.HUMAN_PRIMARY.value]),
            "human_only": len([r for r in results if r.category == MissionCategory.HUMAN_ONLY.value]),
        },
        "missions": [asdict(r) for r in results]
    }
    
    # Sort by priority
    report["missions"].sort(key=lambda x: x["priority_score"], reverse=True)
    
    report_file = TRIAGE_DIR / f"triage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Triage report saved: {report_file}")
    
    # Also save latest
    latest_file = TRIAGE_DIR / "latest_triage.json"
    with open(latest_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report_file


def generate_optimized_mission_list(results: List[TriageResult]) -> Dict[str, Any]:
    """Generate an optimized mission list with AI-first ordering"""
    
    # Group by category
    ai_queue = []
    human_queue = []
    
    for r in sorted(results, key=lambda x: x.priority_score, reverse=True):
        mission_entry = {
            "id": r.mission_id,
            "title": r.title,
            "ai_percentage": int(r.ai_completion_estimate * 100),
            "priority": r.priority_score,
            "ai_time_minutes": r.estimated_ai_time_minutes,
            "human_time_minutes": r.estimated_human_time_minutes,
            "blockers": len(r.blockers),
            "action": r.recommended_action
        }
        
        if r.category in [MissionCategory.AI_AUTONOMOUS.value, MissionCategory.AI_PRIMARY.value]:
            ai_queue.append(mission_entry)
        else:
            human_queue.append(mission_entry)
    
    return {
        "generated_at": datetime.now().isoformat(),
        "ai_first_queue": ai_queue,
        "human_queue": human_queue,
        "stats": {
            "total_missions": len(results),
            "ai_completable": len(ai_queue),
            "needs_human": len(human_queue),
            "total_ai_time_hours": sum(r.estimated_ai_time_minutes for r in results) / 60,
            "total_human_time_hours": sum(r.estimated_human_time_minutes for r in results) / 60,
        }
    }


def main():
    parser = argparse.ArgumentParser(description="AI Mission Triage System")
    parser.add_argument("--scan", action="store_true", help="Scan and triage all missions")
    parser.add_argument("--triage", type=str, help="Triage a specific mission ID")
    parser.add_argument("--auto-assign", action="store_true", help="Auto-assign AI-completable missions to workers")
    parser.add_argument("--report", action="store_true", help="Generate optimized mission report")
    
    args = parser.parse_args()
    
    if args.scan or args.report:
        results = triage_all_missions()
        save_triage_report(results)
        
        # Generate optimized list
        optimized = generate_optimized_mission_list(results)
        optimized_file = TRIAGE_DIR / "optimized_missions.json"
        with open(optimized_file, 'w') as f:
            json.dump(optimized, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("📊 TRIAGE SUMMARY")
        print("="*60)
        print(f"Total Missions: {len(results)}")
        print(f"🤖 AI Autonomous: {optimized['stats']['ai_completable']}")
        print(f"👤 Needs Human: {optimized['stats']['needs_human']}")
        print(f"⏱️  Total AI Time: {optimized['stats']['total_ai_time_hours']:.1f} hours")
        print(f"⏱️  Total Human Time: {optimized['stats']['total_human_time_hours']:.1f} hours")
        print("\n🎯 AI-FIRST QUEUE (start here):")
        for m in optimized["ai_first_queue"][:5]:
            print(f"   • {m['id']}: {m['title'][:35]}... ({m['ai_percentage']}% AI)")
        
        print("\n👤 HUMAN QUEUE (after AI work):")
        for m in optimized["human_queue"][:5]:
            print(f"   • {m['id']}: {m['title'][:35]}... ({m['ai_percentage']}% AI)")
        
    elif args.triage:
        missions = load_all_missions()
        mission = next((m for m in missions if m.get("mission_id") == args.triage), None)
        if mission:
            result = analyze_mission_for_ai(mission)
            print(json.dumps(asdict(result), indent=2))
        else:
            print(f"❌ Mission {args.triage} not found")
            sys.exit(1)
    
    elif args.auto_assign:
        print("🚀 Auto-assign mode coming soon...")
        # This would trigger AI workers for autonomous missions
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

