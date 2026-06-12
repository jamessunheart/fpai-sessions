"""
AI Creative Generator

Generate ad copy variations using AI Brain service.
"""
import httpx
from typing import List, Dict, Optional
from datetime import datetime
import json

from app.config import settings
from app.schemas.creative import GeneratedCreative


class CreativeAIGenerator:
    """
    Generate ad creative copy using AI
    
    Uses the AI Brain service (Claude/GPT) for intelligent copy generation
    """
    
    def __init__(self, brain_url: str = None):
        self.brain_url = brain_url or settings.AI_BRAIN_URL
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def generate_variations(
        self,
        offer,
        tone: str = "professional",
        num_variations: int = 3,
        focus_points: List[str] = None,
        target_audience: str = None
    ) -> List[GeneratedCreative]:
        """
        Generate ad copy variations for an offer
        
        Args:
            offer: Offer model instance
            tone: professional, casual, urgent, inspirational
            num_variations: Number of variations to generate (1-5)
            focus_points: Key benefits to highlight
            target_audience: Description of target audience
            
        Returns:
            List of GeneratedCreative instances
        """
        # Build the prompt
        prompt = self._build_prompt(
            offer_name=offer.name,
            offer_description=offer.description or "",
            offer_price=float(offer.price),
            tone=tone,
            num_variations=num_variations,
            focus_points=focus_points,
            target_audience=target_audience
        )
        
        try:
            # Call AI Brain
            response = await self.client.post(
                f"{self.brain_url}/api/generate",
                json={
                    "prompt": prompt,
                    "max_tokens": 2000,
                    "temperature": 0.8,  # Creative temperature
                    "system": "You are an expert Facebook/Instagram ad copywriter. Generate compelling, high-converting ad copy."
                }
            )
            response.raise_for_status()
            result = response.json()
            
            # Parse AI response
            content = result.get("content") or result.get("response") or result.get("text", "")
            return self._parse_variations(content, num_variations)
            
        except Exception as e:
            # Fallback to template-based generation
            return self._generate_fallback(offer, tone, num_variations)
    
    def _build_prompt(
        self,
        offer_name: str,
        offer_description: str,
        offer_price: float,
        tone: str,
        num_variations: int,
        focus_points: List[str] = None,
        target_audience: str = None
    ) -> str:
        """Build the AI prompt for creative generation"""
        
        tone_descriptions = {
            "professional": "confident, trustworthy, authoritative",
            "casual": "friendly, conversational, relatable",
            "urgent": "time-sensitive, action-oriented, compelling",
            "inspirational": "motivating, empowering, transformational"
        }
        
        prompt = f"""Generate {num_variations} Facebook/Instagram ad copy variations for this coaching offer:

OFFER DETAILS:
- Name: {offer_name}
- Description: {offer_description}
- Price: ${offer_price:,.2f}
- Tone: {tone} ({tone_descriptions.get(tone, '')})
"""
        
        if focus_points:
            prompt += f"\nKEY BENEFITS TO HIGHLIGHT:\n"
            for point in focus_points:
                prompt += f"- {point}\n"
        
        if target_audience:
            prompt += f"\nTARGET AUDIENCE: {target_audience}\n"
        
        prompt += """
REQUIREMENTS FOR EACH VARIATION:
1. Headline: Max 40 characters, attention-grabbing
2. Primary Text: Max 125 characters, address pain point and promise transformation
3. Description: Max 30 characters, supporting detail
4. Image Prompt: Description for AI image generation (what visual would work best)

FORMAT YOUR RESPONSE AS JSON:
[
  {
    "variation": "A",
    "headline": "...",
    "primary_text": "...",
    "description": "...",
    "image_prompt": "...",
    "reasoning": "Why this approach works"
  },
  ...
]

Make each variation distinctly different in approach:
- Variation A: Problem-focused (address pain points)
- Variation B: Solution-focused (highlight transformation)
- Variation C: Social proof / credibility focused

Be specific, avoid generic claims. Focus on emotional triggers and clear benefits."""

        return prompt
    
    def _parse_variations(self, content: str, expected_count: int) -> List[GeneratedCreative]:
        """Parse AI response into GeneratedCreative objects"""
        variations = []
        
        try:
            # Try to extract JSON from response
            # AI might wrap it in markdown code blocks
            content = content.strip()
            if content.startswith("```"):
                # Remove markdown code blocks
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            
            data = json.loads(content)
            
            for item in data:
                variations.append(GeneratedCreative(
                    variation=item.get("variation", chr(65 + len(variations))),
                    headline=item.get("headline", "")[:255],
                    primary_text=item.get("primary_text", ""),
                    description=item.get("description", "")[:100],
                    image_prompt=item.get("image_prompt", "Professional coaching session"),
                    reasoning=item.get("reasoning")
                ))
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract manually or use fallback
            pass
        
        return variations
    
    def _generate_fallback(
        self,
        offer,
        tone: str,
        num_variations: int
    ) -> List[GeneratedCreative]:
        """Generate template-based variations if AI fails"""
        
        templates = {
            "A": {
                "headline": f"Transform Your {self._get_benefit_word(offer.name)}",
                "primary_text": f"Stop struggling. Get expert coaching that actually works. {offer.name} - results guaranteed.",
                "description": "Start your journey today",
                "image_prompt": "Professional coach guiding a successful client, warm lighting, trust"
            },
            "B": {
                "headline": f"Ready for Real Results?",
                "primary_text": f"Join hundreds who've transformed their lives with {offer.name}. Limited spots available.",
                "description": "Book your session now",
                "image_prompt": "Before/after transformation, professional setting, success"
            },
            "C": {
                "headline": f"Expert Coaching, Real Change",
                "primary_text": f"${offer.price:,.0f} investment. Lifetime of results. {offer.name} is your next step to success.",
                "description": "Transform today",
                "image_prompt": "Confident professional celebrating achievement, aspirational"
            }
        }
        
        variations = []
        for i, (var, template) in enumerate(templates.items()):
            if i >= num_variations:
                break
            variations.append(GeneratedCreative(
                variation=var,
                headline=template["headline"][:40],
                primary_text=template["primary_text"][:125],
                description=template["description"][:30],
                image_prompt=template["image_prompt"],
                reasoning=f"Template fallback - {var} variation"
            ))
        
        return variations
    
    def _get_benefit_word(self, offer_name: str) -> str:
        """Extract or infer benefit keyword from offer name"""
        benefit_words = ["Life", "Career", "Business", "Success", "Growth", "Future"]
        name_lower = offer_name.lower()
        
        for word in benefit_words:
            if word.lower() in name_lower:
                return word
        
        return "Success"
    
    async def improve_creative(
        self,
        creative,
        metrics: Dict,
        suggestion_type: str = "ctr"
    ) -> GeneratedCreative:
        """
        Generate improved version of underperforming creative
        
        Args:
            creative: Creative model instance
            metrics: Performance metrics (ctr, conversions, etc.)
            suggestion_type: What to optimize for (ctr, conversions, cpa)
            
        Returns:
            Improved GeneratedCreative
        """
        prompt = f"""Improve this underperforming Facebook ad:

CURRENT AD:
Headline: {creative.headline}
Primary Text: {creative.primary_text}
Description: {creative.description}

PERFORMANCE:
- CTR: {metrics.get('ctr', 0):.2f}%
- Conversions: {metrics.get('conversions', 0)}
- CPA: ${metrics.get('cpa', 0):.2f}

OPTIMIZE FOR: {suggestion_type}

Suggest an improved version with reasoning. Keep the same format but make it more compelling.
Output as JSON with keys: headline, primary_text, description, image_prompt, reasoning"""

        try:
            response = await self.client.post(
                f"{self.brain_url}/api/generate",
                json={"prompt": prompt, "max_tokens": 500, "temperature": 0.7}
            )
            response.raise_for_status()
            result = response.json()
            
            content = result.get("content", "")
            variations = self._parse_variations(content, 1)
            
            if variations:
                return variations[0]
        except:
            pass
        
        # Return original if improvement fails
        return GeneratedCreative(
            variation="IMPROVED",
            headline=creative.headline,
            primary_text=creative.primary_text,
            description=creative.description or "",
            image_prompt="Professional coaching, success",
            reasoning="Could not generate improvement"
        )


