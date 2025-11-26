"""
API Gateway Client
==================
Simple client for services to use the centralized API Gateway.

Usage:
    from core.api_gateway_client import AIClient
    
    client = AIClient(user_id="mission-worker", service_id="ai-missions")
    
    # Chat with any provider through the gateway
    response = await client.chat(
        provider="anthropic",
        model="claude-3-5-sonnet",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    
    print(response.content)
    print(f"Cost: ${response.cost_usd}")
"""

import os
import httpx
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

# Gateway URL (configurable via env)
GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8400")


class Provider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


@dataclass
class ChatResponse:
    content: str
    model: str
    provider: str
    usage: Dict[str, int]
    cost_usd: float
    request_id: str
    timestamp: str
    
    @property
    def total_tokens(self) -> int:
        return self.usage.get("input_tokens", 0) + self.usage.get("output_tokens", 0)


class AIClient:
    """
    Client for the centralized API Gateway.
    Routes all AI requests through the gateway for metering and billing.
    """
    
    def __init__(
        self,
        user_id: str = "anonymous",
        service_id: str = "default",
        project_id: str = None,
        gateway_url: str = None,
    ):
        self.user_id = user_id
        self.service_id = service_id
        self.project_id = project_id
        self.gateway_url = gateway_url or GATEWAY_URL
        self._client = httpx.AsyncClient(timeout=120.0)
    
    async def chat(
        self,
        provider: str | Provider,
        model: str,
        messages: List[Dict[str, str]],
        system: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> ChatResponse:
        """
        Send a chat request through the API Gateway.
        
        Args:
            provider: "openai", "anthropic", or "gemini"
            model: Model name (e.g., "gpt-4o", "claude-3-5-sonnet")
            messages: List of message dicts with "role" and "content"
            system: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
        
        Returns:
            ChatResponse with content, usage, and cost
        """
        if isinstance(provider, str):
            provider = Provider(provider)
        
        payload = {
            "provider": provider.value,
            "model": model,
            "messages": messages,
            "system": system,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "user_id": self.user_id,
            "service_id": self.service_id,
            "project_id": self.project_id,
        }
        
        response = await self._client.post(
            f"{self.gateway_url}/v1/chat",
            json=payload,
        )
        
        if response.status_code != 200:
            raise Exception(f"Gateway error: {response.status_code} - {response.text}")
        
        data = response.json()
        return ChatResponse(**data)
    
    async def get_usage(self, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for this user"""
        response = await self._client.get(
            f"{self.gateway_url}/v1/usage/{self.user_id}",
            params={"days": days},
        )
        return response.json()
    
    async def get_budget(self) -> Dict[str, Any]:
        """Get budget info for this user"""
        response = await self._client.get(
            f"{self.gateway_url}/v1/budget/{self.user_id}",
        )
        return response.json()
    
    # Convenience methods for each provider
    async def claude(
        self,
        prompt: str,
        model: str = "claude-3-5-sonnet-20241022",
        system: str = None,
        **kwargs,
    ) -> ChatResponse:
        """Quick Claude chat"""
        return await self.chat(
            provider=Provider.ANTHROPIC,
            model=model,
            messages=[{"role": "user", "content": prompt}],
            system=system,
            **kwargs,
        )
    
    async def gpt(
        self,
        prompt: str,
        model: str = "gpt-4o",
        system: str = None,
        **kwargs,
    ) -> ChatResponse:
        """Quick GPT chat"""
        return await self.chat(
            provider=Provider.OPENAI,
            model=model,
            messages=[{"role": "user", "content": prompt}],
            system=system,
            **kwargs,
        )
    
    async def gemini(
        self,
        prompt: str,
        model: str = "models/gemini-2.5-flash",
        system: str = None,
        **kwargs,
    ) -> ChatResponse:
        """Quick Gemini chat"""
        return await self.chat(
            provider=Provider.GEMINI,
            model=model,
            messages=[{"role": "user", "content": prompt}],
            system=system,
            **kwargs,
        )
    
    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()


# Synchronous wrapper for simple scripts
class AIClientSync:
    """Synchronous wrapper for AIClient"""
    
    def __init__(self, **kwargs):
        import asyncio
        self._async_client = AIClient(**kwargs)
        self._loop = asyncio.new_event_loop()
    
    def chat(self, **kwargs) -> ChatResponse:
        return self._loop.run_until_complete(self._async_client.chat(**kwargs))
    
    def claude(self, prompt: str, **kwargs) -> ChatResponse:
        return self._loop.run_until_complete(self._async_client.claude(prompt, **kwargs))
    
    def gpt(self, prompt: str, **kwargs) -> ChatResponse:
        return self._loop.run_until_complete(self._async_client.gpt(prompt, **kwargs))
    
    def gemini(self, prompt: str, **kwargs) -> ChatResponse:
        return self._loop.run_until_complete(self._async_client.gemini(prompt, **kwargs))
    
    def get_usage(self, days: int = 30) -> Dict[str, Any]:
        return self._loop.run_until_complete(self._async_client.get_usage(days))


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        async with AIClient(user_id="test", service_id="example") as client:
            # Test with Claude
            response = await client.claude("Say hello in 10 words or less")
            print(f"Claude: {response.content}")
            print(f"Cost: ${response.cost_usd:.4f}")
            print(f"Tokens: {response.total_tokens}")
    
    asyncio.run(main())

