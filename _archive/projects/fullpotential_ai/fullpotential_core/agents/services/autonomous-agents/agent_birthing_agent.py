#!/usr/bin/env python3
"""
👶 Agent Birthing Agent - Creates New Autonomous Agents
The meta-agent that births other agents based on system needs
Part of Full Potential AI Autonomous Intelligence System
"""

import asyncio
import anthropic
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional


class AgentBirthingAgent:
    """Meta-agent that creates other autonomous agents"""

    def __init__(self, api_key: str):
        self.name = "AgentBirthingAgent"
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5-20250929"

        # Agent registry
        self.created_agents = []
        self.agent_templates = self.load_templates()

    def load_templates(self) -> Dict[str, str]:
        """Load agent templates"""
        return {
            "base": """
class AutonomousAgent:
    def __init__(self, name: str, api_key: str, check_interval: int = 60):
        self.name = name
        self.client = anthropic.Anthropic(api_key=api_key)
        self.check_interval = check_interval
        self.running = False

    async def think(self, prompt: str, context: Dict = None) -> str:
        messages = [{
            "role": "user",
            "content": f"You are {self.name}. {prompt}"
        }]
        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=messages
        )
        return response.content[0].text

    async def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.utcnow().isoformat()
        print(f"[{timestamp}] [{self.name}] [{level}] {message}")

    async def run_cycle(self):
        raise NotImplementedError("Subclass must implement run_cycle")

    async def run_forever(self):
        self.running = True
        while self.running:
            try:
                await self.run_cycle()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                await self.log(f"Error: {e}", "ERROR")
                await asyncio.sleep(60)
"""
        }

    async def log(self, message: str, level: str = "INFO"):
        """Log birthing agent activity"""
        timestamp = datetime.utcnow().isoformat()
        log_entry = f"[{timestamp}] [{self.name}] [{level}] {message}"
        print(log_entry)

        try:
            with open(f"/tmp/agent_birthing.log", "a") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"Failed to write log: {e}")

    async def analyze_system_gaps(self) -> List[str]:
        """Analyze what agents are missing"""
        await self.log("Analyzing system for capability gaps...")

        # In production, this would query the agent registry
        # For now, return predefined needs
        gaps = [
            "defi_yield_agent",
            "risk_management_agent",
            "arbitrage_agent",
            "gas_optimizer_agent",
            "portfolio_rebalancer_agent"
        ]

        await self.log(f"Found {len(gaps)} capability gaps")
        return gaps

    async def design_agent(self, agent_type: str) -> Dict[str, Any]:
        """Design a new agent using Claude"""
        await self.log(f"Designing new agent: {agent_type}")

        # Create design prompt
        prompt = f"""Design a new autonomous agent for cryptocurrency treasury management.

Agent Type: {agent_type}

Requirements:
1. The agent must inherit from AutonomousAgent base class
2. Implement run_cycle() method with core logic
3. Include error handling and logging
4. Use async/await patterns
5. Be production-ready

Return a JSON design with:
- name: Agent class name
- purpose: What this agent does
- capabilities: List of capabilities
- data_sources: External APIs/data needed
- key_methods: Main methods to implement
- success_metrics: How to measure success

Be specific and practical."""

        messages = [{"role": "user", "content": prompt}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=messages
        )

        # Parse response
        design_text = response.content[0].text

        # Extract JSON (assuming Claude returns JSON)
        try:
            # Try to find JSON in response
            start = design_text.find('{')
            end = design_text.rfind('}') + 1
            if start != -1 and end > start:
                design = json.loads(design_text[start:end])
            else:
                # Fallback design
                design = {
                    "name": agent_type.title().replace("_", ""),
                    "purpose": f"Autonomous {agent_type}",
                    "capabilities": ["Monitor", "Execute", "Report"],
                    "design_raw": design_text
                }
        except json.JSONDecodeError:
            design = {
                "name": agent_type.title().replace("_", ""),
                "purpose": f"Autonomous {agent_type}",
                "design_raw": design_text
            }

        await self.log(f"Agent design complete: {design.get('name')}")
        return design

    async def generate_agent_code(self, design: Dict[str, Any]) -> str:
        """Generate complete agent code using Claude"""
        await self.log(f"Generating code for {design.get('name')}...")

        prompt = f"""Generate complete Python code for this autonomous agent.

Agent Design:
{json.dumps(design, indent=2)}

Base Template:
{self.agent_templates['base']}

Requirements:
1. Create a complete, production-ready Python file
2. Include all imports
3. Implement all key methods
4. Add comprehensive error handling
5. Include logging throughout
6. Add docstrings
7. Make it executable (#!/usr/bin/env python3)
8. Include main() function for testing

Return ONLY the complete Python code, no explanations."""

        messages = [{"role": "user", "content": prompt}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=messages
        )

        code = response.content[0].text

        # Clean up code (remove markdown if present)
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        await self.log(f"Generated {len(code)} characters of code")
        return code

    async def generate_tests(self, agent_code: str, agent_name: str) -> str:
        """Generate tests for the agent"""
        await self.log(f"Generating tests for {agent_name}...")

        prompt = f"""Generate pytest tests for this agent.

Agent Code:
{agent_code[:2000]}... (truncated)

Requirements:
1. Test initialization
2. Test key methods
3. Test error handling
4. Use pytest fixtures
5. Mock external dependencies
6. Test async methods properly

Return complete test file."""

        messages = [{"role": "user", "content": prompt}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=messages
        )

        tests = response.content[0].text

        if "```python" in tests:
            tests = tests.split("```python")[1].split("```")[0].strip()

        return tests

    async def birth_agent(self, agent_type: str) -> Dict[str, Any]:
        """Complete agent birth process"""
        await self.log(f"🤰 BIRTHING NEW AGENT: {agent_type}")

        birth_record = {
            "agent_type": agent_type,
            "birth_time": datetime.utcnow().isoformat(),
            "status": "in_progress"
        }

        try:
            # Step 1: Design
            design = await self.design_agent(agent_type)
            birth_record["design"] = design

            # Step 2: Generate code
            code = await self.generate_agent_code(design)
            birth_record["code_length"] = len(code)

            # Step 3: Generate tests
            tests = await self.generate_tests(code, design.get("name", agent_type))
            birth_record["test_length"] = len(tests)

            # Step 4: Save files
            agent_filename = f"/tmp/{agent_type}.py"
            test_filename = f"/tmp/test_{agent_type}.py"

            with open(agent_filename, "w") as f:
                f.write(code)

            with open(test_filename, "w") as f:
                f.write(tests)

            # Make executable
            os.chmod(agent_filename, 0o755)

            birth_record["agent_file"] = agent_filename
            birth_record["test_file"] = test_filename
            birth_record["status"] = "success"

            # Step 5: Register agent
            self.created_agents.append(birth_record)

            await self.log(f"👶 AGENT BORN: {design.get('name')} ({agent_type})")
            await self.log(f"📁 Code: {agent_filename}")
            await self.log(f"🧪 Tests: {test_filename}")

            # Save birth record
            self.save_birth_record(birth_record)

            return birth_record

        except Exception as e:
            await self.log(f"❌ BIRTH FAILED: {e}", "ERROR")
            birth_record["status"] = "failed"
            birth_record["error"] = str(e)
            return birth_record

    def save_birth_record(self, record: Dict[str, Any]):
        """Save birth record to file"""
        try:
            with open("/tmp/agent_births.jsonl", "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"Failed to save birth record: {e}")

    async def run_cycle(self):
        """One cycle - check for agent needs"""
        await self.log("Checking system for agent needs...")

        # Analyze gaps
        gaps = await self.analyze_system_gaps()

        if gaps:
            # For demo, birth first gap
            agent_type = gaps[0]
            await self.log(f"Gap detected: {agent_type}")

            # Birth the agent
            result = await self.birth_agent(agent_type)

            if result["status"] == "success":
                await self.log("✅ Agent birthing successful")
            else:
                await self.log("❌ Agent birthing failed", "ERROR")
        else:
            await self.log("✅ No capability gaps detected")

    async def birth_on_demand(self, agent_type: str, specification: str = None):
        """Birth an agent on demand (API endpoint)"""
        await self.log(f"On-demand birth request: {agent_type}")

        if specification:
            await self.log(f"Custom specification provided")

        return await self.birth_agent(agent_type)

    async def run_forever(self):
        """Main loop - monitor for agent needs"""
        await self.log("🚀 Agent Birthing Agent starting...")
        await self.log("Ready to birth new agents on demand or automatically")

        # For now, don't run continuous loop
        # In production, this would monitor system needs
        await self.log("Running in on-demand mode")
        await self.log("Call birth_on_demand(agent_type) to create agents")


async def main():
    """Run the agent birthing agent"""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not api_key:
        print("❌ No ANTHROPIC_API_KEY set")
        return

    agent = AgentBirthingAgent(api_key)

    print("👶 Full Potential AI - Agent Birthing Agent")
    print("=" * 60)

    # Example: Birth a DeFi yield agent
    print("\n🧬 Birthing example agent...")
    result = await agent.birth_agent("defi_yield_agent")

    if result["status"] == "success":
        print(f"\n✅ SUCCESS! Agent born:")
        print(f"   File: {result['agent_file']}")
        print(f"   Tests: {result['test_file']}")
        print(f"   Code: {result['code_length']} chars")
    else:
        print(f"\n❌ Birth failed: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())
