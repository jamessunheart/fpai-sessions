"""
Aria AI Brain Client - Cost Optimized
======================================

Priority: LOCAL LLAMA (FREE) > Together (cheap) > Paid APIs

Uses AI Brain on secondary server which has:
- Local Ollama with llama3.1:8b, llama3.2:3b, mistral:7b (FREE!)
- Together API: Llama 3.3 70B ($0.90/1M tokens)
- xAI: Grok 4 ($2-10/1M tokens)
- OpenAI: GPT-5.1 ($5-15/1M tokens)
- Anthropic: Claude Opus ($15-75/1M tokens)
"""

import os
import httpx
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("aria.brain")

# Import cost tracker
try:
    from cost_tracker import get_cost_tracker, record_cost
    COST_TRACKING_ENABLED = True
except ImportError:
    COST_TRACKING_ENABLED = False
    logger.warning("Cost tracking not available")

# AI Brain service endpoint (on secondary server with local Ollama)
AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://162.0.208.88:8101")


class AIProvider(str, Enum):
    """Available AI providers."""
    AUTO = "auto"           # Smart routing
    OLLAMA = "ollama"       # LOCAL - FREE! (llama3.1:8b)
    TOGETHER = "together"   # Llama 3.3 70B - $0.90/1M
    XAI = "xai"             # Grok 4 - $2-10/1M
    OPENAI = "openai"       # GPT-5.1 - $5-15/1M
    ANTHROPIC = "anthropic" # Claude - $15-75/1M
    VERTEX = "vertex"       # Gemini - $varies


# COST-OPTIMIZED ROUTING
# Priority: FREE local Ollama > Cheap Together > Paid only when needed
PROVIDER_ROUTING = {
    "simple": AIProvider.OLLAMA,       # FREE - Simple questions
    "fast": AIProvider.OLLAMA,         # FREE - Quick responses
    "conversation": AIProvider.OLLAMA, # FREE - Chat
    "creative": AIProvider.TOGETHER,   # $0.90/1M - Larger model for creativity
    "reasoning": AIProvider.TOGETHER,  # $0.90/1M - Good reasoning, cheap
    "trading": AIProvider.XAI,         # $2-10/1M - Precision matters
    "complex": AIProvider.XAI,         # $2-10/1M - Complex multi-step
    "premium": AIProvider.OPENAI,      # $5-15/1M - Only if explicitly needed
    "default": AIProvider.OLLAMA       # FREE - Default to local
}

# Cost per 1M tokens (approximate)
MODEL_COSTS = {
    AIProvider.OLLAMA: {"input": 0.0, "output": 0.0},        # FREE!
    AIProvider.TOGETHER: {"input": 0.90, "output": 0.90},    # Cheapest external
    AIProvider.XAI: {"input": 2.00, "output": 10.00},        # Mid-tier
    AIProvider.OPENAI: {"input": 5.00, "output": 15.00},     # Expensive
    AIProvider.ANTHROPIC: {"input": 15.00, "output": 75.00}, # Most expensive
}


@dataclass
class BrainResponse:
    """Response from AI Brain."""
    text: str
    provider: str
    model: str
    latency_ms: float
    tokens_used: int
    estimated_cost: float = 0.0
    success: bool = True
    error: Optional[str] = None


class AriaBrainClient:
    """Client for AI Brain with cost-optimized routing (local first!)"""
    
    def __init__(self, base_url: str = AI_BRAIN_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
        self._available_providers: Optional[Dict] = None
        self._total_cost = 0.0
        self._total_requests = 0
    
    async def close(self):
        await self.client.aclose()
    
    def _detect_task_type(self, prompt: str) -> str:
        """Detect task type for cost-optimized routing."""
        prompt_lower = prompt.lower()
        prompt_len = len(prompt)
        
        # Super short = definitely local (FREE)
        if prompt_len < 50:
            return "simple"
        
        # Trading keywords -> xAI Grok (precision matters)
        trading_keywords = ["trade", "trading", "signal", "position", "market", 
                          "btc", "eth", "sol", "crypto", "long", "short",
                          "entry", "exit", "stop loss", "take profit"]
        if any(w in prompt_lower for w in trading_keywords):
            return "trading"
        
        # Complex multi-step -> xAI Grok (worth the cost)
        complex_indicators = ["step by step", "detailed analysis", "comprehensive",
                             "in-depth", "multi-part", "complex analysis"]
        if any(w in prompt_lower for w in complex_indicators) and prompt_len > 300:
            return "complex"
        
        # Deep reasoning -> Together (good and cheap)
        reasoning_indicators = ["why does", "explain how", "what causes", 
                               "analyze the", "evaluate", "compare"]
        if any(w in prompt_lower for w in reasoning_indicators) and prompt_len > 150:
            return "reasoning"
        
        # Creative writing -> Together (larger model)
        if any(w in prompt_lower for w in ["write", "create", "story", "poem", "imagine"]):
            return "creative"
        
        # Most queries can use local Ollama (FREE!)
        if prompt_len < 200:
            return "simple"
        
        # Default to conversation (local Ollama)
        return "conversation"
    
    def _get_best_provider(self, task_type: str = "default") -> AIProvider:
        """Get the best provider for a task type."""
        return PROVIDER_ROUTING.get(task_type, PROVIDER_ROUTING["default"])
    
    def _estimate_cost(self, tokens: int, provider: AIProvider) -> float:
        """Calculate cost for tokens."""
        costs = MODEL_COSTS.get(provider, {"input": 0.0, "output": 0.0})
        avg_cost = (costs["input"] + costs["output"]) / 2
        return (tokens / 1_000_000) * avg_cost
    
    async def health_check(self) -> Dict:
        """Check AI Brain health and available providers."""
        try:
            resp = await self.client.get(f"{self.base_url}/")
            if resp.status_code == 200:
                data = resp.json()
                self._available_providers = data.get("providers", {})
                return data
        except Exception as e:
            logger.error(f"AI Brain health check failed: {e}")
        return {"status": "error", "providers": {}}
    
    async def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        provider: AIProvider = AIProvider.AUTO,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> BrainResponse:
        """
        Generate a response with COST-OPTIMIZED routing.
        
        By default uses LOCAL OLLAMA (FREE!) for most queries.
        Only routes to paid APIs for complex/trading tasks.
        """
        try:
            # Smart routing when AUTO
            if provider == AIProvider.AUTO:
                task_type = self._detect_task_type(prompt)
                
                # Budget override: force free tier if approaching limit
                if self.should_use_free_tier():
                    provider = AIProvider.OLLAMA
                    logger.info(f"Budget override: forcing FREE tier (Ollama)")
                else:
                    provider = self._get_best_provider(task_type)
                
                is_free = provider == AIProvider.OLLAMA
                free_tag = "(FREE!)" if is_free else ""
                logger.info(f"Smart routing: {task_type} -> {provider.value} {free_tag}")
            
            payload = {
                "prompt": prompt,
                "provider": provider.value,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            if system_message:
                payload["system_message"] = system_message
            
            if model:
                payload["model"] = model
            
            resp = await self.client.post(
                f"{self.base_url}/generate",
                json=payload
            )
            
            if resp.status_code == 200:
                data = resp.json()
                
                # Calculate cost
                tokens = data.get("tokens_used", 0)
                actual_provider_str = data.get("provider", "ollama")
                try:
                    actual_provider = AIProvider(actual_provider_str)
                except ValueError:
                    actual_provider = AIProvider.OLLAMA
                
                est_cost = self._estimate_cost(tokens, actual_provider)
                self._total_cost += est_cost
                self._total_requests += 1
                
                # Track in persistent cost tracker
                if COST_TRACKING_ENABLED:
                    task_type = self._detect_task_type(prompt) if provider == AIProvider.AUTO else "manual"
                    record_cost(
                        provider=actual_provider_str,
                        model=data.get("model", "unknown"),
                        input_tokens=data.get("input_tokens", tokens // 2),
                        output_tokens=data.get("output_tokens", tokens // 2),
                        query_type=task_type,
                        latency_ms=data.get("latency_ms", 0)
                    )
                
                cost_str = "FREE" if est_cost == 0 else f"${est_cost:.6f}"
                logger.info(f"Response: {tokens} tokens via {actual_provider_str} | Cost: {cost_str} | Session total: ${self._total_cost:.4f}")
                
                return BrainResponse(
                    text=data.get("text", ""),
                    provider=data.get("provider", "unknown"),
                    model=data.get("model", "unknown"),
                    latency_ms=data.get("latency_ms", 0),
                    tokens_used=tokens,
                    estimated_cost=est_cost
                )
            else:
                return BrainResponse(
                    text="",
                    provider="error",
                    model="",
                    latency_ms=0,
                    tokens_used=0,
                    success=False,
                    error=resp.text
                )
                
        except Exception as e:
            logger.error(f"AI Brain generate error: {e}")
            return BrainResponse(
                text="",
                provider="error",
                model="",
                latency_ms=0,
                tokens_used=0,
                success=False,
                error=str(e)
            )
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_message: Optional[str] = None,
        provider: AIProvider = AIProvider.AUTO,
        temperature: float = 0.7
    ) -> BrainResponse:
        """Chat with conversation history."""
        prompt_parts = []
        
        if system_message:
            prompt_parts.append(f"System: {system_message}\n")
        
        for msg in messages[-10:]:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            prompt_parts.append(f"{role}: {content}")
        
        prompt = "\n".join(prompt_parts)
        prompt += "\nAssistant:"
        
        return await self.generate(
            prompt=prompt,
            provider=provider,
            temperature=temperature
        )
    
    async def think(
        self,
        question: str,
        context: Optional[str] = None,
        provider: AIProvider = AIProvider.TOGETHER  # Together for reasoning (cheap)
    ) -> BrainResponse:
        """Deep thinking task - uses Together (Llama 3.3 70B) for reasoning."""
        system = """You are a deep thinking AI assistant. 
Analyze carefully and provide a thoughtful, well-reasoned response.
Be concise but thorough."""
        
        prompt = question
        if context:
            prompt = f"Context: {context}\n\nQuestion: {question}"
        
        return await self.generate(
            prompt=prompt,
            system_message=system,
            provider=provider,
            temperature=0.3
        )
    
    async def trade_analysis(
        self,
        market_data: str,
        question: str
    ) -> BrainResponse:
        """Trading analysis - uses xAI Grok (precision matters for money)."""
        system = """You are an expert trading analyst.
Analyze the data and give actionable insights.
Include: signal strength, key levels, risk/reward, recommended action.
Be concise and direct."""
        
        prompt = f"Market Data:\n{market_data}\n\nQuestion: {question}"
        
        return await self.generate(
            prompt=prompt,
            system_message=system,
            provider=AIProvider.XAI,
            temperature=0.2
        )
    
    def get_stats(self) -> Dict:
        """Get usage statistics."""
        return {
            "total_requests": self._total_requests,
            "total_cost_usd": self._total_cost,
            "avg_cost_per_request": self._total_cost / max(self._total_requests, 1)
        }
    
    def get_cost_report(self) -> str:
        """Get a formatted cost report."""
        if COST_TRACKING_ENABLED:
            tracker = get_cost_tracker()
            return tracker.format_cost_report()
        else:
            return f"Session cost: ${self._total_cost:.4f} ({self._total_requests} requests)"
    
    def should_use_free_tier(self) -> bool:
        """Check if budget constraints require free tier."""
        if COST_TRACKING_ENABLED:
            tracker = get_cost_tracker()
            return tracker.should_use_free_tier()
        return False


# Singleton
_brain_client: Optional[AriaBrainClient] = None


async def get_brain_client() -> AriaBrainClient:
    """Get or create the AI Brain client."""
    global _brain_client
    if _brain_client is None:
        _brain_client = AriaBrainClient()
        health = await _brain_client.health_check()
        if health.get("providers"):
            logger.info("AI Brain connected")
            providers = health.get("providers", {})
            local = "LOCAL (FREE)" if providers.get("ollama") else "not available"
            logger.info(f"   Local Ollama: {local}")
        else:
            logger.warning("AI Brain not available")
    return _brain_client


async def ask_brain(
    prompt: str,
    system: Optional[str] = None,
    provider: str = "auto"
) -> str:
    """Simple interface to ask the AI Brain."""
    client = await get_brain_client()
    
    try:
        provider_enum = AIProvider(provider)
    except ValueError:
        provider_enum = AIProvider.AUTO
    
    response = await client.generate(
        prompt=prompt,
        system_message=system,
        provider=provider_enum
    )
    
    if response.success:
        return response.text
    else:
        return f"Brain error: {response.error}"


if __name__ == "__main__":
    import asyncio
    
    async def test():
        client = await get_brain_client()
        
        print("\n1. Simple question (should use LOCAL Ollama = FREE)")
        resp = await client.generate("What is 2+2?")
        print(f"   Response: {resp.text[:50]}")
        print(f"   Provider: {resp.provider} | Cost: ${resp.estimated_cost:.6f}")
        
        print("\n2. Trading question (should use xAI Grok)")
        resp = await client.generate("Should I go long on SOL at 220?")
        print(f"   Response: {resp.text[:100]}...")
        print(f"   Provider: {resp.provider} | Cost: ${resp.estimated_cost:.6f}")
        
        print("\n3. Deep reasoning (should use Together)")
        resp = await client.think("Why does inflation affect crypto markets?")
        print(f"   Response: {resp.text[:100]}...")
        print(f"   Provider: {resp.provider} | Cost: ${resp.estimated_cost:.6f}")
        
        stats = client.get_stats()
        print(f"\n Session Stats: {stats['total_requests']} requests, ${stats['total_cost_usd']:.4f} total")
        
        await client.close()
    
    asyncio.run(test())

