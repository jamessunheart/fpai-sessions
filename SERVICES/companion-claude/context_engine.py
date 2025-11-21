"""
Context Engine - Monitors James's activity and builds understanding

This is the "awareness" system that knows:
- What you're working on
- Where you are
- What you've recently done
- What's blocking you
- What you might need next
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import psutil


class ContextEngine:
    """Monitors and understands James's current context"""

    def __init__(self, db_path: str = "context.db"):
        self.db_path = db_path
        self.base_dir = Path("/Users/jamessunheart/Development")
        self.ssot_path = self.base_dir / "docs/coordination/SSOT.json"
        self.init_database()

    def init_database(self):
        """Initialize SQLite database for context tracking"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Activity log
        c.execute('''CREATE TABLE IF NOT EXISTS activity_log
                     (timestamp TEXT, event_type TEXT, location TEXT,
                      details TEXT, context_snapshot TEXT)''')

        # Current state
        c.execute('''CREATE TABLE IF NOT EXISTS current_state
                     (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)''')

        # Patterns learned
        c.execute('''CREATE TABLE IF NOT EXISTS learned_patterns
                     (pattern_type TEXT, pattern_data TEXT,
                      confidence REAL, last_seen TEXT)''')

        conn.commit()
        conn.close()

    def get_current_context(self) -> Dict:
        """Get comprehensive current context"""
        return {
            "james_status": self._get_james_status(),
            "work_context": self._get_work_context(),
            "system_state": self._get_system_state(),
            "priorities": self._get_priorities(),
            "blockers": self._get_blockers(),
            "recent_activity": self._get_recent_activity(),
            "wins_today": self._get_wins_today(),
            "suggestions": self._generate_suggestions()
        }

    def _get_james_status(self) -> Dict:
        """Detect what James is currently doing"""
        status = {
            "activity": "unknown",
            "location": "unknown",
            "session_length": None,
            "last_active": None,
            "energy_level": self._estimate_energy_level(),
            "open_terminals": self._get_open_terminals(),
            "open_files": self._get_recently_modified_files()
        }

        # Find most recent terminal activity
        recent_commands = self._get_recent_terminal_commands()
        if recent_commands:
            last_cmd = recent_commands[0]
            status["last_active"] = last_cmd["timestamp"]
            status["location"] = last_cmd["cwd"]

            # Infer activity from location
            if "SERVICES/i-match" in last_cmd["cwd"]:
                status["activity"] = "Working on I MATCH"
            elif "SERVICES/companion-claude" in last_cmd["cwd"]:
                status["activity"] = "Building Companion Claude"
            elif "docs/coordination" in last_cmd["cwd"]:
                status["activity"] = "Session coordination"
            elif last_cmd["command"].startswith("git"):
                status["activity"] = "Git operations"

        return status

    def _get_work_context(self) -> Dict:
        """Understand current work focus"""
        context = {
            "current_focus": None,
            "project": None,
            "phase": None,
            "goal": None
        }

        # Check for active work indicators
        recent_files = self._get_recently_modified_files(minutes=30)

        if recent_files:
            # Infer from file paths
            for file in recent_files:
                if "i-match" in file:
                    context["current_focus"] = "I MATCH Launch"
                    context["project"] = "I MATCH"
                    context["phase"] = "Phase 1: First Revenue"
                    context["goal"] = "Get first paying customer"
                    break
                elif "companion-claude" in file:
                    context["current_focus"] = "AI Companion System"
                    context["project"] = "Companion Claude"
                    context["phase"] = "Initial Build"
                    context["goal"] = "Create proactive AI director"
                    break
                elif "treasury" in file:
                    context["current_focus"] = "Treasury Deployment"
                    context["project"] = "DeFi Yield Strategy"
                    context["phase"] = "Planning"
                    context["goal"] = "Deploy $373K for yield"
                    break

        return context

    def _get_system_state(self) -> Dict:
        """Get state of all systems"""
        state = {
            "services_online": 0,
            "services_total": 0,
            "sessions_active": 0,
            "git_changes": 0,
            "capital": "$373,261",
            "revenue": "$0",
            "last_ssot_update": None
        }

        # Read SSOT.json if available
        if self.ssot_path.exists():
            try:
                with open(self.ssot_path) as f:
                    ssot = json.load(f)

                state["sessions_active"] = ssot.get("session_count", {}).get("active", 0)
                state["git_changes"] = ssot.get("git_changes", 0)
                state["last_ssot_update"] = ssot.get("last_update")

                # Count online services
                server_status = ssot.get("server_status", {})
                state["services_online"] = sum(1 for v in server_status.values() if v == "online")
                state["services_total"] = len(server_status)

            except Exception as e:
                print(f"Error reading SSOT: {e}")

        return state

    def _get_priorities(self) -> List[Dict]:
        """Get current priority stack"""
        # Read from capital vision SSOT
        priorities = []

        capital_ssot = self.base_dir / "docs/coordination/CAPITAL_VISION_SSOT.md"
        if capital_ssot.exists():
            # Phase 1 is always top priority per vision
            priorities.append({
                "rank": 1,
                "title": "Phase 1: First Revenue (I MATCH)",
                "reason": "Critical path to sustainability",
                "roi": "Highest - validates entire model",
                "next_step": "Execute Reddit campaign"
            })

            priorities.append({
                "rank": 2,
                "title": "Treasury Deployment ($373K → Yield)",
                "reason": "$2-7K/month passive income",
                "roi": "High - reduces burn rate immediately",
                "next_step": "Choose deployment strategy"
            })

            priorities.append({
                "rank": 3,
                "title": "Infrastructure Hardening",
                "reason": "Prevent service failures",
                "roi": "Medium - enables scale",
                "next_step": "Ensure all core services online"
            })

        return priorities

    def _get_blockers(self) -> List[Dict]:
        """Identify current blockers"""
        blockers = []

        # Check for common blocker patterns
        recent_activity = self._get_recent_activity(hours=2)

        for activity in recent_activity:
            # Error in terminal
            if activity.get("type") == "command" and "error" in activity.get("output", "").lower():
                blockers.append({
                    "type": "error",
                    "description": "Command failed",
                    "details": activity.get("command"),
                    "when": activity.get("timestamp")
                })

            # Git conflict
            if activity.get("type") == "git" and "conflict" in activity.get("output", "").lower():
                blockers.append({
                    "type": "git_conflict",
                    "description": "Merge conflict detected",
                    "when": activity.get("timestamp")
                })

        # Check for decision blockers from logs
        # (These would be marked by sessions waiting for James)

        return blockers

    def _get_recent_activity(self, hours: int = 4) -> List[Dict]:
        """Get recent activity log"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        since = datetime.now() - timedelta(hours=hours)
        c.execute('''SELECT timestamp, event_type, location, details
                     FROM activity_log
                     WHERE timestamp > ?
                     ORDER BY timestamp DESC LIMIT 50''',
                  (since.isoformat(),))

        activities = []
        for row in c.fetchall():
            activities.append({
                "timestamp": row[0],
                "type": row[1],
                "location": row[2],
                "details": json.loads(row[3]) if row[3] else {}
            })

        conn.close()
        return activities

    def _get_wins_today(self) -> List[str]:
        """Identify wins/achievements today"""
        wins = []

        # Check git commits today
        try:
            result = subprocess.run(
                ["git", "log", "--since=midnight", "--oneline"],
                cwd=self.base_dir,
                capture_output=True,
                text=True
            )
            if result.stdout:
                commits = result.stdout.strip().split('\n')
                if commits and commits[0]:
                    wins.append(f"{len(commits)} commits today")
        except:
            pass

        # Check for completed tasks in activity log
        today_activity = self._get_recent_activity(hours=16)  # Since morning

        for activity in today_activity:
            if activity.get("type") == "task_complete":
                wins.append(activity.get("details", {}).get("task", "Task completed"))

        return wins

    def _generate_suggestions(self) -> List[Dict]:
        """Generate proactive suggestions"""
        suggestions = []

        context = self.get_current_context()

        # Suggest based on time without activity
        last_active = context["james_status"].get("last_active")
        if last_active:
            # Parse ISO timestamp
            last_time = datetime.fromisoformat(last_active.replace('Z', '+00:00'))
            inactive_minutes = (datetime.now() - last_time).total_seconds() / 60

            if inactive_minutes > 120:
                suggestions.append({
                    "type": "check_in",
                    "priority": "medium",
                    "message": f"No activity for {int(inactive_minutes)} minutes. Everything OK?",
                    "action": "Send check-in notification"
                })

        # Suggest based on blockers
        if context.get("blockers"):
            suggestions.append({
                "type": "blocker_help",
                "priority": "high",
                "message": f"{len(context['blockers'])} blocker(s) detected",
                "action": "Offer assistance with blockers"
            })

        # Suggest based on offline services
        system_state = context.get("system_state", {})
        if system_state.get("services_online", 0) < 5:
            suggestions.append({
                "type": "service_health",
                "priority": "medium",
                "message": f"Only {system_state['services_online']} services online",
                "action": "Offer to start critical services"
            })

        return suggestions

    def _get_recently_modified_files(self, minutes: int = 15) -> List[str]:
        """Get files modified in last N minutes"""
        cutoff = datetime.now().timestamp() - (minutes * 60)
        recent_files = []

        # Check common working directories
        search_dirs = [
            self.base_dir / "SERVICES",
            self.base_dir / "docs/coordination",
        ]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            for file in search_dir.rglob("*.py"):
                try:
                    if file.stat().st_mtime > cutoff:
                        recent_files.append(str(file))
                except:
                    pass

        return recent_files[:10]  # Top 10 most recent

    def _get_recent_terminal_commands(self, count: int = 20) -> List[Dict]:
        """Get recent terminal commands from history"""
        commands = []

        # Try to read from zsh history
        history_path = Path.home() / ".zsh_history"
        if history_path.exists():
            try:
                with open(history_path, 'rb') as f:
                    lines = f.readlines()

                # Parse last N commands
                for line in lines[-count:]:
                    try:
                        decoded = line.decode('utf-8', errors='ignore')
                        # Zsh history format: : timestamp:0;command
                        if ';' in decoded:
                            parts = decoded.split(';', 1)
                            if len(parts) == 2:
                                cmd = parts[1].strip()
                                commands.append({
                                    "command": cmd,
                                    "timestamp": datetime.now().isoformat(),
                                    "cwd": str(self.base_dir)
                                })
                    except:
                        continue
            except:
                pass

        return commands

    def _get_open_terminals(self) -> int:
        """Count open terminal windows"""
        try:
            # Count Terminal.app processes
            result = subprocess.run(
                ["pgrep", "-c", "Terminal"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        except:
            pass

        return 0

    def _estimate_energy_level(self) -> str:
        """Estimate James's energy level based on time and activity"""
        hour = datetime.now().hour

        # Simple heuristic based on time of day
        if 6 <= hour < 10:
            return "rising"
        elif 10 <= hour < 14:
            return "high"
        elif 14 <= hour < 17:
            return "moderate"
        elif 17 <= hour < 21:
            return "declining"
        else:
            return "low"

    def log_activity(self, event_type: str, location: str, details: Dict):
        """Log an activity event"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        context_snapshot = json.dumps(self.get_current_context())

        c.execute('''INSERT INTO activity_log
                     (timestamp, event_type, location, details, context_snapshot)
                     VALUES (?, ?, ?, ?, ?)''',
                  (datetime.now().isoformat(), event_type, location,
                   json.dumps(details), context_snapshot))

        conn.commit()
        conn.close()

    def update_state(self, key: str, value: str):
        """Update a state value"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''INSERT OR REPLACE INTO current_state
                     (key, value, updated_at) VALUES (?, ?, ?)''',
                  (key, value, datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def get_state(self, key: str) -> Optional[str]:
        """Get a state value"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('SELECT value FROM current_state WHERE key = ?', (key,))
        row = c.fetchone()

        conn.close()
        return row[0] if row else None


if __name__ == "__main__":
    # Test the context engine
    engine = ContextEngine()
    context = engine.get_current_context()

    print("\n=== CURRENT CONTEXT ===\n")
    print(json.dumps(context, indent=2))
