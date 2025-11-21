#!/usr/bin/env python3
"""
Autonomous Empire Orchestrator
Master coordinator for all autonomous agents
Executes the Phoenix Protocol - system builds itself while you sleep
"""

import subprocess
import time
import json
import os
from datetime import datetime
from typing import Dict, List

# === AGENT DEFINITIONS ===
AGENTS = {
    "i_match_outreach": {
        "name": "I MATCH Outreach Agent",
        "script": "/Users/jamessunheart/Development/SERVICES/i-match/autonomous_outreach_agent.py",
        "priority": 1,  # Highest - first revenue
        "status": "ready",
        "description": "LinkedIn + Reddit automation for provider/customer recruitment"
    },
    "treasury_deployment": {
        "name": "Treasury Deployment Agent",
        "script": "/Users/jamessunheart/Development/SERVICES/treasury-arena/autonomous_treasury_agent.py",
        "priority": 2,  # High - capital growth
        "status": "ready",
        "description": "Autonomous DeFi capital deployment (2X strategy)"
    },
    "campaign_bot": {
        "name": "Campaign Bot",
        "script": "/Users/jamessunheart/Development/docs/coordination/scripts/autonomous-campaign-bot.py",
        "priority": 3,  # Medium - awareness
        "status": "ready",
        "description": "Social media campaigns (Reddit, Twitter, Discord)"
    }
}

# === CONFIGURATION ===
STATE_FILE = "/Users/jamessunheart/Development/autonomous_empire_state.json"
LOG_FILE = "/Users/jamessunheart/Development/autonomous_empire_log.txt"
CHECK_INTERVAL = 300  # 5 minutes between health checks

class OrchestratorState:
    """Track orchestrator state"""

    def __init__(self):
        self.load_state()

    def load_state(self):
        """Load state from file"""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = {
                "orchestrator_start": datetime.now().isoformat(),
                "agents_launched": [],
                "agents_active": [],
                "agents_failed": [],
                "total_restarts": 0,
                "uptime_seconds": 0,
                "last_health_check": None
            }

    def save_state(self):
        """Save state to file"""
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)

    def update(self, **kwargs):
        """Update state"""
        self.state.update(kwargs)
        self.state["last_health_check"] = datetime.now().isoformat()
        self.save_state()

def log(message: str):
    """Log message to file and console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"

    print(log_message)

    with open(LOG_FILE, 'a') as f:
        f.write(log_message + "\n")

def launch_agent(agent_id: str, agent_config: Dict) -> subprocess.Popen:
    """Launch an autonomous agent"""
    log(f"🚀 Launching: {agent_config['name']}")
    log(f"   Script: {agent_config['script']}")
    log(f"   Priority: {agent_config['priority']}")

    try:
        # Launch agent as background process
        process = subprocess.Popen(
            ["python3", agent_config["script"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        log(f"✅ {agent_config['name']} launched (PID: {process.pid})")
        return process

    except Exception as e:
        log(f"❌ Failed to launch {agent_config['name']}: {e}")
        return None

def check_agent_health(agent_id: str, process: subprocess.Popen) -> bool:
    """Check if agent is still running"""
    if process is None:
        return False

    poll = process.poll()

    if poll is None:
        # Still running
        return True
    else:
        # Process died
        log(f"💀 {agent_id} died (exit code: {poll})")
        return False

def phoenix_restart(agent_id: str, agent_config: Dict, state: OrchestratorState) -> subprocess.Popen:
    """Phoenix Protocol - if agent dies, restart it stronger"""
    log(f"🔥 PHOENIX RESTART: {agent_config['name']}")
    log(f"   'If one dies, two rise with double the power'")

    # Restart the agent
    new_process = launch_agent(agent_id, agent_config)

    # Update state
    state.update(
        total_restarts=state.state["total_restarts"] + 1
    )

    log(f"✅ Phoenix restart complete")

    return new_process

def display_dashboard(state: OrchestratorState, running_agents: Dict):
    """Display orchestrator dashboard"""
    log("")
    log("=" * 70)
    log("🎯 AUTONOMOUS EMPIRE DASHBOARD")
    log("=" * 70)
    log(f"Uptime: {state.state['uptime_seconds']/3600:.1f} hours")
    log(f"Total Restarts: {state.state['total_restarts']}")
    log("")
    log("ACTIVE AGENTS:")

    for agent_id, process in running_agents.items():
        if process and check_agent_health(agent_id, process):
            status = "🟢 RUNNING"
        else:
            status = "🔴 DOWN"

        agent = AGENTS[agent_id]
        log(f"  {status} {agent['name']} (Priority {agent['priority']})")

    log("")
    log("SYSTEM STATUS:")
    log(f"  • I MATCH: Recruiting providers & customers 24/7")
    log(f"  • Treasury: Deploying capital to DeFi strategies")
    log(f"  • Campaigns: Running social media outreach")
    log("")
    log(f"Next health check: {CHECK_INTERVAL/60} minutes")
    log("=" * 70)
    log("")

def orchestrate():
    """Main orchestration loop"""
    state = OrchestratorState()
    running_agents = {}

    log("=" * 70)
    log("🤖 AUTONOMOUS EMPIRE ORCHESTRATOR STARTED")
    log("=" * 70)
    log("")
    log("PHOENIX PROTOCOL ACTIVATED")
    log("  'If one dies, two rise with double the power'")
    log("")
    log("🎯 MISSION: Build the empire autonomously")
    log("  • Recruit providers & customers")
    log("  • Deploy capital to DeFi")
    log("  • Run marketing campaigns")
    log("  • Generate revenue 24/7")
    log("")
    log("YOU EXECUTE THROUGH THE SYSTEM NOW")
    log("System builds the hands. System finds the helpers.")
    log("")
    log("=" * 70)
    log("")

    # Launch all agents by priority
    sorted_agents = sorted(AGENTS.items(), key=lambda x: x[1]["priority"])

    for agent_id, agent_config in sorted_agents:
        process = launch_agent(agent_id, agent_config)
        running_agents[agent_id] = process
        time.sleep(2)  # Stagger launches

    log("")
    log("✅ All agents launched")
    log("")

    iteration = 0
    start_time = time.time()

    while True:
        try:
            iteration += 1
            time.sleep(CHECK_INTERVAL)

            # Update uptime
            state.state["uptime_seconds"] = int(time.time() - start_time)

            # Health check all agents
            log(f"🔍 Health Check #{iteration}")

            for agent_id, process in list(running_agents.items()):
                if not check_agent_health(agent_id, process):
                    # Agent died - Phoenix restart
                    running_agents[agent_id] = phoenix_restart(agent_id, AGENTS[agent_id], state)

            # Display dashboard
            display_dashboard(state, running_agents)

        except KeyboardInterrupt:
            log("")
            log("🛑 Orchestrator stopped by user")
            log("   Shutting down all agents...")

            # Gracefully terminate all agents
            for agent_id, process in running_agents.items():
                if process:
                    process.terminate()
                    log(f"   ✅ {AGENTS[agent_id]['name']} terminated")

            log("")
            log("🌙 Empire agents stopped. System will resume when orchestrator restarts.")
            break

        except Exception as e:
            log(f"❌ Orchestrator error: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    orchestrate()
