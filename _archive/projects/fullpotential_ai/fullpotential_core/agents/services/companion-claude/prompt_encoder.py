"""
Prompt Encoder - Converts your intentions into precise prompts for AI agents

This is the "translation layer" that takes what you want
and creates perfect prompts for each AI agent/service.
"""

import json
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime


class PromptEncoder:
    """Encodes human intentions into AI-ready prompts"""

    def __init__(self):
        self.base_dir = Path("/Users/jamessunheart/Development")
        self.ssot_path = self.base_dir / "docs/coordination/SSOT.json"
        self.session_capabilities = self._load_session_capabilities()
        self.service_specs = self._load_service_specs()

    def _load_session_capabilities(self) -> Dict:
        """Load what each session is good at"""
        try:
            with open(self.ssot_path) as f:
                ssot = json.load(f)

            capabilities = {}
            for session_num, session in ssot.get("claude_sessions", {}).items():
                capabilities[f"session-{session_num}"] = {
                    "role": session.get("role"),
                    "goal": session.get("goal"),
                    "specialties": self._infer_specialties(session)
                }

            return capabilities
        except Exception as e:
            print(f"Error loading session capabilities: {e}")
            return {}

    def _infer_specialties(self, session: Dict) -> List[str]:
        """Infer what a session is good at from role/goal"""
        specialties = []
        role = session.get("role", "").lower()
        goal = session.get("goal", "").lower()

        specialty_keywords = {
            "infrastructure": ["infrastructure", "architect", "forge", "systems"],
            "revenue": ["revenue", "catalyst", "money", "sales", "marketing"],
            "dashboard": ["dashboard", "ui", "frontend", "visual"],
            "coordination": ["coordination", "orchestration", "meta", "collective"],
            "deployment": ["deployment", "devops", "production"],
            "activation": ["activation", "execution", "launch"],
            "integration": ["integration", "nexus", "mesh", "api"],
            "testing": ["test", "qa", "quality"],
            "documentation": ["docs", "documentation", "guide"],
        }

        for specialty, keywords in specialty_keywords.items():
            if any(kw in role or kw in goal for kw in keywords):
                specialties.append(specialty)

        return specialties

    def _load_service_specs(self) -> Dict:
        """Load service specifications"""
        specs = {}

        services_dir = self.base_dir / "SERVICES"
        if services_dir.exists():
            for service_dir in services_dir.iterdir():
                if service_dir.is_dir():
                    spec_file = service_dir / "SPEC.md"
                    if spec_file.exists():
                        specs[service_dir.name] = {
                            "path": str(service_dir),
                            "spec_path": str(spec_file)
                        }

        return specs

    def encode_intent(self, intent: str, target: str = "auto") -> Dict:
        """
        Encode a human intention into AI prompts

        Args:
            intent: What you want to accomplish (e.g., "Get I MATCH to first revenue")
            target: Where to send ("auto", "all-sessions", "session-X", "service-Y")

        Returns:
            {
                "routing": {...},  # Which agents should receive this
                "prompts": {...},  # Encoded prompts for each agent
                "coordination": {...}  # How agents should coordinate
            }
        """

        # Parse intent
        intent_analysis = self._analyze_intent(intent)

        # Route to appropriate agents
        routing = self._route_intent(intent_analysis, target)

        # Generate prompts for each target
        prompts = {}
        for agent_id in routing["targets"]:
            prompts[agent_id] = self._generate_prompt(
                intent_analysis,
                agent_id,
                routing
            )

        # Generate coordination plan
        coordination = self._generate_coordination_plan(
            intent_analysis,
            routing,
            prompts
        )

        return {
            "intent": intent,
            "analysis": intent_analysis,
            "routing": routing,
            "prompts": prompts,
            "coordination": coordination,
            "encoded_at": datetime.now().isoformat()
        }

    def _analyze_intent(self, intent: str) -> Dict:
        """Analyze what the user wants"""
        analysis = {
            "raw_intent": intent,
            "intent_type": None,
            "domain": None,
            "action": None,
            "target_entity": None,
            "urgency": "normal",
            "complexity": "medium",
            "keywords": []
        }

        intent_lower = intent.lower()

        # Detect intent type
        if any(word in intent_lower for word in ["build", "create", "develop", "implement"]):
            analysis["intent_type"] = "build"
        elif any(word in intent_lower for word in ["fix", "debug", "solve", "resolve"]):
            analysis["intent_type"] = "fix"
        elif any(word in intent_lower for word in ["deploy", "launch", "ship", "publish"]):
            analysis["intent_type"] = "deploy"
        elif any(word in intent_lower for word in ["analyze", "investigate", "understand", "explain"]):
            analysis["intent_type"] = "analyze"
        elif any(word in intent_lower for word in ["optimize", "improve", "enhance", "upgrade"]):
            analysis["intent_type"] = "optimize"

        # Detect domain
        if "i match" in intent_lower or "imatch" in intent_lower:
            analysis["domain"] = "i-match"
            analysis["target_entity"] = "I MATCH service"
        elif "treasury" in intent_lower or "yield" in intent_lower or "defi" in intent_lower:
            analysis["domain"] = "treasury"
            analysis["target_entity"] = "Treasury system"
        elif "dashboard" in intent_lower:
            analysis["domain"] = "dashboard"
            analysis["target_entity"] = "Dashboard service"
        elif "session" in intent_lower or "agent" in intent_lower:
            analysis["domain"] = "coordination"
            analysis["target_entity"] = "Session coordination"

        # Detect urgency
        if any(word in intent_lower for word in ["urgent", "asap", "critical", "now", "immediately"]):
            analysis["urgency"] = "high"
        elif any(word in intent_lower for word in ["when possible", "eventually", "sometime"]):
            analysis["urgency"] = "low"

        # Extract keywords
        analysis["keywords"] = [
            word for word in intent_lower.split()
            if len(word) > 3 and word not in ["that", "this", "with", "from", "have", "been"]
        ]

        return analysis

    def _route_intent(self, analysis: Dict, target: str) -> Dict:
        """Determine which agents should handle this"""
        routing = {
            "targets": [],
            "primary": None,
            "supporting": [],
            "routing_strategy": None
        }

        if target == "all-sessions":
            # Broadcast to all active sessions
            routing["targets"] = list(self.session_capabilities.keys())
            routing["routing_strategy"] = "broadcast"

        elif target.startswith("session-"):
            # Direct to specific session
            routing["targets"] = [target]
            routing["primary"] = target
            routing["routing_strategy"] = "direct"

        elif target == "auto":
            # Intelligent routing based on intent
            routing = self._intelligent_routing(analysis)

        else:
            # Try to find service or session
            routing["targets"] = [target]
            routing["routing_strategy"] = "direct"

        return routing

    def _intelligent_routing(self, analysis: Dict) -> Dict:
        """Intelligently route based on intent analysis"""
        routing = {
            "targets": [],
            "primary": None,
            "supporting": [],
            "routing_strategy": "intelligent"
        }

        domain = analysis.get("domain")
        intent_type = analysis.get("intent_type")

        # Domain-based routing
        if domain == "i-match":
            routing["primary"] = "session-15"  # Activation Catalyst
            routing["supporting"] = ["session-1"]  # Forge for infrastructure
            routing["targets"] = [routing["primary"]] + routing["supporting"]

        elif domain == "treasury":
            routing["primary"] = "session-6"  # Catalyst - Revenue
            routing["supporting"] = ["session-1"]  # Infrastructure support
            routing["targets"] = [routing["primary"]] + routing["supporting"]

        elif domain == "dashboard":
            routing["primary"] = "session-7"  # Dashboard Hub
            routing["targets"] = [routing["primary"]]

        elif domain == "coordination":
            routing["primary"] = "session-13"  # Meta-Coordinator
            routing["targets"] = [routing["primary"]]

        else:
            # Default to Forge for infrastructure tasks
            routing["primary"] = "session-1"
            routing["targets"] = [routing["primary"]]

        # Intent-type modifications
        if intent_type == "deploy":
            # Always include Forge for deployment
            if "session-1" not in routing["targets"]:
                routing["supporting"].append("session-1")
                routing["targets"].append("session-1")

        return routing

    def _generate_prompt(self, analysis: Dict, agent_id: str, routing: Dict) -> str:
        """Generate a specific prompt for an agent"""

        intent = analysis["raw_intent"]
        agent_info = self.session_capabilities.get(agent_id, {})
        role = agent_info.get("role", "Assistant")

        is_primary = (agent_id == routing.get("primary"))

        prompt_parts = []

        # Context setting
        prompt_parts.append(f"**Role Context:** You are {role}")

        # Intent framing
        if is_primary:
            prompt_parts.append(f"**Primary Objective:** {intent}")
            prompt_parts.append(f"**Your Responsibility:** You are the primary agent for this task.")
        else:
            prompt_parts.append(f"**Overall Goal:** {intent}")
            prompt_parts.append(f"**Your Role:** Provide supporting assistance to {routing.get('primary')}")

        # Domain-specific context
        if analysis.get("domain"):
            prompt_parts.append(f"**Domain:** {analysis['domain']}")

        # Action guidance
        intent_type = analysis.get("intent_type")
        if intent_type == "build":
            prompt_parts.append("**Action:** Design and implement the solution. Focus on clean architecture and UDC compliance.")
        elif intent_type == "fix":
            prompt_parts.append("**Action:** Diagnose the issue, propose a fix, and implement it.")
        elif intent_type == "deploy":
            prompt_parts.append("**Action:** Prepare for deployment, verify readiness, and execute deployment safely.")
        elif intent_type == "analyze":
            prompt_parts.append("**Action:** Analyze thoroughly and provide detailed findings with recommendations.")

        # Coordination info
        if len(routing["targets"]) > 1:
            others = [t for t in routing["targets"] if t != agent_id]
            prompt_parts.append(f"**Coordination:** Work with {', '.join(others)} to accomplish this goal.")

        # Urgency
        urgency = analysis.get("urgency", "normal")
        if urgency == "high":
            prompt_parts.append("**Urgency:** HIGH - This is time-sensitive. Prioritize accordingly.")

        # Success criteria
        prompt_parts.append("**Success Criteria:**")
        prompt_parts.append("- Accomplish the stated objective")
        prompt_parts.append("- Follow UDC compliance (5 endpoints)")
        prompt_parts.append("- Report progress to Companion Claude")
        prompt_parts.append("- Update SSOT.json when complete")

        return "\n\n".join(prompt_parts)

    def _generate_coordination_plan(self, analysis: Dict, routing: Dict, prompts: Dict) -> Dict:
        """Create a coordination plan for multi-agent work"""

        plan = {
            "type": "sequential" if len(routing["targets"]) == 1 else "parallel",
            "primary_agent": routing.get("primary"),
            "phases": [],
            "communication_protocol": "session-send-message.sh",
            "completion_criteria": []
        }

        # Simple plan for single agent
        if len(routing["targets"]) == 1:
            plan["phases"] = [{
                "phase": 1,
                "agents": routing["targets"],
                "description": "Complete the task",
                "dependencies": []
            }]

        # Multi-agent coordination
        else:
            # Phase 1: Analysis (if needed)
            if analysis.get("intent_type") in ["analyze", "build"]:
                plan["phases"].append({
                    "phase": 1,
                    "agents": [routing["primary"]],
                    "description": "Analyze and plan approach",
                    "dependencies": []
                })

            # Phase 2: Parallel execution
            plan["phases"].append({
                "phase": 2,
                "agents": routing["targets"],
                "description": "Execute in parallel",
                "dependencies": [1] if len(plan["phases"]) > 0 else []
            })

            # Phase 3: Integration
            if len(routing["targets"]) > 2:
                plan["phases"].append({
                    "phase": 3,
                    "agents": [routing["primary"]],
                    "description": "Integrate results",
                    "dependencies": [2]
                })

        # Completion criteria
        plan["completion_criteria"] = [
            "Primary objective achieved",
            "All agents report completion",
            "SSOT.json updated",
            "James notified"
        ]

        return plan

    def encode_batch(self, intents: List[str], target: str = "auto") -> List[Dict]:
        """Encode multiple intents at once"""
        return [self.encode_intent(intent, target) for intent in intents]

    def encode_from_template(self, template_name: str, variables: Dict) -> Dict:
        """Encode using a template (for common patterns)"""

        templates = {
            "launch_service": {
                "intent": "Launch {service_name} service and get it to first revenue",
                "routing": "auto",
                "additional_context": {
                    "success_metric": "First paying customer",
                    "timeline": "ASAP"
                }
            },
            "fix_service": {
                "intent": "Fix {service_name} - {problem_description}",
                "routing": "session-1",
                "additional_context": {
                    "priority": "high"
                }
            },
            "build_feature": {
                "intent": "Build {feature_name} for {service_name}",
                "routing": "auto",
                "additional_context": {}
            }
        }

        if template_name not in templates:
            raise ValueError(f"Unknown template: {template_name}")

        template = templates[template_name]

        # Fill in variables
        intent = template["intent"].format(**variables)

        # Encode
        result = self.encode_intent(intent, template["routing"])

        # Add template context
        result["template"] = template_name
        result["template_variables"] = variables
        result["additional_context"] = template.get("additional_context", {})

        return result


if __name__ == "__main__":
    # Test the prompt encoder
    encoder = PromptEncoder()

    # Test encoding
    result = encoder.encode_intent("Get I MATCH to first revenue", "auto")

    print("\n=== PROMPT ENCODING ===\n")
    print(json.dumps(result, indent=2))

    print("\n=== GENERATED PROMPTS ===\n")
    for agent_id, prompt in result["prompts"].items():
        print(f"\n--- {agent_id} ---")
        print(prompt)
