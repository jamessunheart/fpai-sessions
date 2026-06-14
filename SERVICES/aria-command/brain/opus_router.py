#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - OPUS BRAIN ROUTER
========================================

Intelligent routing to the right model for the task.
Uses Claude Opus 4 for complex reasoning and architecture.
"""

import os
import re
import json
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum
import httpx

logger = logging.getLogger("aria.opus")

# ============================================================================
# CONFIGURATION
# ============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Model configurations
MODELS = {
    "opus": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",  # Best available - upgrade to opus when available
        "max_tokens": 8192,
        "context_window": 200000,
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015
    },
    "sonnet": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 8192,
        "context_window": 200000,
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015
    },
    "quick": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "max_tokens": 4096,
        "context_window": 128000,
        "cost_per_1k_input": 0.00015,
        "cost_per_1k_output": 0.0006
    },
    "flash": {
        "provider": "gemini",
        "model": "gemini-2.0-flash",
        "max_tokens": 8192,
        "context_window": 1000000,
        "cost_per_1k_input": 0.000075,
        "cost_per_1k_output": 0.0003
    }
}


class TaskComplexity(str, Enum):
    SIMPLE = "simple"      # Quick answers, status checks
    MODERATE = "moderate"  # Single file edits, explanations
    COMPLEX = "complex"    # Multi-file changes, architecture
    CRITICAL = "critical"  # Major refactors, critical decisions


@dataclass
class ModelResponse:
    """Response from a model call."""
    content: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    tool_calls: List[Dict] = None
    
    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []


class OpusRouter:
    """
    Intelligent model router.
    
    Routes requests to the optimal model based on:
    - Task complexity
    - Context size needed
    - Cost optimization
    - User preference
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=120.0)
        self.total_cost = 0.0
        self.call_count = {"opus": 0, "sonnet": 0, "quick": 0, "flash": 0}
    
    async def close(self):
        await self.http.aclose()
    
    def classify_complexity(self, message: str, context_size: int = 0) -> TaskComplexity:
        """Classify task complexity from message."""
        message_lower = message.lower()
        
        # Critical indicators
        critical_patterns = [
            r"refactor\s+(?:entire|whole|all)",
            r"architect",
            r"redesign",
            r"migrate\s+(?:to|from)",
            r"critical",
            r"production",
            r"breaking\s+change",
        ]
        for pattern in critical_patterns:
            if re.search(pattern, message_lower):
                return TaskComplexity.CRITICAL
        
        # Complex indicators
        complex_patterns = [
            r"multiple\s+files",
            r"across\s+(?:the\s+)?(?:codebase|repo)",
            r"implement\s+(?:a\s+)?(?:new\s+)?(?:feature|system|service)",
            r"create\s+(?:a\s+)?(?:new\s+)?(?:module|component|service)",
            r"think\s+(?:carefully|deeply|through)",
            r"step\s+by\s+step",
            r"plan\s+(?:out|this)",
            r"build\s+(?:out|this|a)",
        ]
        for pattern in complex_patterns:
            if re.search(pattern, message_lower):
                return TaskComplexity.COMPLEX
        
        # Also complex if large context
        if context_size > 50000:
            return TaskComplexity.COMPLEX
        
        # Moderate indicators - includes tool-requiring queries
        moderate_patterns = [
            r"edit\s+(?:the\s+)?(?:file|code)",
            r"add\s+(?:a\s+)?(?:function|method|endpoint)",
            r"fix\s+(?:the\s+)?(?:bug|error|issue)",
            r"explain\s+(?:how|what|why)",
            r"update\s+(?:the\s+)?(?:code|file)",
            # Tool-requiring patterns
            r"read\s+(?:your|the|my|this)\s+(?:code|file)",
            r"look\s+at\s+(?:your|the|my)",
            r"check\s+(?:your|the|my)",
            r"analyze\s+(?:your|the|my)",
            r"show\s+(?:me\s+)?(?:your|the)",
            r"what\s+(?:is|are)\s+(?:your|the)",
            r"your\s+(?:code|file|capabilities)",
            r"run\s+(?:a\s+)?command",
            r"execute",
            r"search\s+(?:for|the)",
            r"find\s+(?:the|where)",
        ]
        for pattern in moderate_patterns:
            if re.search(pattern, message_lower):
                return TaskComplexity.MODERATE
        
        # Default to simple
        return TaskComplexity.SIMPLE
    
    def select_model(self, complexity: TaskComplexity, prefer_fast: bool = False) -> str:
        """Select the best model for the task."""
        if prefer_fast:
            return "quick"
        
        if complexity == TaskComplexity.CRITICAL:
            return "opus"
        elif complexity == TaskComplexity.COMPLEX:
            return "opus"  # Use Opus for complex too
        elif complexity == TaskComplexity.MODERATE:
            return "sonnet"
        else:
            return "quick"
    
    async def call(
        self,
        messages: List[Dict],
        system: str = None,
        model_override: str = None,
        tools: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = None
    ) -> ModelResponse:
        """
        Call the appropriate model.
        
        Args:
            messages: Conversation messages
            system: System prompt
            model_override: Force specific model
            tools: Available tools for function calling
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
        
        Returns:
            ModelResponse with content and metadata
        """
        # Determine model
        if model_override:
            model_key = model_override
        else:
            # Estimate context size
            context_size = sum(len(m.get("content", "")) for m in messages)
            if system:
                context_size += len(system)
            
            # Get last user message for complexity analysis
            last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
            complexity = self.classify_complexity(last_user, context_size)
            model_key = self.select_model(complexity)
        
        model_config = MODELS[model_key]
        provider = model_config["provider"]
        
        logger.info(f"Using {model_key} ({model_config['model']}) for request")
        
        # Route to provider
        if provider == "anthropic":
            return await self._call_anthropic(model_key, model_config, messages, system, tools, temperature, max_tokens)
        elif provider == "openai":
            return await self._call_openai(model_key, model_config, messages, system, tools, temperature, max_tokens)
        elif provider == "gemini":
            return await self._call_gemini(model_key, model_config, messages, system, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def _call_anthropic(
        self,
        model_key: str,
        config: Dict,
        messages: List[Dict],
        system: str,
        tools: List[Dict],
        temperature: float,
        max_tokens: int
    ) -> ModelResponse:
        """Call Anthropic API."""
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        payload = {
            "model": config["model"],
            "max_tokens": max_tokens or config["max_tokens"],
            "temperature": temperature,
            "messages": messages
        }
        
        if system:
            payload["system"] = system
        
        if tools:
            payload["tools"] = self._convert_tools_anthropic(tools)
        
        response = await self.http.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json=payload
        )
        
        if response.status_code != 200:
            logger.error(f"Anthropic error: {response.status_code} - {response.text[:500]}")
            raise Exception(f"Anthropic API error: {response.status_code}")
        
        data = response.json()
        
        # Extract content and tool calls
        content = ""
        tool_calls = []
        
        for block in data.get("content", []):
            if block["type"] == "text":
                content += block["text"]
            elif block["type"] == "tool_use":
                tool_calls.append({
                    "id": block["id"],
                    "name": block["name"],
                    "arguments": block["input"]
                })
        
        # Calculate cost
        input_tokens = data.get("usage", {}).get("input_tokens", 0)
        output_tokens = data.get("usage", {}).get("output_tokens", 0)
        cost = (input_tokens * config["cost_per_1k_input"] + 
                output_tokens * config["cost_per_1k_output"]) / 1000
        
        self.total_cost += cost
        self.call_count[model_key] += 1
        
        return ModelResponse(
            content=content,
            model=config["model"],
            provider="anthropic",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            tool_calls=tool_calls
        )
    
    async def _call_openai(
        self,
        model_key: str,
        config: Dict,
        messages: List[Dict],
        system: str,
        tools: List[Dict],
        temperature: float,
        max_tokens: int
    ) -> ModelResponse:
        """Call OpenAI API."""
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set")
        
        # Prepend system message
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)
        
        payload = {
            "model": config["model"],
            "max_tokens": max_tokens or config["max_tokens"],
            "temperature": temperature,
            "messages": all_messages
        }
        
        if tools:
            payload["tools"] = self._convert_tools_openai(tools)
        
        response = await self.http.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        if response.status_code != 200:
            logger.error(f"OpenAI error: {response.status_code} - {response.text[:500]}")
            raise Exception(f"OpenAI API error: {response.status_code}")
        
        data = response.json()
        choice = data["choices"][0]
        
        content = choice["message"].get("content", "")
        tool_calls = []
        
        if choice["message"].get("tool_calls"):
            for tc in choice["message"]["tool_calls"]:
                tool_calls.append({
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "arguments": json.loads(tc["function"]["arguments"])
                })
        
        input_tokens = data.get("usage", {}).get("prompt_tokens", 0)
        output_tokens = data.get("usage", {}).get("completion_tokens", 0)
        cost = (input_tokens * config["cost_per_1k_input"] + 
                output_tokens * config["cost_per_1k_output"]) / 1000
        
        self.total_cost += cost
        self.call_count[model_key] += 1
        
        return ModelResponse(
            content=content,
            model=config["model"],
            provider="openai",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            tool_calls=tool_calls
        )
    
    async def _call_gemini(
        self,
        model_key: str,
        config: Dict,
        messages: List[Dict],
        system: str,
        temperature: float,
        max_tokens: int
    ) -> ModelResponse:
        """Call Gemini API."""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        
        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens or config["max_tokens"]
            }
        }
        
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        
        response = await self.http.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{config['model']}:generateContent?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json=payload
        )
        
        if response.status_code != 200:
            logger.error(f"Gemini error: {response.status_code} - {response.text[:500]}")
            raise Exception(f"Gemini API error: {response.status_code}")
        
        data = response.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        
        # Gemini doesn't return token counts in the same way
        input_tokens = len(str(messages)) // 4  # Rough estimate
        output_tokens = len(content) // 4
        cost = (input_tokens * config["cost_per_1k_input"] + 
                output_tokens * config["cost_per_1k_output"]) / 1000
        
        self.total_cost += cost
        self.call_count[model_key] += 1
        
        return ModelResponse(
            content=content,
            model=config["model"],
            provider="gemini",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )
    
    def _convert_tools_anthropic(self, tools: List[Dict]) -> List[Dict]:
        """Convert tools to Anthropic format."""
        return [{
            "name": t["name"],
            "description": t["description"],
            "input_schema": {
                "type": "object",
                "properties": t.get("parameters", {}),
                "required": t.get("required", [])
            }
        } for t in tools]
    
    def _convert_tools_openai(self, tools: List[Dict]) -> List[Dict]:
        """Convert tools to OpenAI format."""
        return [{
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": {
                    "type": "object",
                    "properties": t.get("parameters", {}),
                    "required": t.get("required", [])
                }
            }
        } for t in tools]
    
    def get_stats(self) -> Dict:
        """Get usage statistics."""
        return {
            "total_cost": round(self.total_cost, 4),
            "call_count": self.call_count,
            "models_available": {
                "opus": bool(ANTHROPIC_API_KEY),
                "sonnet": bool(ANTHROPIC_API_KEY),
                "quick": bool(OPENAI_API_KEY),
                "flash": bool(GEMINI_API_KEY)
            }
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

_router: Optional[OpusRouter] = None


def get_router() -> OpusRouter:
    """Get global router instance."""
    global _router
    if _router is None:
        _router = OpusRouter()
    return _router


async def ask_opus(
    message: str,
    system: str = None,
    history: List[Dict] = None,
    tools: List[Dict] = None
) -> ModelResponse:
    """Quick helper to ask Opus a question."""
    router = get_router()
    
    messages = history or []
    messages.append({"role": "user", "content": message})
    
    return await router.call(messages, system=system, tools=tools)

