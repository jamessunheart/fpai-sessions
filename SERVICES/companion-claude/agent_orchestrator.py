"""
Agent Orchestrator - Manages all AI agents (sessions & services)

This component:
- Tracks all 23 Claude sessions
- Monitors 64+ services
- Delegates work intelligently
- Prevents conflicts
- Coordinates multi-agent projects
"""

import json
import subprocess
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime


class AgentOrchestrator:
    """Orchestrates all AI agents and services"""

    def __init__(self):
        self.base_dir = Path("/Users/jamessunheart/Development")
        self.ssot_path = self.base_dir / "docs/coordination/SSOT.json"
        self.scripts_dir = self.base_dir / "docs/coordination/scripts"
        self.sessions_dir = self.base_dir / "docs/coordination/sessions/ACTIVE"

    def get_all_sessions(self) -> Dict:
        """Get status of all Claude sessions"""
        try:
            with open(self.ssot_path) as f:
                ssot = json.load(f)

            sessions = ssot.get("claude_sessions", {})

            # Enrich with additional info
            for session_id, session in sessions.items():
                session["session_number"] = session_id
                session["is_active"] = session.get("status") == "active"

            return {
                "total": len(sessions),
                "active": sum(1 for s in sessions.values() if s.get("status") == "active"),
                "inactive": sum(1 for s in sessions.values() if s.get("status") == "inactive"),
                "sessions": sessions
            }

        except Exception as e:
            print(f"Error getting sessions: {e}")
            return {"total": 0, "active": 0, "inactive": 0, "sessions": {}}

    def get_all_services(self) -> Dict:
        """Get status of all services"""
        try:
            with open(self.ssot_path) as f:
                ssot = json.load(f)

            services = ssot.get("services", {}).get("services", [])

            return {
                "total": len(services),
                "running": sum(1 for s in services if s.get("status") in ["running", "production"]),
                "stopped": sum(1 for s in services if s.get("status") == "stopped"),
                "services": services
            }

        except Exception as e:
            print(f"Error getting services: {e}")
            return {"total": 0, "running": 0, "stopped": 0, "services": []}

    def delegate(self, task: str, routing: Dict, prompts: Dict) -> List[Dict]:
        """
        Delegate a task to appropriate agents

        Args:
            task: The task description
            routing: Routing information (which agents)
            prompts: Encoded prompts for each agent

        Returns:
            List of delegation results
        """
        results = []

        targets = routing.get("targets", [])
        primary = routing.get("primary")

        for agent_id in targets:
            prompt = prompts.get(agent_id)

            if not prompt:
                continue

            is_primary = (agent_id == primary)

            # Create task file for the agent
            result = self._create_task_for_agent(
                agent_id,
                task,
                prompt,
                is_primary
            )

            results.append(result)

            # Send message to agent via coordination system
            self._send_message_to_agent(
                agent_id,
                f"New task assigned: {task}",
                priority="high" if is_primary else "normal"
            )

        return results

    def _create_task_for_agent(
        self,
        agent_id: str,
        task: str,
        prompt: str,
        is_primary: bool
    ) -> Dict:
        """Create a task file for an agent to pick up"""

        try:
            # Ensure sessions directory exists
            self.sessions_dir.mkdir(parents=True, exist_ok=True)

            # Create task file
            task_file = self.sessions_dir / f"{agent_id}-task-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"

            task_content = f"""# Task Assignment

**Assigned by:** Companion Claude
**Assigned at:** {datetime.now().isoformat()}
**Priority:** {"PRIMARY" if is_primary else "SUPPORTING"}

## Task

{task}

## Your Instructions

{prompt}

## Status

- [ ] Task acknowledged
- [ ] In progress
- [ ] Completed

## Notes

_Add your progress notes here_

---

**When complete:**
1. Check all boxes above
2. Update SSOT.json
3. Notify Companion Claude via `/message` endpoint
"""

            with open(task_file, "w") as f:
                f.write(task_content)

            return {
                "agent_id": agent_id,
                "task_file": str(task_file),
                "created": True,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "agent_id": agent_id,
                "created": False,
                "error": str(e)
            }

    def _send_message_to_agent(self, agent_id: str, message: str, priority: str = "normal"):
        """Send a message to an agent via session coordination"""

        try:
            # Use session-send-message.sh if available
            send_script = self.scripts_dir / "session-send-message.sh"

            if send_script.exists():
                subprocess.run(
                    [str(send_script), agent_id, "Task Assignment", message, priority],
                    check=True,
                    capture_output=True
                )

        except Exception as e:
            print(f"Error sending message to {agent_id}: {e}")

    def start_session(self, session_id: str) -> Dict:
        """Start a Claude session"""

        try:
            # Check if session exists
            sessions = self.get_all_sessions()

            if session_id not in sessions["sessions"]:
                return {
                    "success": False,
                    "error": f"Session {session_id} not found"
                }

            # For now, starting a session is manual
            # In the future, could integrate with terminal automation

            return {
                "success": True,
                "message": f"To start {session_id}, open a new terminal and run 'claude'",
                "session_id": session_id
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def stop_session(self, session_id: str) -> Dict:
        """Stop a Claude session"""

        # Mark session as inactive in SSOT
        try:
            with open(self.ssot_path) as f:
                ssot = json.load(f)

            if session_id in ssot.get("claude_sessions", {}):
                ssot["claude_sessions"][session_id]["status"] = "inactive"
                ssot["claude_sessions"][session_id]["marked_inactive_at"] = datetime.now().isoformat()

                with open(self.ssot_path, "w") as f:
                    json.dump(ssot, f, indent=2)

                return {
                    "success": True,
                    "session_id": session_id,
                    "status": "inactive"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_best_agent_for_task(self, task_description: str) -> str:
        """Find the best agent for a task"""

        sessions = self.get_all_sessions()["sessions"]

        # Simple keyword matching
        task_lower = task_description.lower()

        # Define expertise areas
        expertise = {
            "session-1": ["infrastructure", "architecture", "deployment", "systems"],
            "session-2": ["coordination", "architecture", "infrastructure"],
            "session-6": ["revenue", "treasury", "money", "finance"],
            "session-7": ["dashboard", "ui", "frontend", "visualization"],
            "session-13": ["coordination", "meta", "orchestration"],
            "session-15": ["activation", "execution", "launch", "revenue"],
        }

        best_match = None
        best_score = 0

        for session_id, keywords in expertise.items():
            score = sum(1 for kw in keywords if kw in task_lower)

            if score > best_score:
                best_score = score
                best_match = session_id

        # Default to Forge if no match
        return best_match or "session-1"

    def get_agent_workload(self, agent_id: str) -> Dict:
        """Get current workload for an agent"""

        # Count task files
        task_files = list(self.sessions_dir.glob(f"{agent_id}-task-*.md"))

        # Check for incomplete tasks
        incomplete = 0
        for task_file in task_files:
            try:
                with open(task_file) as f:
                    content = f.read()
                    if "- [ ] Completed" in content:
                        incomplete += 1
            except:
                pass

        return {
            "agent_id": agent_id,
            "total_tasks": len(task_files),
            "incomplete_tasks": incomplete,
            "completed_tasks": len(task_files) - incomplete,
            "workload_level": "low" if incomplete < 2 else "medium" if incomplete < 5 else "high"
        }

    def coordinate_multi_agent_task(self, task: str, agents: List[str], coordination_plan: Dict) -> Dict:
        """Coordinate a task across multiple agents"""

        # Create coordination file
        coord_file = self.sessions_dir / f"coordination-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"

        coord_content = f"""# Multi-Agent Coordination

**Task:** {task}
**Agents:** {', '.join(agents)}
**Created:** {datetime.now().isoformat()}

## Coordination Plan

{json.dumps(coordination_plan, indent=2)}

## Agent Assignments

"""

        for agent in agents:
            coord_content += f"\n### {agent}\n"
            coord_content += f"- [ ] Task assigned\n"
            coord_content += f"- [ ] In progress\n"
            coord_content += f"- [ ] Completed\n"

        coord_content += """
## Progress Notes

_Agents add notes here as work progresses_

## Completion

- [ ] All agents completed
- [ ] Results integrated
- [ ] Task verified
"""

        with open(coord_file, "w") as f:
            f.write(coord_content)

        return {
            "coordination_file": str(coord_file),
            "agents": agents,
            "created": True
        }


if __name__ == "__main__":
    # Test the orchestrator
    orchestrator = AgentOrchestrator()

    print("\n=== ALL SESSIONS ===")
    sessions = orchestrator.get_all_sessions()
    print(json.dumps(sessions, indent=2))

    print("\n=== ALL SERVICES ===")
    services = orchestrator.get_all_services()
    print(json.dumps(services, indent=2))
