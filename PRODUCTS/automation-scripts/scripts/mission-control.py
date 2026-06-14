#!/usr/bin/env python3
"""
Mission Control - Unified Session Orchestrator
Directs all Claude sessions toward high-value goals with shared consciousness
"""

import json
import datetime
import os
from pathlib import Path
from typing import Dict, List, Optional

class MissionControl:
    """Central orchestrator for all Claude sessions"""

    def __init__(self):
        self.base_path = Path("/Users/jamessunheart/Development/docs/coordination")
        self.consciousness_path = self.base_path / "consciousness"
        self.consciousness_path.mkdir(exist_ok=True)

        # Core files
        self.goals_file = self.consciousness_path / "goals.json"
        self.knowledge_file = self.consciousness_path / "unified_knowledge.json"
        self.sessions_file = self.consciousness_path / "active_sessions.json"
        self.priorities_file = self.consciousness_path / "mission_priorities.json"

    def get_current_mission(self) -> Dict:
        """Get the highest priority mission for new sessions"""
        priorities = self._load_priorities()

        # Sort by priority score (urgency * impact * feasibility)
        sorted_missions = sorted(
            priorities.get("missions", []),
            key=lambda m: m.get("priority_score", 0),
            reverse=True
        )

        if sorted_missions:
            return sorted_missions[0]

        return {"mission": "general_support", "priority_score": 1}

    def register_session(self, session_id: str, capabilities: List[str], context: str) -> Dict:
        """Register a new session and assign mission"""
        sessions = self._load_sessions()

        # Assign mission based on capabilities and current priorities
        mission = self.get_current_mission()

        session_data = {
            "session_id": session_id,
            "started_at": datetime.datetime.now().isoformat(),
            "capabilities": capabilities,
            "context": context,
            "assigned_mission": mission,
            "status": "active",
            "last_heartbeat": datetime.datetime.now().isoformat()
        }

        sessions[session_id] = session_data
        self._save_sessions(sessions)

        return {
            "mission": mission,
            "shared_knowledge": self._get_relevant_knowledge(mission),
            "active_goals": self._get_active_goals(),
            "coordination_needed": self._check_coordination_opportunities(session_data)
        }

    def session_heartbeat(self, session_id: str, progress: Dict) -> Dict:
        """Update session progress and get new directives"""
        sessions = self._load_sessions()

        if session_id in sessions:
            sessions[session_id]["last_heartbeat"] = datetime.datetime.now().isoformat()
            sessions[session_id]["latest_progress"] = progress
            self._save_sessions(sessions)

            # Share learnings across sessions
            if "learnings" in progress:
                self._share_learnings(progress["learnings"])

            # Check if mission should be updated
            return {
                "continue": True,
                "mission_update": self._check_mission_update(session_id),
                "collaboration_requests": self._get_collaboration_requests(session_id)
            }

        return {"continue": False, "error": "Session not registered"}

    def share_learning(self, category: str, learning: str, impact: str = "medium"):
        """Share a learning across all sessions"""
        knowledge = self._load_knowledge()

        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "category": category,
            "learning": learning,
            "impact": impact,
            "applied_count": 0
        }

        if category not in knowledge:
            knowledge[category] = []

        knowledge[category].append(entry)
        self._save_knowledge(knowledge)

        print(f"📚 Shared learning: {category} - {learning}")

    def set_mission_priority(self, mission: str, urgency: int, impact: int, feasibility: int, description: str = ""):
        """Set or update a mission priority"""
        priorities = self._load_priorities()

        priority_score = urgency * impact * feasibility

        mission_data = {
            "mission": mission,
            "description": description,
            "urgency": urgency,  # 1-10
            "impact": impact,    # 1-10
            "feasibility": feasibility,  # 1-10
            "priority_score": priority_score,
            "set_at": datetime.datetime.now().isoformat(),
            "status": "active"
        }

        missions = priorities.get("missions", [])

        # Update if exists, otherwise add
        updated = False
        for i, m in enumerate(missions):
            if m["mission"] == mission:
                missions[i] = mission_data
                updated = True
                break

        if not updated:
            missions.append(mission_data)

        priorities["missions"] = missions
        self._save_priorities(priorities)

        print(f"🎯 Mission priority set: {mission} (score: {priority_score})")

    def get_unified_context(self) -> Dict:
        """Get complete unified context for any session"""
        return {
            "active_missions": self.get_current_mission(),
            "shared_knowledge": self._load_knowledge(),
            "active_goals": self._get_active_goals(),
            "active_sessions": self._load_sessions(),
            "recent_learnings": self._get_recent_learnings(hours=24)
        }

    def sync_with_server(self):
        """Sync consciousness with server at 198.54.123.234"""
        try:
            # Load server consciousness
            server_consciousness = self._load_server_consciousness()

            # Merge knowledge
            local_knowledge = self._load_knowledge()
            merged = self._merge_knowledge(local_knowledge, server_consciousness.get("knowledge", {}))
            self._save_knowledge(merged)

            # Upload local knowledge to server
            self._upload_to_server(merged)

            print("✅ Consciousness synced with server")
            return True
        except Exception as e:
            print(f"⚠️  Sync failed: {e}")
            return False

    # Helper methods

    def _load_priorities(self) -> Dict:
        if self.priorities_file.exists():
            return json.loads(self.priorities_file.read_text())
        return {"missions": []}

    def _save_priorities(self, data: Dict):
        self.priorities_file.write_text(json.dumps(data, indent=2))

    def _load_sessions(self) -> Dict:
        if self.sessions_file.exists():
            return json.loads(self.sessions_file.read_text())
        return {}

    def _save_sessions(self, data: Dict):
        self.sessions_file.write_text(json.dumps(data, indent=2))

    def _load_knowledge(self) -> Dict:
        if self.knowledge_file.exists():
            return json.loads(self.knowledge_file.read_text())
        return {}

    def _save_knowledge(self, data: Dict):
        self.knowledge_file.write_text(json.dumps(data, indent=2))

    def _get_active_goals(self) -> List[Dict]:
        if self.goals_file.exists():
            goals = json.loads(self.goals_file.read_text())
            return [g for g in goals.get("goals", []) if g.get("status") == "active"]
        return []

    def _get_relevant_knowledge(self, mission: Dict) -> List[Dict]:
        knowledge = self._load_knowledge()
        # Return knowledge relevant to mission
        relevant = []
        mission_name = mission.get("mission", "")
        for category, items in knowledge.items():
            if mission_name in category or category in mission_name:
                relevant.extend(items[-5:])  # Last 5 from each relevant category
        return relevant

    def _get_recent_learnings(self, hours: int = 24) -> List[Dict]:
        knowledge = self._load_knowledge()
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)

        recent = []
        for category, items in knowledge.items():
            for item in items:
                timestamp = datetime.datetime.fromisoformat(item["timestamp"])
                if timestamp > cutoff:
                    recent.append({**item, "category": category})

        return sorted(recent, key=lambda x: x["timestamp"], reverse=True)

    def _share_learnings(self, learnings: List[Dict]):
        for learning in learnings:
            self.share_learning(
                learning.get("category", "general"),
                learning.get("content", ""),
                learning.get("impact", "medium")
            )

    def _check_mission_update(self, session_id: str) -> Optional[Dict]:
        # Check if higher priority mission emerged
        current_mission = self.get_current_mission()
        sessions = self._load_sessions()

        if session_id in sessions:
            assigned = sessions[session_id].get("assigned_mission", {})
            if current_mission.get("priority_score", 0) > assigned.get("priority_score", 0) * 1.5:
                return current_mission

        return None

    def _get_collaboration_requests(self, session_id: str) -> List[Dict]:
        # Find other sessions that need collaboration
        sessions = self._load_sessions()
        requests = []

        for sid, sdata in sessions.items():
            if sid != session_id and sdata.get("needs_collaboration"):
                requests.append({
                    "session_id": sid,
                    "mission": sdata.get("assigned_mission"),
                    "request": sdata.get("collaboration_request")
                })

        return requests

    def _check_coordination_opportunities(self, session_data: Dict) -> List[str]:
        # Check if this session can coordinate with others
        opportunities = []
        sessions = self._load_sessions()

        for sid, sdata in sessions.items():
            if sid != session_data["session_id"]:
                # Check for complementary capabilities
                my_caps = set(session_data.get("capabilities", []))
                their_caps = set(sdata.get("capabilities", []))

                if my_caps & their_caps:  # Overlapping capabilities
                    opportunities.append(f"coordinate_with_{sid}")

        return opportunities

    def _load_server_consciousness(self) -> Dict:
        """Load consciousness from server"""
        import subprocess
        result = subprocess.run(
            ["ssh", "root@198.54.123.234", "cat /root/CONSCIOUSNESS/long_term.json"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {}

    def _upload_to_server(self, knowledge: Dict):
        """Upload knowledge to server"""
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json.dumps(knowledge, indent=2))
            temp_file = f.name

        subprocess.run([
            "scp", temp_file,
            "root@198.54.123.234:/root/CONSCIOUSNESS/unified_knowledge.json"
        ])

        os.unlink(temp_file)

    def _merge_knowledge(self, local: Dict, server: Dict) -> Dict:
        """Merge local and server knowledge bases"""
        merged = local.copy()

        for category, items in server.items():
            if category not in merged:
                merged[category] = []

            # Add server items that aren't in local
            for item in items:
                if item not in merged[category]:
                    merged[category].append(item)

        return merged


def main():
    """CLI interface for Mission Control"""
    import sys

    mc = MissionControl()

    if len(sys.argv) < 2:
        print("""
🎯 Mission Control - Unified Session Orchestrator

Commands:
  start <session-id> <context>     - Register new session
  heartbeat <session-id>            - Send heartbeat
  mission <name> <u> <i> <f> <desc> - Set mission priority (urgency, impact, feasibility 1-10)
  learn <category> <learning>       - Share learning across sessions
  status                            - Show current status
  sync                              - Sync with server consciousness
  context                           - Get unified context

Examples:
  ./mission-control.py mission dns_automation 9 8 7 "Automate all DNS management"
  ./mission-control.py learn deployment "Namecheap API requires all hosts set at once"
  ./mission-control.py sync
  ./mission-control.py status
        """)
        return

    command = sys.argv[1]

    if command == "start" and len(sys.argv) >= 4:
        session_id = sys.argv[2]
        context = sys.argv[3]
        result = mc.register_session(session_id, ["general"], context)
        print(json.dumps(result, indent=2))

    elif command == "mission" and len(sys.argv) >= 7:
        name = sys.argv[2]
        urgency = int(sys.argv[3])
        impact = int(sys.argv[4])
        feasibility = int(sys.argv[5])
        desc = " ".join(sys.argv[6:])
        mc.set_mission_priority(name, urgency, impact, feasibility, desc)

    elif command == "learn" and len(sys.argv) >= 4:
        category = sys.argv[2]
        learning = " ".join(sys.argv[3:])
        mc.share_learning(category, learning, "high")

    elif command == "status":
        context = mc.get_unified_context()
        print(json.dumps(context, indent=2))

    elif command == "sync":
        mc.sync_with_server()

    elif command == "context":
        context = mc.get_unified_context()
        print(json.dumps(context, indent=2))

    else:
        print(f"❌ Unknown command: {command}")


if __name__ == "__main__":
    main()
