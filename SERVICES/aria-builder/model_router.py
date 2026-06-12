#!/usr/bin/env python3
"""
ARIA MULTI-MODEL ROUTER
=======================

Routes requests to the optimal AI model based on task type.

Strategy:
- OpenAI gpt-4o-mini: Fast responses (1-2 sec), conversation
- Claude Sonnet: Code generation, complex reasoning
- Gemini Flash: Verification, fallback, cheap second opinions

This provides redundancy and validation - if one fails, fallback to another.
"""

import os
import json
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import httpx

logger = logging.getLogger("aria.model_router")

# ============================================================================
# CONFIGURATION
# ============================================================================

# API Keys from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Model configurations
MODELS = {
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o-mini",
        "max_tokens": 4096,
        "temperature": 0.7
    },
    "claude": {
        "url": "https://api.anthropic.com/v1/messages",
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "temperature": 0.7
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models",
        "model": "gemini-2.0-flash",
        "max_tokens": 4096,
        "temperature": 0.7
    }
}

# Task routing configuration
TASK_ROUTING = {
    "chat": ["openai", "gemini"],           # Fast response needed
    "code_gen": ["claude", "gemini"],        # Best code quality
    "code_review": ["gemini", "claude"],     # Cheap verification
    "spec_create": ["claude"],               # Complex reasoning
    "intent_parse": ["openai", "gemini"],    # Fast classification
    "verify": ["gemini", "openai"],          # Cheap second opinion
    "consensus": ["openai", "claude", "gemini"]  # All vote
}


class TaskType(str, Enum):
    CHAT = "chat"
    CODE_GEN = "code_gen"
    CODE_REVIEW = "code_review"
    SPEC_CREATE = "spec_create"
    INTENT_PARSE = "intent_parse"
    VERIFY = "verify"
    CONSENSUS = "consensus"


@dataclass
class ModelResponse:
    """Response from an AI model."""
    provider: str
    model: str
    content: str
    tokens_used: int = 0
    latency_ms: int = 0
    success: bool = True
    error: Optional[str] = None


class ModelRouter:
    """
    Routes requests to optimal AI model based on task type.
    
    Provides:
    - Smart routing based on task
    - Automatic fallback on failure
    - Consensus voting for critical decisions
    - Cost tracking
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=60.0)
        self.call_count = {"openai": 0, "claude": 0, "gemini": 0}
        self.error_count = {"openai": 0, "claude": 0, "gemini": 0}
        
        # Check which providers are available
        self.available = {
            "openai": bool(OPENAI_API_KEY),
            "claude": bool(ANTHROPIC_API_KEY),
            "gemini": bool(GEMINI_API_KEY)
        }
        
        available_list = [k for k, v in self.available.items() if v]
        logger.info(f"ModelRouter initialized. Available: {available_list}")
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    async def route(
        self,
        task: TaskType,
        prompt: str,
        system: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> ModelResponse:
        """
        Route request to optimal model for the task.
        
        Args:
            task: Type of task (determines routing)
            prompt: User prompt
            system: Optional system prompt
            context: Optional additional context
        
        Returns:
            ModelResponse with content or error
        """
        providers = TASK_ROUTING.get(task.value, ["openai"])
        
        # Filter to available providers
        providers = [p for p in providers if self.available.get(p)]
        
        if not providers:
            return ModelResponse(
                provider="none",
                model="none",
                content="",
                success=False,
                error="No AI providers available. Check API keys."
            )
        
        # Try each provider in order
        for provider in providers:
            try:
                response = await self._call_provider(provider, prompt, system)
                if response.success:
                    return response
                logger.warning(f"{provider} failed: {response.error}")
            except Exception as e:
                logger.error(f"{provider} exception: {e}")
                self.error_count[provider] += 1
        
        # All failed
        return ModelResponse(
            provider="none",
            model="none",
            content="",
            success=False,
            error=f"All providers failed: {providers}"
        )
    
    async def consensus(
        self,
        prompt: str,
        system: Optional[str] = None
    ) -> Dict[str, ModelResponse]:
        """
        Get responses from all available models for consensus.
        
        Returns dict of provider -> response.
        """
        tasks = []
        providers = []
        
        for provider in ["openai", "claude", "gemini"]:
            if self.available.get(provider):
                tasks.append(self._call_provider(provider, prompt, system))
                providers.append(provider)
        
        if not tasks:
            return {}
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        result = {}
        for provider, response in zip(providers, responses):
            if isinstance(response, Exception):
                result[provider] = ModelResponse(
                    provider=provider,
                    model="error",
                    content="",
                    success=False,
                    error=str(response)
                )
            else:
                result[provider] = response
        
        return result
    
    async def _call_provider(
        self,
        provider: str,
        prompt: str,
        system: Optional[str] = None
    ) -> ModelResponse:
        """Call a specific AI provider."""
        import time
        start = time.time()
        
        try:
            if provider == "openai":
                response = await self._call_openai(prompt, system)
            elif provider == "claude":
                response = await self._call_claude(prompt, system)
            elif provider == "gemini":
                response = await self._call_gemini(prompt, system)
            else:
                return ModelResponse(
                    provider=provider,
                    model="unknown",
                    content="",
                    success=False,
                    error=f"Unknown provider: {provider}"
                )
            
            response.latency_ms = int((time.time() - start) * 1000)
            self.call_count[provider] += 1
            return response
            
        except Exception as e:
            self.error_count[provider] += 1
            return ModelResponse(
                provider=provider,
                model=MODELS[provider]["model"],
                content="",
                success=False,
                error=str(e)
            )
    
    async def _call_openai(self, prompt: str, system: Optional[str] = None) -> ModelResponse:
        """Call OpenAI API."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.http.post(
            MODELS["openai"]["url"],
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODELS["openai"]["model"],
                "messages": messages,
                "max_tokens": MODELS["openai"]["max_tokens"],
                "temperature": MODELS["openai"]["temperature"]
            }
        )
        
        if response.status_code != 200:
            return ModelResponse(
                provider="openai",
                model=MODELS["openai"]["model"],
                content="",
                success=False,
                error=f"HTTP {response.status_code}: {response.text[:200]}"
            )
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        
        return ModelResponse(
            provider="openai",
            model=MODELS["openai"]["model"],
            content=content,
            tokens_used=tokens,
            success=True
        )
    
    async def _call_claude(self, prompt: str, system: Optional[str] = None) -> ModelResponse:
        """Call Anthropic Claude API."""
        payload = {
            "model": MODELS["claude"]["model"],
            "max_tokens": MODELS["claude"]["max_tokens"],
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if system:
            payload["system"] = system
        
        response = await self.http.post(
            MODELS["claude"]["url"],
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        if response.status_code != 200:
            return ModelResponse(
                provider="claude",
                model=MODELS["claude"]["model"],
                content="",
                success=False,
                error=f"HTTP {response.status_code}: {response.text[:200]}"
            )
        
        data = response.json()
        content = data["content"][0]["text"]
        tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
        
        return ModelResponse(
            provider="claude",
            model=MODELS["claude"]["model"],
            content=content,
            tokens_used=tokens,
            success=True
        )
    
    async def _call_gemini(self, prompt: str, system: Optional[str] = None) -> ModelResponse:
        """Call Google Gemini API."""
        model = MODELS["gemini"]["model"]
        url = f"{MODELS['gemini']['url']}/{model}:generateContent?key={GEMINI_API_KEY}"
        
        # Combine system and prompt for Gemini
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        
        response = await self.http.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": MODELS["gemini"]["max_tokens"],
                    "temperature": MODELS["gemini"]["temperature"]
                }
            }
        )
        
        if response.status_code != 200:
            return ModelResponse(
                provider="gemini",
                model=model,
                content="",
                success=False,
                error=f"HTTP {response.status_code}: {response.text[:200]}"
            )
        
        data = response.json()
        
        # Extract content from Gemini response
        try:
            content = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            return ModelResponse(
                provider="gemini",
                model=model,
                content="",
                success=False,
                error=f"Failed to parse response: {e}"
            )
        
        return ModelResponse(
            provider="gemini",
            model=model,
            content=content,
            tokens_used=0,  # Gemini doesn't report tokens the same way
            success=True
        )
    
    def get_stats(self) -> Dict:
        """Get usage statistics."""
        return {
            "available": self.available,
            "calls": self.call_count,
            "errors": self.error_count
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_router: Optional[ModelRouter] = None


def get_router() -> ModelRouter:
    """Get or create the global router instance."""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


async def quick_chat(prompt: str, system: Optional[str] = None) -> str:
    """Fast chat response using OpenAI/Gemini."""
    router = get_router()
    response = await router.route(TaskType.CHAT, prompt, system)
    return response.content if response.success else f"Error: {response.error}"


async def generate_code(prompt: str, context: Optional[str] = None) -> str:
    """Generate code using Claude."""
    router = get_router()
    system = "You are an expert Python developer. Generate clean, well-documented code."
    if context:
        prompt = f"Context:\n{context}\n\nRequest:\n{prompt}"
    response = await router.route(TaskType.CODE_GEN, prompt, system)
    return response.content if response.success else f"Error: {response.error}"


async def verify_code(code: str, criteria: str = "correctness and safety") -> str:
    """Verify code using Gemini (cheap second opinion)."""
    router = get_router()
    prompt = f"Review this code for {criteria}:\n\n```python\n{code}\n```\n\nProvide brief assessment."
    response = await router.route(TaskType.VERIFY, prompt)
    return response.content if response.success else f"Error: {response.error}"


async def parse_intent(text: str) -> str:
    """Parse user intent quickly."""
    router = get_router()
    system = """Classify the user's intent into one of:
- add_command: Adding a new command
- add_response: Adding a pattern response
- add_endpoint: Adding an API endpoint
- modify_code: Changing existing code
- read_code: Viewing/understanding code
- restart: Restarting a service
- other: Something else

Respond with JSON: {"intent": "...", "target": "...", "details": "..."}"""
    
    response = await router.route(TaskType.INTENT_PARSE, text, system)
    return response.content if response.success else '{"intent": "other", "error": true}'


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        router = get_router()
        print(f"Stats: {router.get_stats()}")
        
        # Test quick chat
        print("\n--- Testing Quick Chat ---")
        response = await quick_chat("What is 2+2?")
        print(f"Response: {response[:200]}")
        
        # Test code gen
        print("\n--- Testing Code Gen ---")
        response = await generate_code("Write a function to calculate fibonacci numbers")
        print(f"Response: {response[:500]}")
        
        print(f"\nFinal stats: {router.get_stats()}")
        await router.close()
    
    asyncio.run(test())


