"""
ARIA AI ROUTER
==============

Routes AI requests to the best available backend:
1. GPU Bridge (Vast.ai GPUs) - Fast, quality responses
2. Local Ollama - Free fallback
3. Paid APIs - Last resort

Target: Response time under 5 seconds for most queries.
"""

import os
import asyncio
import logging
import time
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
import httpx

logger = logging.getLogger("aria.router")

# Configuration
GPU_BRIDGE_URL = os.getenv("GPU_BRIDGE_URL", "http://162.0.208.88:8400")
LOCAL_OLLAMA_URL = os.getenv("LOCAL_OLLAMA_URL", "http://162.0.208.88:11434")
SMART_SCALER_URL = os.getenv("SMART_SCALER_URL", "http://162.0.208.88:8450")

# Model preferences
CONVERSATION_MODEL = "llama3.1:8b"      # Good for chat
CODING_MODEL = "qwen2.5-coder:7b"       # Good for code
FAST_MODEL = "llama3.2:3b"              # Quick responses

# Timeouts
FAST_TIMEOUT = 5.0      # For simple queries
STANDARD_TIMEOUT = 15.0  # For most queries  
COMPLEX_TIMEOUT = 60.0   # For complex generation


class BackendType(str, Enum):
    """Available AI backends."""
    GPU_BRIDGE = "gpu_bridge"
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class RouteResult:
    """Result from routing a request."""
    response: str
    backend: str
    model: str
    latency_ms: float
    tokens: int
    cost: float = 0.0
    success: bool = True
    error: Optional[str] = None


class AriaRouter:
    """
    Intelligent router for AI requests.
    
    Routing priority:
    1. GPU Bridge (Vast.ai) - when available and healthy
    2. Local Ollama - free fallback
    3. Paid APIs - only for critical/complex needs
    
    Features:
    - Health tracking per backend
    - Automatic failover
    - Response time monitoring
    - Cost tracking
    """
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=STANDARD_TIMEOUT)
        
        # Backend health status
        self.backends = {
            BackendType.GPU_BRIDGE: {"healthy": False, "last_check": 0, "avg_latency": 0},
            BackendType.OLLAMA: {"healthy": False, "last_check": 0, "avg_latency": 0},
        }
        
        # Stats
        self.stats = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "total_cost": 0.0,
            "total_latency_ms": 0,
            "by_backend": {b.value: 0 for b in BackendType}
        }
        
        logger.info("AriaRouter initialized")
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
    
    async def check_health(self):
        """Check health of all backends."""
        await asyncio.gather(
            self._check_gpu_bridge(),
            self._check_ollama(),
            return_exceptions=True
        )
    
    async def _check_gpu_bridge(self):
        """Check GPU Bridge health."""
        try:
            r = await self.http_client.get(f"{GPU_BRIDGE_URL}/health", timeout=5.0)
            if r.status_code == 200:
                self.backends[BackendType.GPU_BRIDGE]["healthy"] = True
                data = r.json()
                gpu_count = data.get("total_gpus", 0)
                logger.info(f"✅ GPU Bridge healthy: {gpu_count} GPUs")
            else:
                self.backends[BackendType.GPU_BRIDGE]["healthy"] = False
        except Exception as e:
            self.backends[BackendType.GPU_BRIDGE]["healthy"] = False
            logger.warning(f"⚠️ GPU Bridge unavailable: {e}")
        
        self.backends[BackendType.GPU_BRIDGE]["last_check"] = time.time()
    
    async def _check_ollama(self):
        """Check local Ollama health."""
        try:
            r = await self.http_client.get(f"{LOCAL_OLLAMA_URL}/api/tags", timeout=5.0)
            if r.status_code == 200:
                self.backends[BackendType.OLLAMA]["healthy"] = True
                models = r.json().get("models", [])
                logger.info(f"✅ Local Ollama healthy: {len(models)} models")
            else:
                self.backends[BackendType.OLLAMA]["healthy"] = False
        except Exception as e:
            self.backends[BackendType.OLLAMA]["healthy"] = False
            logger.warning(f"⚠️ Local Ollama unavailable: {e}")
        
        self.backends[BackendType.OLLAMA]["last_check"] = time.time()
    
    def _select_backend(self, task_type: str = "conversation") -> BackendType:
        """Select best backend for task."""
        # Prefer GPU Bridge for quality
        if self.backends[BackendType.GPU_BRIDGE]["healthy"]:
            return BackendType.GPU_BRIDGE
        
        # Fallback to Ollama
        if self.backends[BackendType.OLLAMA]["healthy"]:
            return BackendType.OLLAMA
        
        # No healthy backends - try GPU Bridge anyway
        return BackendType.GPU_BRIDGE
    
    def _select_model(self, task_type: str = "conversation") -> str:
        """Select best model for task type."""
        if task_type in ["code", "technical", "code_generation"]:
            return CODING_MODEL
        elif task_type in ["fast", "simple"]:
            return FAST_MODEL
        else:
            return CONVERSATION_MODEL
    
    def _detect_task_type(self, prompt: str) -> str:
        """Detect task type from prompt."""
        prompt_lower = prompt.lower()
        
        # Very short = fast
        if len(prompt) < 50:
            return "fast"
        
        # Code indicators
        if any(w in prompt_lower for w in ["code", "function", "class", "implement", "python", "javascript"]):
            return "code"
        
        # Technical indicators
        if any(w in prompt_lower for w in ["error", "debug", "log", "server", "deploy"]):
            return "technical"
        
        return "conversation"
    
    def _get_timeout(self, task_type: str) -> float:
        """Get appropriate timeout for task type."""
        if task_type == "fast":
            return FAST_TIMEOUT
        elif task_type in ["code", "technical"]:
            return COMPLEX_TIMEOUT
        return STANDARD_TIMEOUT
    
    async def route(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        task_type: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> RouteResult:
        """
        Route a request to the best available backend.
        
        Args:
            prompt: The user's message
            system_prompt: System prompt for context
            task_type: Override auto-detection
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            RouteResult with response and metadata
        """
        start_time = time.time()
        self.stats["total_requests"] += 1
        
        # Auto-detect task type if not provided
        if not task_type:
            task_type = self._detect_task_type(prompt)
        
        # Check backend health (if stale)
        now = time.time()
        for backend_type, status in self.backends.items():
            if now - status["last_check"] > 60:  # Check every 60 seconds
                await self.check_health()
                break
        
        # Select backend and model
        backend = self._select_backend(task_type)
        model = self._select_model(task_type)
        timeout = self._get_timeout(task_type)
        
        logger.info(f"Routing: {task_type} → {backend.value} ({model})")
        
        # Try primary backend
        result = await self._call_backend(
            backend, prompt, system_prompt, model, max_tokens, temperature, timeout
        )
        
        # If failed, try fallback
        if not result.success and backend != BackendType.OLLAMA:
            logger.info(f"Primary failed, trying Ollama fallback...")
            result = await self._call_backend(
                BackendType.OLLAMA, prompt, system_prompt, model, max_tokens, temperature, timeout
            )
        
        # Calculate latency
        result.latency_ms = (time.time() - start_time) * 1000
        
        # Update stats
        if result.success:
            self.stats["successful"] += 1
            self.stats["by_backend"][result.backend] += 1
            self.stats["total_latency_ms"] += result.latency_ms
            self.stats["total_cost"] += result.cost
        else:
            self.stats["failed"] += 1
        
        return result
    
    async def _call_backend(
        self,
        backend: BackendType,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        max_tokens: int,
        temperature: float,
        timeout: float
    ) -> RouteResult:
        """Call a specific backend."""
        if backend == BackendType.GPU_BRIDGE:
            return await self._call_gpu_bridge(
                prompt, system_prompt, model, max_tokens, temperature, timeout
            )
        elif backend == BackendType.OLLAMA:
            return await self._call_ollama(
                prompt, system_prompt, model, max_tokens, temperature, timeout
            )
        else:
            return RouteResult(
                response="",
                backend=backend.value,
                model=model,
                latency_ms=0,
                tokens=0,
                success=False,
                error=f"Unknown backend: {backend}"
            )
    
    async def _call_gpu_bridge(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        max_tokens: int,
        temperature: float,
        timeout: float
    ) -> RouteResult:
        """Call GPU Bridge."""
        try:
            # Build request
            payload = {
                "prompt": prompt,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            
            if system_prompt:
                payload["system_prompt"] = system_prompt
            
            # Call GPU Bridge
            r = await self.http_client.post(
                f"{GPU_BRIDGE_URL}/generate",
                json=payload,
                timeout=timeout
            )
            
            if r.status_code == 200:
                data = r.json()
                return RouteResult(
                    response=data.get("response", data.get("text", "")),
                    backend="gpu_bridge",
                    model=data.get("model", model),
                    latency_ms=data.get("latency_ms", 0),
                    tokens=data.get("tokens", len(data.get("response", "").split())),
                    cost=0.0,  # GPU Bridge is pre-paid
                    success=True
                )
            else:
                return RouteResult(
                    response="",
                    backend="gpu_bridge",
                    model=model,
                    latency_ms=0,
                    tokens=0,
                    success=False,
                    error=f"HTTP {r.status_code}: {r.text[:100]}"
                )
                
        except Exception as e:
            return RouteResult(
                response="",
                backend="gpu_bridge",
                model=model,
                latency_ms=0,
                tokens=0,
                success=False,
                error=str(e)
            )
    
    async def _call_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        max_tokens: int,
        temperature: float,
        timeout: float
    ) -> RouteResult:
        """Call local Ollama."""
        try:
            # Build prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant:"
            
            payload = {
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature
                }
            }
            
            r = await self.http_client.post(
                f"{LOCAL_OLLAMA_URL}/api/generate",
                json=payload,
                timeout=timeout
            )
            
            if r.status_code == 200:
                data = r.json()
                response_text = data.get("response", "")
                return RouteResult(
                    response=response_text,
                    backend="ollama",
                    model=data.get("model", model),
                    latency_ms=0,
                    tokens=len(response_text.split()),
                    cost=0.0,  # Free!
                    success=True
                )
            else:
                return RouteResult(
                    response="",
                    backend="ollama",
                    model=model,
                    latency_ms=0,
                    tokens=0,
                    success=False,
                    error=f"HTTP {r.status_code}"
                )
                
        except Exception as e:
            return RouteResult(
                response="",
                backend="ollama",
                model=model,
                latency_ms=0,
                tokens=0,
                success=False,
                error=str(e)
            )
    
    def get_status(self) -> Dict:
        """Get router status."""
        return {
            "backends": {
                b.value: {
                    "healthy": self.backends[b]["healthy"],
                    "requests": self.stats["by_backend"][b.value]
                }
                for b in [BackendType.GPU_BRIDGE, BackendType.OLLAMA]
            },
            "stats": {
                "total_requests": self.stats["total_requests"],
                "successful": self.stats["successful"],
                "failed": self.stats["failed"],
                "success_rate": self.stats["successful"] / max(1, self.stats["total_requests"]),
                "avg_latency_ms": self.stats["total_latency_ms"] / max(1, self.stats["successful"]),
                "total_cost": self.stats["total_cost"]
            }
        }


# Singleton instance
_router: Optional[AriaRouter] = None


async def get_router() -> AriaRouter:
    """Get or create the global router instance."""
    global _router
    if _router is None:
        _router = AriaRouter()
        await _router.check_health()
    return _router


