#!/usr/bin/env python3
"""
Task Automation Framework - CLI Tool
Command-line interface for task management
"""

import sys
import json
import os
from typing import Optional
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Task, TaskType, TaskStatus
from src.database import TaskDatabase
from src.task_analyzer import TaskAnalyzer


def create_task_cmd(args):
    """Create a new task"""
    db = TaskDatabase()

    task = Task(
        type=TaskType(args.type),
        service=args.service,
        description=args.description,
        params=json.loads(args.params) if args.params else {}
    )

    # Analyze task if requested
    if args.analyze and os.environ.get("ANTHROPIC_API_KEY"):
        print("🔍 Analyzing task...")
        analyzer = TaskAnalyzer()
        analysis = analyzer.analyze_task(task)

        print(f"\n📊 Analysis Results:")
        print(f"  Can Automate: {'✅ Yes' if analysis.can_automate else '❌ No'}")
        print(f"  Automation Level: {analysis.automation_level.upper()}")
        print(f"  Difficulty: {analysis.estimated_difficulty}")
        print(f"  Estimated Time: {analysis.estimated_time_minutes} minutes")

        if analysis.blockers_identified:
            print(f"  Blockers: {', '.join([b.value for b in analysis.blockers_identified])}")

        print(f"\n  Recommended Approach:")
        print(f"  {analysis.recommended_approach}")

        print(f"\n  Steps:")
        for i, step in enumerate(analysis.steps, 1):
            print(f"    {i}. {step}")

        if analysis.risks:
            print(f"\n  ⚠️  Risks:")
            for risk in analysis.risks:
                print(f"    - {risk}")

        # Update task with analysis results
        task.automation_level = analysis.automation_level
        if analysis.blockers_identified:
            task.blocker = analysis.blockers_identified[0]
            task.blocker_details = f"{len(analysis.blockers_identified)} blockers identified"

    db.create_task(task)
    print(f"\n✅ Task created: {task.id}")
    print(f"   Service: {task.service}")
    print(f"   Type: {task.type}")
    print(f"   Status: {task.status}")


def list_tasks_cmd(args):
    """List tasks"""
    db = TaskDatabase()

    status_filter = TaskStatus(args.status) if args.status else None
    tasks = db.list_tasks(
        status=status_filter,
        service=args.service,
        limit=args.limit
    )

    if not tasks:
        print("No tasks found")
        return

    print(f"\n📋 Tasks ({len(tasks)}):\n")

    for task in tasks:
        status_emoji = {
            "pending": "⏳",
            "in_progress": "🔄",
            "blocked": "🚧",
            "completed": "✅",
            "failed": "❌",
            "cancelled": "🚫"
        }.get(task.status, "❓")

        automation_emoji = {
            "full": "🤖",
            "semi": "🤝",
            "manual": "👤"
        }.get(task.automation_level, "")

        print(f"{status_emoji} {task.id}")
        print(f"   Service: {task.service}")
        print(f"   Type: {task.type}")
        print(f"   Status: {task.status} {automation_emoji}")
        print(f"   Created: {task.created_at.strftime('%Y-%m-%d %H:%M')}")

        if task.blocker:
            print(f"   Blocker: {task.blocker}")

        if task.error_message:
            print(f"   Error: {task.error_message}")

        print()


def show_task_cmd(args):
    """Show task details"""
    db = TaskDatabase()
    task = db.get_task(args.task_id)

    if not task:
        print(f"❌ Task not found: {args.task_id}")
        return

    print(f"\n📄 Task: {task.id}\n")
    print(f"Service: {task.service}")
    print(f"Type: {task.type}")
    print(f"Description: {task.description}")
    print(f"Status: {task.status}")
    print(f"Automation Level: {task.automation_level or 'Not analyzed'}")
    print(f"Priority: {task.priority}/10")
    print(f"Created: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

    if task.started_at:
        print(f"Started: {task.started_at.strftime('%Y-%m-%d %H:%M:%S')}")

    if task.completed_at:
        print(f"Completed: {task.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        duration = (task.completed_at - task.started_at).total_seconds() / 60
        print(f"Duration: {duration:.1f} minutes")

    if task.blocker:
        print(f"\n🚧 Blocker: {task.blocker}")
        if task.blocker_details:
            print(f"   Details: {task.blocker_details}")

    if task.params:
        print(f"\n📦 Parameters:")
        print(json.dumps(task.params, indent=2))

    if task.result:
        print(f"\n✅ Result:")
        print(json.dumps(task.result, indent=2))

    if task.error_message:
        print(f"\n❌ Error: {task.error_message}")

    if task.logs:
        print(f"\n📝 Logs:")
        for log in task.logs:
            print(f"   {log}")


def stats_cmd(args):
    """Show task statistics"""
    db = TaskDatabase()
    stats = db.get_stats()

    print(f"\n📊 Task Statistics\n")
    print(f"Total Tasks: {stats['total']}")
    print(f"Completed: {stats['completed']}")
    print(f"Blocked: {stats['blocked']}")
    print(f"Success Rate: {stats['success_rate']}%")

    print(f"\n📈 Status Breakdown:")
    for status, count in stats['status_breakdown'].items():
        print(f"  {status}: {count}")


def suggest_cmd(args):
    """Suggest service for task"""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not set")
        return

    analyzer = TaskAnalyzer()
    suggestion = analyzer.suggest_service(args.description, args.category)

    print(f"\n💡 Service Suggestion\n")
    print(f"Recommended: {suggestion['recommended_service']}")
    print(f"Reason: {suggestion['reason']}")
    print(f"Setup Complexity: {suggestion['setup_complexity']}")
    print(f"Free Tier: {suggestion['free_tier_limits']}")

    if suggestion.get('alternatives'):
        print(f"\nAlternatives:")
        for alt in suggestion['alternatives']:
            print(f"  - {alt}")


def main():
    parser = argparse.ArgumentParser(
        description="Task Automation Framework CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create task
    create_parser = subparsers.add_parser("create", help="Create a new task")
    create_parser.add_argument("type", choices=[t.value for t in TaskType], help="Task type")
    create_parser.add_argument("service", help="Service name (e.g., sendgrid, mailgun)")
    create_parser.add_argument("description", help="Task description")
    create_parser.add_argument("--params", help="JSON parameters")
    create_parser.add_argument("--analyze", action="store_true", help="Analyze task with AI")
    create_parser.set_defaults(func=create_task_cmd)

    # List tasks
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("--status", choices=[s.value for s in TaskStatus], help="Filter by status")
    list_parser.add_argument("--service", help="Filter by service")
    list_parser.add_argument("--limit", type=int, default=50, help="Limit results")
    list_parser.set_defaults(func=list_tasks_cmd)

    # Show task
    show_parser = subparsers.add_parser("show", help="Show task details")
    show_parser.add_argument("task_id", help="Task ID")
    show_parser.set_defaults(func=show_task_cmd)

    # Stats
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    stats_parser.set_defaults(func=stats_cmd)

    # Suggest
    suggest_parser = subparsers.add_parser("suggest", help="Suggest service for task")
    suggest_parser.add_argument("description", help="Task description")
    suggest_parser.add_argument("--category", default="email", help="Service category")
    suggest_parser.set_defaults(func=suggest_cmd)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
