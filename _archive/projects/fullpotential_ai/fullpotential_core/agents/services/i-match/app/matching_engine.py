"""AI-powered matching engine using Ollama (Llama 3.1) and Claude API fallback"""

from typing import List, Dict, Any, Tuple
from anthropic import Anthropic
import httpx
import json

from .config import settings
from .database import Customer, Provider


class MatchingEngine:
    """
    AI-powered matching engine that finds optimal provider matches for customers.

    SOVEREIGNTY FIRST: Uses local Ollama (Llama 3.1) for $0 cost.
    Fallback to Claude API only if Ollama unavailable.

    Analyzes deep compatibility across multiple dimensions:
    - Service fit and expertise
    - Communication style compatibility
    - Values alignment
    - Location and logistics
    - Pricing fit
    - Availability and capacity
    """

    def __init__(self):
        """Initialize matching engine"""
        self.ollama_endpoint = settings.ollama_endpoint if settings.ollama_endpoint else None
        self.client = None
        if settings.anthropic_api_key:
            self.client = Anthropic(api_key=settings.anthropic_api_key)

    async def find_matches(
        self,
        customer: Customer,
        providers: List[Provider],
        max_matches: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find best provider matches for a customer.

        Args:
            customer: Customer seeking a provider
            providers: List of available providers
            max_matches: Maximum number of matches to return

        Returns:
            List of match results with scores and reasoning
        """
        if not self.ollama_endpoint and not self.client:
            raise Exception("No AI models configured (need either Ollama or Anthropic API key)")

        # Filter providers by service type
        relevant_providers = [
            p for p in providers
            if p.service_type == customer.service_type and p.active and p.accepting_clients
        ]

        if not relevant_providers:
            return []

        # Generate matches for each provider
        matches = []
        for provider in relevant_providers:
            match_result = await self._analyze_match(customer, provider)
            if match_result["match_score"] >= settings.minimum_match_score:
                matches.append(match_result)

        # Sort by match score (highest first)
        matches.sort(key=lambda x: x["match_score"], reverse=True)

        # Return top N matches
        return matches[:max_matches]

    async def _analyze_match(
        self,
        customer: Customer,
        provider: Provider
    ) -> Dict[str, Any]:
        """
        Analyze compatibility between customer and provider.

        SOVEREIGNTY FIRST: Uses Ollama (Llama 3.1) for $0 cost.
        Fallback to Claude API if Ollama fails.

        Returns:
            {
                "provider_id": int,
                "match_score": int (0-100),
                "match_reasoning": str,
                "criteria_scores": {
                    "expertise": int,
                    "communication": int,
                    "values": int,
                    "location": int,
                    "pricing": int
                }
            }
        """

        # Build analysis prompt
        prompt = self._build_analysis_prompt(customer, provider)

        # Try Ollama first (SOVEREIGN - $0 cost)
        if self.ollama_endpoint:
            try:
                response_text = await self._call_ollama(prompt)
                return self._parse_match_response(response_text, provider.id)
            except Exception as e:
                # Ollama failed, fall back to Claude if available
                if not self.client:
                    raise Exception(f"Ollama failed and no Claude fallback: {e}")

        # Fallback to Claude API
        if self.client:
            # Try multiple models in order of capability
            models_to_try = [
                "claude-3-opus-20240229",      # Most capable Claude 3
                "claude-3-5-sonnet-20241022",  # Latest Sonnet 3.5
                "claude-3-5-sonnet-20240620",  # Stable Sonnet 3.5
                "claude-3-sonnet-20240229",    # Fallback Sonnet
                "claude-3-haiku-20240307",     # Fastest, most accessible
            ]

            message = None
            last_error = None

            for model in models_to_try:
                try:
                    message = self.client.messages.create(
                        model=model,
                        max_tokens=2000,
                        messages=[{
                            "role": "user",
                            "content": prompt
                        }]
                    )
                    break  # Success! Exit loop
                except Exception as e:
                    last_error = e
                    continue  # Try next model

            if not message:
                raise Exception(f"No available Claude models. Last error: {last_error}")

            # Parse response
            response_text = message.content[0].text
        else:
            raise Exception("No AI models available")

        return self._parse_match_response(response_text, provider.id)

    async def _call_ollama(self, prompt: str) -> str:
        """Call local Ollama API - SOVEREIGN AI ($0 cost)"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.ollama_endpoint}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 2000,
                        "temperature": 0.7
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")

    def _parse_match_response(self, response_text: str, provider_id: int) -> Dict[str, Any]:
        """Parse AI response into match result"""

        # Extract JSON from response
        try:
            # Claude might return markdown code blocks, extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text

            result = json.loads(json_text)

            # Ensure all required fields
            if "provider_id" not in result:
                result["provider_id"] = provider_id

            return result

        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "provider_id": provider_id,
                "match_score": 50,
                "match_reasoning": f"Analysis completed. Response: {response_text[:200]}...",
                "criteria_scores": {
                    "expertise": 50,
                    "communication": 50,
                    "values": 50,
                    "location": 50,
                    "pricing": 50
                }
            }

    def _build_analysis_prompt(
        self,
        customer: Customer,
        provider: Provider
    ) -> str:
        """Build Claude API prompt for match analysis"""

        return f"""You are an expert matchmaking AI that analyzes compatibility between customers seeking services and service providers.

**CUSTOMER PROFILE:**
Name: {customer.name}
Service Needed: {customer.service_type}
Needs: {customer.needs_description}
Location: {customer.location_city}, {customer.location_state}
Preferences: {json.dumps(customer.preferences, indent=2)}
Values (1-10 scale): {json.dumps(customer.values, indent=2)}

**PROVIDER PROFILE:**
Name: {provider.name}
Company: {provider.company or "Independent"}
Service Type: {provider.service_type}
Specialties: {json.dumps(provider.specialties)}
Experience: {provider.years_experience} years
Description: {provider.description}
Location: {provider.location_city}, {provider.location_state}
Serves Remote: {provider.serves_remote}
Pricing: {provider.pricing_model} - ${provider.price_range_low:,.0f} to ${provider.price_range_high:,.0f}
Performance: {provider.successful_matches}/{provider.total_matches} successful matches, {provider.avg_rating or 0:.1f}/5.0 rating

**TASK:**
Analyze the compatibility between this customer and provider across these dimensions:

1. **Expertise Match** (0-100): How well does the provider's expertise match the customer's needs?
2. **Communication Fit** (0-100): Based on provider description and customer preferences, how well would they communicate?
3. **Values Alignment** (0-100): Do they share similar professional values and approaches?
4. **Location/Logistics** (0-100): How practical is the location fit (consider remote capability)?
5. **Pricing Fit** (0-100): Does the provider's pricing align with what the customer likely expects?

Calculate an **Overall Match Score (0-100)** using weighted average:
- Expertise: 40%
- Communication: 20%
- Values: 20%
- Location: 10%
- Pricing: 10%

Provide clear reasoning for the match score.

**OUTPUT FORMAT (JSON only, no other text):**
```json
{{
    "provider_id": {provider.id},
    "match_score": <0-100>,
    "match_reasoning": "<2-3 sentence explanation of why this is a good/poor match>",
    "criteria_scores": {{
        "expertise": <0-100>,
        "communication": <0-100>,
        "values": <0-100>,
        "location": <0-100>,
        "pricing": <0-100>
    }}
}}
```

Analyze now:"""

    def calculate_commission(
        self,
        deal_value_usd: float,
        commission_percent: float = None
    ) -> float:
        """Calculate commission amount"""
        if commission_percent is None:
            commission_percent = settings.default_commission_percent

        return deal_value_usd * (commission_percent / 100.0)

    async def batch_match(
        self,
        customers: List[Customer],
        providers: List[Provider]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Batch match multiple customers to providers.

        Returns:
            {customer_id: [match_results]}
        """
        results = {}

        for customer in customers:
            matches = await self.find_matches(customer, providers)
            results[customer.id] = matches

        return results

    def get_match_quality_label(self, match_score: int) -> str:
        """Get human-readable quality label for match score"""
        if match_score >= 90:
            return "Excellent Match"
        elif match_score >= 80:
            return "Very Good Match"
        elif match_score >= 70:
            return "Good Match"
        elif match_score >= 60:
            return "Fair Match"
        else:
            return "Poor Match"
