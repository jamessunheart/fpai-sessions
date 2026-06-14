#!/usr/bin/env python3
"""
ARIA BUILDER INTENTS
====================

Classifies user messages into builder intents and extracts parameters.

Intent Categories:
- add_command: Adding a new Telegram command
- add_response: Adding a pattern response
- add_endpoint: Adding an API endpoint
- modify_code: Changing existing code
- read_code: Viewing/understanding code
- restart: Restarting a service
- query: Asking about something (not a build request)
"""

import re
import json
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger("aria.builder_intents")


class BuilderIntent(str, Enum):
    """Types of builder intents."""
    ADD_COMMAND = "add_command"
    ADD_RESPONSE = "add_response"
    ADD_ENDPOINT = "add_endpoint"
    MODIFY_CODE = "modify_code"
    READ_CODE = "read_code"
    RESTART = "restart"
    CONFIG_CHANGE = "config_change"
    QUERY = "query"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    """Risk levels for builder actions."""
    READ = "read"           # View only, auto-execute
    SAFE_WRITE = "safe"     # Add new, auto-approve
    MODIFY = "modify"       # Change existing, needs approval
    RISKY = "risky"         # Restart/delete, needs confirmation


@dataclass
class ParsedIntent:
    """Result of parsing a user message for builder intent."""
    intent: BuilderIntent
    risk_level: RiskLevel
    confidence: float  # 0-1
    target_file: Optional[str] = None
    target_function: Optional[str] = None
    command_name: Optional[str] = None
    description: str = ""
    parameters: Dict = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
    
    def to_dict(self) -> Dict:
        return {
            "intent": self.intent.value,
            "risk_level": self.risk_level.value,
            "confidence": self.confidence,
            "target_file": self.target_file,
            "target_function": self.target_function,
            "command_name": self.command_name,
            "description": self.description,
            "parameters": self.parameters
        }
    
    @property
    def is_builder_request(self) -> bool:
        """Check if this is a builder request (not just a query)."""
        return self.intent not in [BuilderIntent.QUERY, BuilderIntent.UNKNOWN]
    
    @property
    def needs_approval(self) -> bool:
        """Check if this action needs user approval."""
        return self.risk_level in [RiskLevel.MODIFY, RiskLevel.RISKY]


# Pattern definitions for intent detection
INTENT_PATTERNS = {
    BuilderIntent.ADD_COMMAND: [
        r"add\s+(?:a\s+)?(?:new\s+)?(?:command|cmd)\s+(?:called\s+|named\s+)?[/]?(\w+)",
        r"create\s+(?:a\s+)?(?:new\s+)?[/](\w+)\s+command",
        r"(?:new|add)\s+[/](\w+)",
        r"make\s+(?:a\s+)?(?:command|cmd)\s+(?:for|that|to)",
    ],
    BuilderIntent.ADD_RESPONSE: [
        r"(?:when|if)\s+(?:someone|i|user)\s+(?:say|says|ask|asks)",
        r"respond\s+(?:to|with)",
        r"(?:add|create)\s+(?:a\s+)?(?:response|reply)",
        r"answer\s+(?:with|when)",
    ],
    BuilderIntent.ADD_ENDPOINT: [
        r"add\s+(?:a\s+)?(?:new\s+)?(?:endpoint|api|route)",
        r"create\s+(?:a\s+)?(?:new\s+)?(?:endpoint|api|route)",
        r"(?:new|add)\s+[/]?(?:api|endpoint)\s+(?:for|that|to)",
    ],
    BuilderIntent.MODIFY_CODE: [
        r"(?:change|update|modify|fix|edit)\s+(?:the\s+)?(\w+)",
        r"(?:make|set)\s+(?:the\s+)?(\w+)\s+(?:to|=)",
        r"(?:refactor|improve|optimize)\s+(?:the\s+)?(\w+)",
    ],
    BuilderIntent.READ_CODE: [
        r"(?:show|display|view|see)\s+(?:me\s+)?(?:the\s+)?(?:code|file|function)",
        r"(?:what|how)\s+(?:does|is)\s+(\w+)",
        r"(?:explain|describe)\s+(?:the\s+)?(\w+)",
        r"(?:look|check)\s+(?:at\s+)?(?:the\s+)?(\w+)",
    ],
    BuilderIntent.RESTART: [
        r"restart\s+(?:the\s+)?(\w+)",
        r"reload\s+(?:the\s+)?(\w+)",
        r"stop\s+(?:and\s+)?start\s+(?:the\s+)?(\w+)",
    ],
    BuilderIntent.CONFIG_CHANGE: [
        r"(?:change|set|update)\s+(?:the\s+)?(?:config|setting|env)",
        r"(?:add|remove)\s+(?:the\s+)?(?:env|environment)",
    ],
}

# Risk levels by intent
INTENT_RISK = {
    BuilderIntent.ADD_COMMAND: RiskLevel.SAFE_WRITE,
    BuilderIntent.ADD_RESPONSE: RiskLevel.SAFE_WRITE,
    BuilderIntent.ADD_ENDPOINT: RiskLevel.MODIFY,
    BuilderIntent.MODIFY_CODE: RiskLevel.MODIFY,
    BuilderIntent.READ_CODE: RiskLevel.READ,
    BuilderIntent.RESTART: RiskLevel.RISKY,
    BuilderIntent.CONFIG_CHANGE: RiskLevel.RISKY,
    BuilderIntent.QUERY: RiskLevel.READ,
    BuilderIntent.UNKNOWN: RiskLevel.READ,
}

# File mapping for common targets
FILE_KEYWORDS = {
    "server": "server.py",
    "api": "server.py",
    "endpoint": "server.py",
    "action": "actions.py",
    "actions": "actions.py",
    "memory": "memory.py",
    "voice": "voice.py",
    "trading": "trading_intel.py",
    "proactive": "proactive.py",
    "response": "smart_responses.py",
    "responses": "smart_responses.py",
    "channel": "channels.py",
    "telegram": "channels.py",
}


class IntentParser:
    """
    Parses user messages to detect builder intents.
    
    Uses pattern matching for fast, cheap classification.
    Falls back to LLM for complex cases.
    """
    
    def __init__(self, use_llm_fallback: bool = True):
        self.use_llm_fallback = use_llm_fallback
    
    def parse(self, text: str) -> ParsedIntent:
        """
        Parse a user message for builder intent.
        
        Args:
            text: User's message
        
        Returns:
            ParsedIntent with detected intent and parameters
        """
        text_lower = text.lower().strip()
        
        # Check each intent pattern
        for intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    return self._build_intent(intent, text, match)
        
        # No pattern matched - it's probably a query or unknown
        if self._looks_like_question(text_lower):
            return ParsedIntent(
                intent=BuilderIntent.QUERY,
                risk_level=RiskLevel.READ,
                confidence=0.7,
                description=text
            )
        
        return ParsedIntent(
            intent=BuilderIntent.UNKNOWN,
            risk_level=RiskLevel.READ,
            confidence=0.3,
            description=text
        )
    
    def _build_intent(
        self,
        intent: BuilderIntent,
        text: str,
        match: re.Match
    ) -> ParsedIntent:
        """Build a ParsedIntent from a pattern match."""
        
        # Extract any captured groups
        groups = match.groups()
        
        # Determine target file
        target_file = self._detect_file(text)
        
        # Extract command name if present
        command_name = None
        if intent == BuilderIntent.ADD_COMMAND and groups:
            command_name = groups[0].lstrip('/')
        
        # Extract target function if modifying
        target_function = None
        if intent == BuilderIntent.MODIFY_CODE and groups:
            target_function = groups[0]
        
        return ParsedIntent(
            intent=intent,
            risk_level=INTENT_RISK[intent],
            confidence=0.85,
            target_file=target_file,
            target_function=target_function,
            command_name=command_name,
            description=text,
            parameters=self._extract_params(intent, text)
        )
    
    def _detect_file(self, text: str) -> Optional[str]:
        """Detect which file the user is referring to."""
        text_lower = text.lower()
        
        # Check for explicit file mention
        file_match = re.search(r'(\w+\.py)', text)
        if file_match:
            return file_match.group(1)
        
        # Check keyword mapping
        for keyword, filename in FILE_KEYWORDS.items():
            if keyword in text_lower:
                return filename
        
        return None
    
    def _extract_params(self, intent: BuilderIntent, text: str) -> Dict:
        """Extract parameters specific to the intent type."""
        params = {}
        
        if intent == BuilderIntent.ADD_COMMAND:
            # Try to extract what the command should do
            for phrase in ["that ", "to ", "which ", "for "]:
                if phrase in text.lower():
                    idx = text.lower().find(phrase) + len(phrase)
                    params["purpose"] = text[idx:].strip()
                    break
        
        elif intent == BuilderIntent.ADD_ENDPOINT:
            # Try to extract HTTP method
            for method in ["get", "post", "put", "delete", "patch"]:
                if method in text.lower():
                    params["method"] = method.upper()
                    break
            
            # Try to extract path
            path_match = re.search(r'[/](\w+(?:/\w+)*)', text)
            if path_match:
                params["path"] = path_match.group(0)
        
        elif intent == BuilderIntent.RESTART:
            # Extract service name
            service_match = re.search(r'restart\s+(?:the\s+)?(\w+)', text.lower())
            if service_match:
                params["service"] = service_match.group(1)
        
        return params
    
    def _looks_like_question(self, text: str) -> bool:
        """Check if text looks like a question (not a build request)."""
        question_starters = [
            "what", "how", "why", "when", "where", "who",
            "can you", "could you", "would you",
            "is there", "are there", "do you", "does"
        ]
        
        for starter in question_starters:
            if text.startswith(starter):
                return True
        
        return text.endswith("?")
    
    def is_in_scope(self, intent: ParsedIntent) -> Tuple[bool, str]:
        """
        Check if the intent is within allowed scope.
        
        Returns:
            (is_allowed, reason)
        """
        # Aria can only modify her own files
        ALLOWED_FILES = [
            "server.py", "actions.py", "smart_responses.py",
            "memory.py", "memory_v2.py", "proactive.py",
            "proactive_daemon.py", "voice.py", "channels.py",
            "trading_intel.py", ".env"
        ]
        
        if intent.target_file:
            if intent.target_file not in ALLOWED_FILES:
                return False, f"Cannot modify {intent.target_file} - outside Aria scope"
        
        # Cannot change certain configs via Telegram
        if intent.intent == BuilderIntent.CONFIG_CHANGE:
            text_lower = intent.description.lower()
            forbidden = ["api_key", "token", "secret", "password"]
            for word in forbidden:
                if word in text_lower:
                    return False, f"Cannot change {word} via Telegram for security"
        
        return True, "OK"


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_parser: Optional[IntentParser] = None


def get_parser() -> IntentParser:
    """Get or create the global parser instance."""
    global _parser
    if _parser is None:
        _parser = IntentParser()
    return _parser


def parse_intent(text: str) -> ParsedIntent:
    """Parse a message for builder intent."""
    return get_parser().parse(text)


def is_builder_request(text: str) -> bool:
    """Quick check if text looks like a builder request."""
    intent = parse_intent(text)
    return intent.is_builder_request


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    test_messages = [
        "add a command called /positions that shows trading positions",
        "create new /memory command",
        "add an endpoint for getting system health",
        "change the status function to include memory stats",
        "show me the code in server.py",
        "restart aria",
        "what is the current price of SOL?",
        "when someone asks about trading, respond with the latest signals",
        "how does the memory system work?",
        "update the config to increase timeout",
    ]
    
    parser = get_parser()
    
    print("=" * 60)
    print("INTENT PARSER TEST")
    print("=" * 60)
    
    for msg in test_messages:
        result = parser.parse(msg)
        in_scope, reason = parser.is_in_scope(result)
        
        print(f"\nMessage: {msg}")
        print(f"  Intent: {result.intent.value}")
        print(f"  Risk: {result.risk_level.value}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Target file: {result.target_file}")
        print(f"  Command: {result.command_name}")
        print(f"  Needs approval: {result.needs_approval}")
        print(f"  In scope: {in_scope} ({reason})")
        print(f"  Params: {result.parameters}")


