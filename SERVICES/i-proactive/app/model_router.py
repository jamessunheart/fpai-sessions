"""Intelligent multi-model routing for optimal task execution with optimization"""

from typing import Optional, Dict, Any
from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai
import httpx

from .config import settings
from .models import ModelType, Task
from .optimization_engine import OptimizationEngine


class ModelRouter:
    """Routes tasks to optimal AI models based on task characteristics"""

    def __init__(self):
        """Initialize model clients"""
        self.openai_client = None
        self.anthropic_client = None
        self.gemini_client = None
        self.ollama_endpoint = None

        # Initialize optimization engine
        self.optimizer = OptimizationEngine()

        # Initialize available clients
        if settings.openai_api_key:
            self.openai_client = OpenAI(api_key=settings.openai_api_key)

        if settings.anthropic_api_key:
            self.anthropic_client = Anthropic(api_key=settings.anthropic_api_key)

        if settings.google_api_key:
            genai.configure(api_key=settings.google_api_key)
            self.gemini_client = genai

        # Ollama is always available if endpoint is configured
        if settings.ollama_endpoint:
            self.ollama_endpoint = settings.ollama_endpoint

    def select_model(self, task: Task) -> ModelType:
        """
        Intelligently select the best model for a task.

        Selection criteria (SOVEREIGN FIRST):
        - Prefer local Llama 3.1 for sovereignty and $0 cost
        - Fallback to corporate APIs only for complex tasks
        - Code generation: Claude (best at structured code) OR Llama
        - Complex reasoning: GPT-4 OR Llama
        - Analysis/summarization: Llama (fast, local, free)
        - Strategic decisions: Llama (sovereign decision making)
        """
        if task.preferred_model != ModelType.AUTO:
            return task.preferred_model

        # SOVEREIGNTY: Default to local Llama if available
        if self.ollama_endpoint:
            # For now, use Llama for everything (it's capable of all tasks)
            # Later we can add smart routing for complex tasks
            return ModelType.LLAMA_3_1_8B

        # Keyword-based intelligent routing (fallback to corporate APIs)
        description_lower = task.description.lower()

        # Code generation -> Claude
        if any(word in description_lower for word in ["code", "implement", "build", "create file", "write code"]):
            return ModelType.CLAUDE_SONNET if self.anthropic_client else ModelType.GPT4

        # Complex reasoning -> GPT-4
        if any(word in description_lower for word in ["analyze", "decide", "strategy", "plan", "evaluate"]):
            return ModelType.GPT4_TURBO if self.openai_client else ModelType.CLAUDE_OPUS

        # Fast analysis -> Gemini
        if any(word in description_lower for word in ["summarize", "extract", "classify", "categorize"]):
            return ModelType.GEMINI_PRO if self.gemini_client else ModelType.GPT4

        # Default to GPT-4 if available
        if self.openai_client:
            return ModelType.GPT4
        elif self.anthropic_client:
            return ModelType.CLAUDE_SONNET
        elif self.gemini_client:
            return ModelType.GEMINI_PRO
        else:
            raise Exception("No AI models configured. Please add API keys to .env")

    async def execute_task(
        self,
        task: Task,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:
        """
        Execute a task using the selected model.

        Returns:
            {
                "result": str,
                "model_used": ModelType,
                "tokens_used": int,
                "cost_usd": float
            }
        """
        model = self.select_model(task)

        # Build prompt
        user_prompt = f"""Task: {task.title}

Description: {task.description}

Context: {task.context if task.context else 'None'}

Please complete this task thoroughly and return the result."""

        # Execute with selected model
        if model == ModelType.LLAMA_3_1_8B:
            return await self._execute_ollama(system_prompt, user_prompt, max_tokens)
        elif model in [ModelType.GPT4, ModelType.GPT4_TURBO]:
            return await self._execute_openai(model, system_prompt, user_prompt, max_tokens)
        elif model in [ModelType.CLAUDE_OPUS, ModelType.CLAUDE_SONNET]:
            return await self._execute_anthropic(model, system_prompt, user_prompt, max_tokens)
        elif model == ModelType.GEMINI_PRO:
            return await self._execute_gemini(system_prompt, user_prompt, max_tokens)
        else:
            raise ValueError(f"Unsupported model: {model}")

    async def _execute_openai(
        self,
        model: ModelType,
        system_prompt: Optional[str],
        user_prompt: str,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Execute using OpenAI API"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = self.openai_client.chat.completions.create(
            model=model.value,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7
        )

        return {
            "result": response.choices[0].message.content,
            "model_used": model,
            "tokens_used": response.usage.total_tokens,
            "cost_usd": self._calculate_openai_cost(model, response.usage.total_tokens)
        }

    async def _execute_anthropic(
        self,
        model: ModelType,
        system_prompt: Optional[str],
        user_prompt: str,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Execute using Anthropic Claude API"""
        message = self.anthropic_client.messages.create(
            model=model.value,
            max_tokens=max_tokens,
            system=system_prompt if system_prompt else "You are a helpful AI assistant.",
            messages=[{"role": "user", "content": user_prompt}]
        )

        tokens_used = message.usage.input_tokens + message.usage.output_tokens

        return {
            "result": message.content[0].text,
            "model_used": model,
            "tokens_used": tokens_used,
            "cost_usd": self._calculate_anthropic_cost(model, message.usage.input_tokens, message.usage.output_tokens)
        }

    async def _execute_gemini(
        self,
        system_prompt: Optional[str],
        user_prompt: str,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Execute using Google Gemini API"""
        model = self.gemini_client.GenerativeModel('gemini-pro')

        full_prompt = user_prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{user_prompt}"

        response = model.generate_content(
            full_prompt,
            generation_config={'max_output_tokens': max_tokens}
        )

        return {
            "result": response.text,
            "model_used": ModelType.GEMINI_PRO,
            "tokens_used": 0,  # Gemini doesn't expose token counts easily
            "cost_usd": 0.001  # Approximate
        }

    async def _execute_ollama(
        self,
        system_prompt: Optional[str],
        user_prompt: str,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Execute using local Ollama (Llama 3.1 8B) - SOVEREIGN AI with CACHING"""
        # Build messages
        full_prompt = user_prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{user_prompt}"

        # Define the actual execution function for cache wrapping
        async def execute_ollama_call():
            # Call Ollama API (OpenAI-compatible endpoint)
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.ollama_endpoint}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": 0.7
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()

            return {
                "result": result.get("response", ""),
                "model_used": ModelType.LLAMA_3_1_8B,
                "tokens_used": 0,  # Ollama doesn't return token counts by default
                "cost_usd": 0.0  # LOCAL = FREE! Sovereignty costs $0
            }

        # Execute with optimization (caching + performance monitoring)
        return await self.optimizer.optimize_ai_call(
            prompt=full_prompt,
            model=settings.ollama_model,
            execute_func=execute_ollama_call
        )

    def _calculate_openai_cost(self, model: ModelType, total_tokens: int) -> float:
        """Calculate OpenAI API cost"""
        # Approximate pricing (per 1K tokens)
        pricing = {
            ModelType.GPT4: 0.03,
            ModelType.GPT4_TURBO: 0.01
        }
        price_per_1k = pricing.get(model, 0.01)
        return (total_tokens / 1000) * price_per_1k

    def _calculate_anthropic_cost(self, model: ModelType, input_tokens: int, output_tokens: int) -> float:
        """Calculate Anthropic API cost"""
        # Approximate pricing (per 1M tokens)
        input_price_per_1m = 3.0  # $3 per 1M input tokens
        output_price_per_1m = 15.0  # $15 per 1M output tokens

        input_cost = (input_tokens / 1_000_000) * input_price_per_1m
        output_cost = (output_tokens / 1_000_000) * output_price_per_1m

        return input_cost + output_cost

    def available_models(self) -> list[ModelType]:
        """Get list of available models based on configured API keys"""
        models = []

        # SOVEREIGN AI FIRST
        if self.ollama_endpoint:
            models.append(ModelType.LLAMA_3_1_8B)

        if self.openai_client:
            models.extend([ModelType.GPT4, ModelType.GPT4_TURBO])

        if self.anthropic_client:
            models.extend([ModelType.CLAUDE_OPUS, ModelType.CLAUDE_SONNET])

        if self.gemini_client:
            models.append(ModelType.GEMINI_PRO)

        return models
