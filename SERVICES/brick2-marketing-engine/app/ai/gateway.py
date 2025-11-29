"""
BRICK 2 AI Gateway
==================

Unified AI client that routes requests to the best available provider.
Supports Claude, OpenAI, and Gemini with intelligent task routing.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logging.basicConfig(level=logging.INFO)

# 🚀 AUTONOMOUS KEY INTEGRATION - Connect to Community Key Pool
try:
    core_path = str(Path(__file__).parent.parent.parent.parent.parent / "core")
    if core_path not in sys.path:
        sys.path.insert(0, core_path)
    from boot_autonomous import boot
    boot(verbose=False)
except Exception:
    pass

# Try to import the core API gateway client
try:
    # Add workspace root to path for core module access
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
    if workspace_root not in sys.path:
        sys.path.insert(0, workspace_root)
    from core.api_gateway_client import AIClient, Provider
    HAS_GATEWAY = True
except ImportError as e:
    print(f"Warning: Could not import API Gateway client: {e}")
    HAS_GATEWAY = False
    AIClient = None
    Provider = None


class AIProvider(str, Enum):
    """Supported AI providers"""
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    LLAMA = "llama"    # Local Llama via Ollama (FREE!)
    BRAIN = "brain"    # New AI Brain Service (Central Cognitive Gateway)
    AUTO = "auto"      # Let the gateway decide


class TaskType(str, Enum):
    """Task types for intelligent routing"""
    CONTENT_GENERATION = "content_generation"
    LEAD_QUALIFICATION = "lead_qualification"
    MARKET_RESEARCH = "market_research"
    DATA_ANALYSIS = "data_analysis"
    CONVERSATION = "conversation"
    CODE_GENERATION = "code_generation"
    STRATEGIC_PLANNING = "strategic_planning"


@dataclass
class AIResponse:
    """Standardized response from any AI provider"""
    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class AIGateway:
    """
    Unified AI Gateway for BRICK 2 Marketing Engine.
    
    Routes requests to optimal AI provider based on task type.
    Uses core API Gateway when available for metering.
    
    Usage:
        gateway = AIGateway()
        
        # Auto-route based on task
        response = await gateway.generate(
            prompt="Write a compelling email subject line",
            task_type=TaskType.CONTENT_GENERATION
        )
        
        # Force specific provider
        response = await gateway.generate(
            prompt="Analyze this lead data",
            provider=AIProvider.CLAUDE
        )
    """
    
    # Task-to-provider routing (best provider for each task)
    TASK_ROUTING = {
        TaskType.CONTENT_GENERATION: AIProvider.CLAUDE,      # Claude excels at writing
        TaskType.LEAD_QUALIFICATION: AIProvider.OPENAI,      # GPT-4 good at classification
        TaskType.MARKET_RESEARCH: AIProvider.GEMINI,         # Gemini good at analysis
        TaskType.DATA_ANALYSIS: AIProvider.GEMINI,           # Gemini multimodal
        TaskType.CONVERSATION: AIProvider.LLAMA,             # Llama FREE for conversations
        TaskType.CODE_GENERATION: AIProvider.CLAUDE,         # Claude best at code
        TaskType.STRATEGIC_PLANNING: AIProvider.CLAUDE,      # Claude for reasoning
    }
    
    # Model defaults - ABSOLUTE LATEST MODELS (Nov 2025)
    # Verified working via direct API testing
    DEFAULT_MODELS = {
        AIProvider.CLAUDE: "claude-opus-4-5",             # Claude Opus 4.5 (BEST - flagship)
        AIProvider.OPENAI: "gpt-5.1",                      # GPT-5.1 (LATEST!)
        AIProvider.GEMINI: "gemini-3-pro-preview",        # Gemini 3 Pro Preview (LATEST)
        AIProvider.LLAMA: "llama3.1:8b",                  # Llama 3.1 8B via Ollama (FREE!)
        AIProvider.BRAIN: "default",                      # AI Brain default model
    }
    
    # Fallback chain (try in order)
    FALLBACK_MODELS = {
        AIProvider.CLAUDE: ["claude-sonnet-4", "claude-3-5-sonnet", "claude-haiku"],
        AIProvider.OPENAI: ["gpt-5", "o3", "gpt-4o", "gpt-4o-mini"],
        AIProvider.GEMINI: ["models/gemini-2.5-pro", "models/gemini-2.5-flash"],
        AIProvider.LLAMA: ["llama3.1:8b", "llama2:7b"],   # Llama fallbacks
        AIProvider.BRAIN: [],                             # Brain handles its own fallbacks
    }
    
    # Ollama server URL (local to server)
    OLLAMA_URL = "http://localhost:11434"
    
    def __init__(
        self,
        anthropic_api_key: str = None,
        openai_api_key: str = None,
        google_api_key: str = None,
        brain_key: str = None,
        brain_url: str = None,
        use_gateway: bool = True,
        gateway_url: str = None,
    ):
        """
        Initialize AI Gateway.
        
        Args:
            anthropic_api_key: Claude API key (or from env ANTHROPIC_API_KEY)
            openai_api_key: OpenAI API key (or from env OPENAI_API_KEY)  
            google_api_key: Google AI key (or from env GOOGLE_AI_API_KEY)
            brain_key: AI Brain Service Key (or from env AI_BRAIN_SERVICE_KEY)
            brain_url: AI Brain URL (or from env AI_BRAIN_URL)
            use_gateway: Use core API gateway for metering (if available)
            gateway_url: Override gateway URL
        """
        self.anthropic_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.google_key = google_api_key or os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        self.brain_key = brain_key or os.getenv("AI_BRAIN_SERVICE_KEY")
        self.brain_url = brain_url or os.getenv("AI_BRAIN_URL", "http://198.54.123.234:8250")
        
        self.use_gateway = use_gateway and HAS_GATEWAY
        # Default to server gateway if not specified
        self.gateway_url = gateway_url or os.getenv("API_GATEWAY_URL", "http://198.54.123.234:8400")
        
        # Initialize gateway client if available
        self._gateway_client = None
        self._gateway_available = False  # Track if gateway is responding
        if self.use_gateway:
            self._gateway_client = AIClient(
                user_id="brick2-marketing",
                service_id="brick2-marketing-engine",
                gateway_url=self.gateway_url,
            )
            self._gateway_available = True  # Will be set to False on first failure
        
        # Try to fetch missing keys from API Portal
        self._fetch_keys_from_portal()
        
        # Initialize direct providers
        self._providers = {}
        self._init_providers()
    
    def _fetch_keys_from_portal(self):
        """Fetch missing API keys from the API Portal"""
        # Only try if we are missing keys
        if self.anthropic_key and self.openai_key and self.google_key:
            return

        # Portal URL (internal)
        portal_url = os.getenv("API_PORTAL_URL", "http://localhost:8060")
        
        try:
            import httpx
            
            # Helper to fetch key
            def fetch_key(api_name, capability):
                try:
                    # Using httpx sync client
                    with httpx.Client(timeout=2.0) as client:
                        resp = client.post(
                            f"{portal_url}/internal/request-key",
                            json={
                                "api_name": api_name,
                                "capability": capability,
                                "calling_service": "brick2-marketing-engine"
                            }
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            return data.get("api_key")
                except Exception:
                    pass
                return None

            if not self.anthropic_key:
                key = fetch_key("Claude API", "llm")
                if key:
                    self.anthropic_key = key
                    logging.info("✅ Fetched Claude key from API Portal")

            if not self.openai_key:
                key = fetch_key("OpenAI API", "llm")
                if key:
                    self.openai_key = key
                    logging.info("✅ Fetched OpenAI key from API Portal")

            if not self.google_key:
                key = fetch_key("Gemini API", "research")
                if key:
                    self.google_key = key
                    logging.info("✅ Fetched Gemini key from API Portal")

        except ImportError:
            logging.warning("httpx library not found, cannot fetch keys from portal")
        except Exception as e:
            logging.warning(f"Failed to fetch keys from API Portal: {e}")

    def _init_providers(self):
        """Initialize direct API clients for each provider"""
        if self.anthropic_key:
            try:
                from anthropic import Anthropic
                self._providers[AIProvider.CLAUDE] = Anthropic(api_key=self.anthropic_key)
            except ImportError:
                pass
        
        if self.openai_key:
            try:
                from openai import OpenAI
                self._providers[AIProvider.OPENAI] = OpenAI(api_key=self.openai_key)
            except ImportError:
                pass
        
        if self.google_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.google_key)
                self._providers[AIProvider.GEMINI] = genai
            except ImportError:
                pass
        
        # Llama via Ollama (always try - it's local and free!)
        try:
            import httpx
            # Quick check if Ollama is running
            resp = httpx.get(f"{self.OLLAMA_URL}/api/tags", timeout=2.0)
            if resp.status_code == 200:
                self._providers[AIProvider.LLAMA] = {"url": self.OLLAMA_URL}
                logging.info("✅ Ollama/Llama connected (FREE local inference)")
        except Exception:
            logging.debug("Ollama not available (optional)")
            
        # AI Brain Service (New 8250)
        if self.brain_key and self.brain_url:
            self._providers[AIProvider.BRAIN] = {"url": self.brain_url, "key": self.brain_key}
            logging.info("✅ AI Brain connected (Port 8250)")
    
    async def refresh_models(self) -> Dict[str, List[str]]:
        """
        Dynamically fetch available models from the API gateway.
        Updates DEFAULT_MODELS with the latest available.
        
        Returns:
            Dict mapping provider to list of available models
        """
        import httpx
        
        available = {
            "claude": [],
            "openai": [],
            "gemini": [],
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.gateway_url}/v1/pricing")
                if response.status_code == 200:
                    data = response.json()
                    pricing = data.get("pricing_per_million_tokens", {})
                    
                    for model_name in pricing.keys():
                        if model_name.startswith("claude"):
                            available["claude"].append(model_name)
                        elif model_name.startswith("gpt") or model_name.startswith("o"):
                            available["openai"].append(model_name)
                        elif model_name.startswith("gemini"):
                            available["gemini"].append(model_name)
                    
                    # Update defaults with best available (latest first)
                    if available["claude"]:
                        # Prefer opus > sonnet > haiku
                        for pref in ["opus", "sonnet", "haiku"]:
                            for m in available["claude"]:
                                if pref in m:
                                    self.DEFAULT_MODELS[AIProvider.CLAUDE] = m
                                    break
                            if self.DEFAULT_MODELS.get(AIProvider.CLAUDE) in available["claude"]:
                                break
                    
                    if available["openai"]:
                        # Prefer gpt-5 > o3 > gpt-4o
                        for pref in ["gpt-5", "o3", "gpt-4o"]:
                            for m in available["openai"]:
                                if pref in m:
                                    self.DEFAULT_MODELS[AIProvider.OPENAI] = m
                                    break
                            if self.DEFAULT_MODELS.get(AIProvider.OPENAI) in available["openai"]:
                                break
                    
                    if available["gemini"]:
                        # Prefer latest: 2.5-pro > 2.5-flash (add models/ prefix for Google API)
                        for pref in ["2.5-pro", "2.5-flash"]:
                            for m in available["gemini"]:
                                if pref in m:
                                    # Add models/ prefix for Google API compatibility
                                    self.DEFAULT_MODELS[AIProvider.GEMINI] = f"models/{m}" if not m.startswith("models/") else m
                                    break
                            if "2.5" in self.DEFAULT_MODELS.get(AIProvider.GEMINI, ""):
                                break
                    
                    print(f"✅ Models refreshed: Claude={self.DEFAULT_MODELS[AIProvider.CLAUDE]}, "
                          f"OpenAI={self.DEFAULT_MODELS[AIProvider.OPENAI]}, "
                          f"Gemini={self.DEFAULT_MODELS[AIProvider.GEMINI]}")
                    
        except Exception as e:
            print(f"⚠️ Could not refresh models: {e}")
        
        return available
    
    @property
    def available_providers(self) -> List[AIProvider]:
        """Get list of configured providers"""
        return list(self._providers.keys())
    
    @property
    def status(self) -> Dict[str, Any]:
        """Get gateway status"""
        return {
            "gateway_available": self.use_gateway,
            "providers": {
                "claude": AIProvider.CLAUDE in self._providers,
                "openai": AIProvider.OPENAI in self._providers,
                "gemini": AIProvider.GEMINI in self._providers,
                "llama": AIProvider.LLAMA in self._providers,  # FREE local!
                "brain": AIProvider.BRAIN in self._providers,  # New Brain
            },
            "default_models": {
                provider.value: model 
                for provider, model in self.DEFAULT_MODELS.items()
            },
            "default_routing": {
                task.value: provider.value 
                for task, provider in self.TASK_ROUTING.items()
            }
        }
    
    def select_provider(
        self, 
        task_type: TaskType = None,
        preferred: AIProvider = None
    ) -> AIProvider:
        """
        Select best provider for a task.
        
        Args:
            task_type: Type of task (for auto-routing)
            preferred: Preferred provider (overrides auto)
            
        Returns:
            Best available provider
        """
        # If using gateway, all providers are available through it
        if self._gateway_client:
            # If preferred, use it
            if preferred and preferred != AIProvider.AUTO:
                return preferred
            
            # Route based on task type
            if task_type:
                ideal = self.TASK_ROUTING.get(task_type)
                if ideal:
                    return ideal
            
            # Default to Claude for general tasks
            return AIProvider.CLAUDE
        
        # Fallback to local providers
        # If preferred and available, use it
        if preferred and preferred != AIProvider.AUTO:
            if preferred in self._providers:
                return preferred
        
        # Route based on task type
        if task_type:
            ideal = self.TASK_ROUTING.get(task_type)
            if ideal and ideal in self._providers:
                return ideal
        
        # Fall back to first available
        if self._providers:
            return list(self._providers.keys())[0]
        
        raise ValueError("No AI providers configured. Add API keys to environment or connect to gateway.")
    
    async def generate(
        self,
        prompt: str,
        system: str = None,
        provider: AIProvider = AIProvider.AUTO,
        task_type: TaskType = None,
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> AIResponse:
        """
        Generate AI response with automatic fallback.
        
        Args:
            prompt: User prompt
            system: System prompt (instructions)
            provider: Force specific provider (or AUTO)
            task_type: Task type for auto-routing
            model: Override model
            max_tokens: Max response tokens
            temperature: Sampling temperature
            
        Returns:
            AIResponse with content and metadata
        """
        # Select provider
        selected = self.select_provider(task_type, provider)
        
        # Try gateway first with fallback to direct
        if self._gateway_client and self._gateway_available:
            try:
                return await self._generate_via_gateway(
                    prompt, system, selected, model, max_tokens, temperature
                )
            except Exception as e:
                logging.warning(f"Gateway failed, falling back to direct: {e}")
                self._gateway_available = False
        
        # Direct API call (fallback or primary when no gateway)
        if self._providers:
            # Check if selected provider is available locally
            if selected not in self._providers:
                logging.warning(f"Provider {selected} not available locally, falling back to first available")
                selected = list(self._providers.keys())[0]
            
            try:
                return await self._generate_direct(
                    prompt, system, selected, model, max_tokens, temperature
                )
            except Exception as e:
                logging.error(f"Direct API call to {selected} failed: {e}")
                # Try fallback to another provider
                for fallback_provider in self._providers.keys():
                    if fallback_provider != selected:
                        try:
                            logging.info(f"Falling back to {fallback_provider}")
                            return await self._generate_direct(
                                prompt, system, fallback_provider, None, max_tokens, temperature
                            )
                        except Exception as fe:
                            logging.error(f"Fallback to {fallback_provider} also failed: {fe}")
                raise RuntimeError(f"All providers failed. Last error: {e}")
        
        raise RuntimeError("No AI providers available. Configure ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY.")
    
    async def _generate_via_gateway(
        self,
        prompt: str,
        system: str,
        provider: AIProvider,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> AIResponse:
        """Generate using core API Gateway (with metering)"""
        model = model or self.DEFAULT_MODELS[provider]
        
        # Llama is always direct (local, not through gateway)
        if provider == AIProvider.LLAMA:
            return await self._call_llama(prompt, system, model, max_tokens, temperature)
        
        # Map to gateway provider enum
        gateway_provider = {
            AIProvider.CLAUDE: "anthropic",
            AIProvider.OPENAI: "openai",
            AIProvider.GEMINI: "gemini",
        }.get(provider)
        
        response = await self._gateway_client.chat(
            provider=gateway_provider,
            model=model,
            messages=[{"role": "user", "content": prompt}],
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return AIResponse(
            content=response.content,
            provider=provider.value,
            model=response.model,
            input_tokens=response.usage.get("input_tokens", 0),
            output_tokens=response.usage.get("output_tokens", 0),
            cost_usd=response.cost_usd,
            metadata={"request_id": response.request_id},
        )
    
    async def _generate_direct(
        self,
        prompt: str,
        system: str,
        provider: AIProvider,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> AIResponse:
        """Generate using direct API calls"""
        model = model or self.DEFAULT_MODELS[provider]
        
        if provider == AIProvider.CLAUDE:
            return await self._call_claude(prompt, system, model, max_tokens, temperature)
        elif provider == AIProvider.OPENAI:
            return await self._call_openai(prompt, system, model, max_tokens, temperature)
        elif provider == AIProvider.GEMINI:
            return await self._call_gemini(prompt, system, model, max_tokens, temperature)
        elif provider == AIProvider.LLAMA:
            return await self._call_llama(prompt, system, model, max_tokens, temperature)
        elif provider == AIProvider.BRAIN:
            return await self._call_brain(prompt, system, model, max_tokens, temperature)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def _call_brain(
        self, prompt: str, system: str, model: str, max_tokens: int, temperature: float
    ) -> AIResponse:
        """Call new AI Brain Service (Port 8250)"""
        import httpx
        
        config = self._providers[AIProvider.BRAIN]
        url = f"{config['url']}/ai/generate"
        key = config['key']
        
        # Build prompt with system instruction if supported or prepend
        full_prompt = prompt
        if system:
            full_prompt = f"System: {system}\n\nUser: {prompt}"
            
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={
                    "X-Service-Key": key,
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": full_prompt,
                    # Pass other params if the brain supports them, for now keep it simple based on curl example
                    "model": model if model != "default" else None,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"AI Brain error: {response.status_code} - {response.text}")
            
            data = response.json()
            
            # Parse response - adapting to unknown schema, assuming it might return 'response' or 'content'
            content = data.get("response") or data.get("content") or data.get("text") or str(data)
            
            return AIResponse(
                content=content,
                provider="brain",
                model=model or "default",
                input_tokens=0, 
                output_tokens=0,
                cost_usd=0.0,  # Internal service
                metadata=data
            )

    async def _call_claude(
        self, prompt: str, system: str, model: str, max_tokens: int, temperature: float
    ) -> AIResponse:
        """Direct Claude API call"""
        client = self._providers[AIProvider.CLAUDE]
        
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system or "You are a helpful marketing AI assistant.",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        
        return AIResponse(
            content=message.content[0].text,
            provider="claude",
            model=model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            cost_usd=self._estimate_cost("claude", message.usage.input_tokens, message.usage.output_tokens),
        )
    
    async def _call_openai(
        self, prompt: str, system: str, model: str, max_tokens: int, temperature: float
    ) -> AIResponse:
        """Direct OpenAI API call"""
        client = self._providers[AIProvider.OPENAI]
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        # GPT-5/O-series models don't support temperature and use max_completion_tokens
        is_advanced_model = model.startswith("gpt-5") or model.startswith("o1") or model.startswith("o3") or model.startswith("o4")
        
        if is_advanced_model:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=max_tokens,
                # No temperature for O-series/GPT-5
            )
        else:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        
        return AIResponse(
            content=response.choices[0].message.content or "",
            provider="openai",
            model=model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            cost_usd=self._estimate_cost("openai", response.usage.prompt_tokens, response.usage.completion_tokens),
        )
    
    async def _call_gemini(
        self, prompt: str, system: str, model: str, max_tokens: int, temperature: float
    ) -> AIResponse:
        """Direct Gemini API call"""
        genai = self._providers[AIProvider.GEMINI]
        
        # Gemini API works WITHOUT "models/" prefix when using GenerativeModel
        model_name = model.replace("models/", "") if model.startswith("models/") else model
        gemini_model = genai.GenerativeModel(model_name)
        
        # Simple prompt - avoid complex generation_config which can cause empty responses
        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"
        
        # Call without generation_config for reliability (Gemini has issues with it)
        response = gemini_model.generate_content(full_prompt)
        
        # Handle empty or blocked responses
        if not response.candidates or not response.candidates[0].content.parts:
            raise ValueError(f"Gemini returned empty response. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'unknown'}")
        
        return AIResponse(
            content=response.text,
            provider="gemini",
            model=model,
            input_tokens=0,  # Gemini doesn't expose
            output_tokens=0,
            cost_usd=0.001,  # Approximate
        )
    
    async def _call_llama(
        self, prompt: str, system: str, model: str, max_tokens: int, temperature: float
    ) -> AIResponse:
        """Direct Llama API call via Ollama (FREE local inference!)"""
        import httpx
        
        # Build prompt with system instruction
        full_prompt = prompt
        if system:
            full_prompt = f"[INST] {system} [/INST]\n\n{prompt}"
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.OLLAMA_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    }
                }
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Ollama error: {response.status_code} - {response.text}")
            
            data = response.json()
            
            return AIResponse(
                content=data.get("response", ""),
                provider="llama",
                model=model,
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
                cost_usd=0.0,  # FREE! Local inference
                metadata={
                    "total_duration_ms": data.get("total_duration", 0) / 1_000_000,
                    "eval_duration_ms": data.get("eval_duration", 0) / 1_000_000,
                }
            )
    
    def _estimate_cost(self, provider: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate API cost"""
        # Approximate pricing (per 1M tokens)
        pricing = {
            "claude": {"input": 3.0, "output": 15.0},
            "openai": {"input": 2.5, "output": 10.0},
            "gemini": {"input": 0.075, "output": 0.30},
            "llama": {"input": 0.0, "output": 0.0},  # FREE! Local inference
        }
        
        rates = pricing.get(provider, {"input": 1.0, "output": 5.0})
        input_cost = (input_tokens / 1_000_000) * rates["input"]
        output_cost = (output_tokens / 1_000_000) * rates["output"]
        
        return round(input_cost + output_cost, 6)
    
    # Convenience methods
    async def content(self, prompt: str, **kwargs) -> AIResponse:
        """Generate marketing content (uses Claude)"""
        return await self.generate(
            prompt, 
            task_type=TaskType.CONTENT_GENERATION,
            system="You are an expert marketing copywriter. Write compelling, conversion-focused content.",
            **kwargs
        )
    
    async def qualify_lead(self, lead_data: str, criteria: str = None, **kwargs) -> AIResponse:
        """Qualify a lead (uses OpenAI)"""
        system = f"""You are a lead qualification expert. Analyze the lead data and determine:
1. Lead quality score (0-100)
2. Key interests/needs
3. Recommended next action
4. Urgency level (low/medium/high)

{f'Qualification criteria: {criteria}' if criteria else ''}

Return your analysis as structured JSON."""
        
        return await self.generate(
            lead_data,
            system=system,
            task_type=TaskType.LEAD_QUALIFICATION,
            **kwargs
        )
    
    async def research(self, topic: str, **kwargs) -> AIResponse:
        """Market research (uses Gemini)"""
        return await self.generate(
            f"Research and analyze: {topic}",
            system="You are a market research analyst. Provide data-driven insights and actionable recommendations.",
            task_type=TaskType.MARKET_RESEARCH,
            **kwargs
        )
    
    async def close(self):
        """Close gateway client"""
        if self._gateway_client:
            await self._gateway_client.close()


# Singleton instance
_gateway = None

def get_gateway() -> AIGateway:
    """Get singleton AI Gateway instance"""
    global _gateway
    if _gateway is None:
        _gateway = AIGateway()
    return _gateway

