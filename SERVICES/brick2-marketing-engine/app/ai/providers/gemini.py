"""
Gemini Provider for BRICK 2
===========================

Specialized Google Gemini integration for:
- Market research
- Data analysis
- Multimodal content
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class GeminiConfig:
    """Gemini provider configuration"""
    api_key: str = None
    model: str = "models/gemini-2.5-pro"  # Gemini 2.5 Pro (latest available)
    max_tokens: int = 4096
    temperature: float = 0.7


class GeminiProvider:
    """
    Gemini-specific provider with marketing capabilities.
    
    Best for:
    - Fast analysis tasks
    - Market research
    - Data summarization
    - Multimodal content (images + text)
    """
    
    def __init__(self, config: GeminiConfig = None):
        self.config = config or GeminiConfig()
        self.config.api_key = self.config.api_key or os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        self._genai = None
        self._model = None
        
        if self.config.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.config.api_key)
                self._genai = genai
                self._model = genai.GenerativeModel(self.config.model)
            except ImportError:
                pass
    
    @property
    def is_available(self) -> bool:
        return self._model is not None
    
    async def generate(
        self,
        prompt: str,
        system: str = None,
        max_tokens: int = None,
        temperature: float = None,
    ) -> Dict[str, Any]:
        """
        Generate with Gemini.
        
        Args:
            prompt: User prompt
            system: System instruction (prepended to prompt)
            max_tokens: Override max tokens
            temperature: Override temperature
            
        Returns:
            Dict with content and metadata
        """
        if not self._model:
            raise RuntimeError("Gemini client not initialized. Check GOOGLE_AI_API_KEY.")
        
        # Combine system and user prompt
        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"
        
        # Generate
        response = self._model.generate_content(
            full_prompt,
            generation_config={
                "max_output_tokens": max_tokens or self.config.max_tokens,
                "temperature": temperature or self.config.temperature,
            },
        )
        
        # Gemini has very low pricing
        cost = 0.001  # Approximate
        
        return {
            "content": response.text,
            "model": self.config.model,
            "input_tokens": 0,  # Not exposed by Gemini
            "output_tokens": 0,
            "cost_usd": cost,
        }
    
    async def research(self, topic: str, **kwargs) -> Dict[str, Any]:
        """Conduct market research"""
        system = """You are a market research analyst. Provide:
1. Market overview and size
2. Key trends and drivers
3. Competitive landscape
4. Opportunities and threats
5. Recommendations

Be specific with data and insights."""
        
        return await self.generate(
            f"Research topic: {topic}",
            system=system,
            **kwargs,
        )
    
    async def analyze_data(self, data: str, question: str, **kwargs) -> Dict[str, Any]:
        """Analyze data and answer questions"""
        prompt = f"""Data:
{data}

Question: {question}

Provide a clear, data-driven answer."""
        
        return await self.generate(prompt, **kwargs)
    
    async def summarize(self, text: str, length: str = "medium", **kwargs) -> Dict[str, Any]:
        """Summarize text"""
        length_instructions = {
            "short": "Summarize in 2-3 sentences.",
            "medium": "Summarize in a paragraph (5-7 sentences).",
            "long": "Provide a detailed summary with key points.",
        }
        
        prompt = f"""{length_instructions.get(length, length_instructions['medium'])}

Text to summarize:
{text}"""
        
        return await self.generate(prompt, **kwargs)
    
    async def competitor_analysis(self, company: str, competitors: List[str], **kwargs) -> Dict[str, Any]:
        """Analyze competitors"""
        prompt = f"""Analyze {company} against these competitors: {', '.join(competitors)}

Compare:
1. Value proposition
2. Target audience
3. Pricing strategy
4. Marketing approach
5. Strengths and weaknesses

Provide actionable competitive insights."""
        
        return await self.generate(prompt, **kwargs)

