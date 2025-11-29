"""
OpenAI Provider for BRICK 2
===========================

Specialized OpenAI integration for:
- Conversational AI (chatbots)
- Function calling
- Lead qualification
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class OpenAIConfig:
    """OpenAI provider configuration"""
    api_key: str = None
    model: str = "gpt-5.1"  # GPT 5.1 (latest)
    max_tokens: int = 4096
    temperature: float = 0.7


class OpenAIProvider:
    """
    OpenAI-specific provider with marketing capabilities.
    
    Best for:
    - Conversational interactions
    - Function calling / tool use
    - Quick classification tasks
    - Chat-based lead qualification
    """
    
    def __init__(self, config: OpenAIConfig = None):
        self.config = config or OpenAIConfig()
        self.config.api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
        
        self._client = None
        if self.config.api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.config.api_key)
            except ImportError:
                pass
    
    @property
    def is_available(self) -> bool:
        return self._client is not None
    
    async def generate(
        self,
        prompt: str,
        system: str = None,
        messages: List[Dict] = None,
        max_tokens: int = None,
        temperature: float = None,
        functions: List[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Generate with OpenAI.
        
        Args:
            prompt: User prompt (ignored if messages provided)
            system: System prompt
            messages: Full message history (for conversations)
            max_tokens: Override max tokens
            temperature: Override temperature
            functions: Function definitions for function calling
            
        Returns:
            Dict with content, tokens, cost, function_call
        """
        if not self._client:
            raise RuntimeError("OpenAI client not initialized. Check OPENAI_API_KEY.")
        
        # Build messages
        if messages is None:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
        
        # API call
        kwargs = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
        }
        
        if functions:
            kwargs["tools"] = [{"type": "function", "function": f} for f in functions]
        
        response = self._client.chat.completions.create(**kwargs)
        
        # Extract response
        choice = response.choices[0]
        content = choice.message.content or ""
        function_call = None
        
        if choice.message.tool_calls:
            function_call = {
                "name": choice.message.tool_calls[0].function.name,
                "arguments": choice.message.tool_calls[0].function.arguments,
            }
        
        # Cost calculation (GPT-4o pricing)
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = (input_tokens * 2.5 + output_tokens * 10.0) / 1_000_000
        
        return {
            "content": content,
            "model": self.config.model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
            "function_call": function_call,
        }
    
    async def chat(
        self,
        messages: List[Dict],
        system: str = "You are a helpful marketing assistant.",
        **kwargs,
    ) -> Dict[str, Any]:
        """Continue a conversation"""
        full_messages = [{"role": "system", "content": system}] + messages
        return await self.generate(prompt="", messages=full_messages, **kwargs)
    
    async def classify(
        self,
        text: str,
        categories: List[str],
        **kwargs,
    ) -> Dict[str, Any]:
        """Classify text into categories"""
        prompt = f"""Classify the following text into one of these categories: {', '.join(categories)}

Text: {text}

Return only the category name, nothing else."""
        
        result = await self.generate(prompt, temperature=0.1, **kwargs)
        result["category"] = result["content"].strip()
        return result
    
    async def extract(
        self,
        text: str,
        schema: Dict,
        **kwargs,
    ) -> Dict[str, Any]:
        """Extract structured data using function calling"""
        functions = [{
            "name": "extract_data",
            "description": "Extract structured data from text",
            "parameters": schema,
        }]
        
        return await self.generate(
            f"Extract the following information from this text:\n\n{text}",
            functions=functions,
            **kwargs,
        )

