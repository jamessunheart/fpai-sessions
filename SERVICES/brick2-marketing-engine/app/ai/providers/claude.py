"""
Claude Provider for BRICK 2
===========================

Specialized Claude integration for marketing tasks:
- Content generation (emails, ads, social posts)
- Strategic planning
- Complex reasoning
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class ClaudeConfig:
    """Claude provider configuration"""
    api_key: str = None
    model: str = "claude-opus-4-5-20250514"  # Claude Opus 4.5 (latest)
    max_tokens: int = 4096
    temperature: float = 0.7


class ClaudeProvider:
    """
    Claude-specific provider with marketing prompts.
    
    Best for:
    - Long-form content generation
    - Email sequences
    - Strategic analysis
    - Complex reasoning tasks
    """
    
    # Marketing-specific system prompts
    PROMPTS = {
        "email_copywriter": """You are an expert email copywriter specializing in B2B marketing.
Write emails that:
- Have compelling subject lines (50 chars max)
- Open with a hook that creates curiosity
- Focus on benefits, not features
- Include a clear call-to-action
- Sound human and conversational
- Are optimized for mobile reading (short paragraphs)""",

        "social_media": """You are a social media marketing expert.
Create content that:
- Stops the scroll with a strong hook
- Uses appropriate hashtags
- Includes engagement triggers (questions, CTAs)
- Matches platform best practices
- Is optimized for the algorithm""",

        "ad_copywriter": """You are a direct response ad copywriter.
Write ad copy that:
- Grabs attention in the first line
- Identifies the pain point
- Presents the solution
- Includes social proof when possible
- Has a compelling CTA
- Is A/B test ready (provide variations)""",

        "content_strategist": """You are a content marketing strategist.
Analyze and plan:
- Content gaps and opportunities
- SEO keyword targeting
- Content calendar recommendations
- Funnel stage mapping
- Conversion optimization""",

        "lead_qualifier": """You are a sales qualification expert.
Analyze lead data to determine:
- BANT score (Budget, Authority, Need, Timeline)
- Pain points and buying signals
- Recommended approach
- Follow-up priority
- Objection handling strategies""",
    }
    
    def __init__(self, config: ClaudeConfig = None):
        self.config = config or ClaudeConfig()
        self.config.api_key = self.config.api_key or os.getenv("ANTHROPIC_API_KEY")
        
        self._client = None
        if self.config.api_key:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.config.api_key)
            except ImportError:
                pass
    
    @property
    def is_available(self) -> bool:
        return self._client is not None
    
    async def generate(
        self,
        prompt: str,
        persona: str = None,
        system: str = None,
        max_tokens: int = None,
        temperature: float = None,
    ) -> Dict[str, Any]:
        """
        Generate with Claude.
        
        Args:
            prompt: User prompt
            persona: Use a predefined persona (email_copywriter, social_media, etc.)
            system: Custom system prompt (overrides persona)
            max_tokens: Override max tokens
            temperature: Override temperature
            
        Returns:
            Dict with content, tokens, cost
        """
        if not self._client:
            raise RuntimeError("Claude client not initialized. Check ANTHROPIC_API_KEY.")
        
        # Build system prompt
        if system is None and persona:
            system = self.PROMPTS.get(persona, self.PROMPTS["content_strategist"])
        elif system is None:
            system = "You are a helpful marketing AI assistant."
        
        message = self._client.messages.create(
            model=self.config.model,
            max_tokens=max_tokens or self.config.max_tokens,
            temperature=temperature or self.config.temperature,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        
        # Cost calculation (Claude 3.5 Sonnet pricing)
        cost = (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000
        
        return {
            "content": message.content[0].text,
            "model": self.config.model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
        }
    
    # Convenience methods
    async def email(self, context: str, **kwargs) -> Dict[str, Any]:
        """Generate email copy"""
        return await self.generate(context, persona="email_copywriter", **kwargs)
    
    async def social_post(self, context: str, platform: str = "linkedin", **kwargs) -> Dict[str, Any]:
        """Generate social media post"""
        prompt = f"Platform: {platform}\n\n{context}"
        return await self.generate(prompt, persona="social_media", **kwargs)
    
    async def ad_copy(self, product: str, audience: str, **kwargs) -> Dict[str, Any]:
        """Generate ad copy with variations"""
        prompt = f"""Product/Service: {product}
Target Audience: {audience}

Generate 3 ad copy variations with different angles."""
        return await self.generate(prompt, persona="ad_copywriter", **kwargs)
    
    async def qualify(self, lead_data: str, **kwargs) -> Dict[str, Any]:
        """Qualify a lead"""
        return await self.generate(lead_data, persona="lead_qualifier", **kwargs)

