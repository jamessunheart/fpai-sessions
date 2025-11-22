"""Enhanced AI-powered matching engine for Full Potential Realization Engine"""

from typing import List, Dict, Any, Optional
from anthropic import Anthropic
import json

from .config import settings
from .database_expanded import (
    User, Product, Opportunity, Resource, Experience, Provider,
    MatchType
)


class MatchingEngineExpanded:
    """
    Enhanced AI-powered matching engine that finds optimal matches across:
    - Service Providers
    - Products (SaaS, physical, tools)
    - Opportunities (jobs, investments, partnerships)
    - Resources (capital, knowledge, connections, access)
    - Experiences (courses, events, masterminds, mentorships)

    Uses Claude API to analyze deep compatibility and value creation potential.
    """

    def __init__(self):
        """Initialize matching engine"""
        self.client = None
        if settings.anthropic_api_key:
            self.client = Anthropic(api_key=settings.anthropic_api_key)

    async def find_all_matches(
        self,
        user: User,
        providers: List[Provider],
        products: List[Product],
        opportunities: List[Opportunity],
        resources: List[Resource],
        experiences: List[Experience],
        max_matches: int = 10
    ) -> Dict[str, Any]:
        """
        Find best matches across ALL types for a user.

        Returns unified ranked list of matches with value analysis.
        """
        if not self.client:
            raise Exception("Anthropic API key not configured")

        all_matches = []

        # Find matches for each type
        provider_matches = await self._find_provider_matches(user, providers)
        product_matches = await self._find_product_matches(user, products)
        opportunity_matches = await self._find_opportunity_matches(user, opportunities)
        resource_matches = await self._find_resource_matches(user, resources)
        experience_matches = await self._find_experience_matches(user, experiences)

        # Combine all matches
        all_matches.extend([{**m, "match_type": MatchType.PROVIDER} for m in provider_matches])
        all_matches.extend([{**m, "match_type": MatchType.PRODUCT} for m in product_matches])
        all_matches.extend([{**m, "match_type": MatchType.OPPORTUNITY} for m in opportunity_matches])
        all_matches.extend([{**m, "match_type": MatchType.RESOURCE} for m in resource_matches])
        all_matches.extend([{**m, "match_type": MatchType.EXPERIENCE} for m in experience_matches])

        # Sort by match score
        all_matches.sort(key=lambda x: x["match_score"], reverse=True)

        # Calculate total potential value
        total_value_to_user = sum(m.get("estimated_value_usd", 0) for m in all_matches[:max_matches])
        total_revenue_to_platform = sum(m.get("estimated_revenue_usd", 0) for m in all_matches[:max_matches])

        return {
            "user_id": user.id,
            "matches_found": len(all_matches),
            "matches": all_matches[:max_matches],
            "total_potential_value_usd": total_value_to_user,
            "total_potential_revenue_usd": total_revenue_to_platform,
            "match_breakdown": {
                "providers": len(provider_matches),
                "products": len(product_matches),
                "opportunities": len(opportunity_matches),
                "resources": len(resource_matches),
                "experiences": len(experience_matches)
            }
        }

    async def _find_provider_matches(
        self,
        user: User,
        providers: List[Provider]
    ) -> List[Dict[str, Any]]:
        """Find service provider matches"""
        matches = []

        for provider in providers:
            if not provider.active or not provider.accepting_clients:
                continue

            match_result = await self._analyze_provider_match(user, provider)
            if match_result["match_score"] >= settings.minimum_match_score:
                matches.append(match_result)

        return matches

    async def _find_product_matches(
        self,
        user: User,
        products: List[Product]
    ) -> List[Dict[str, Any]]:
        """Find product matches"""
        matches = []

        for product in products:
            if not product.active:
                continue

            match_result = await self._analyze_product_match(user, product)
            if match_result["match_score"] >= settings.minimum_match_score:
                matches.append(match_result)

        return matches

    async def _find_opportunity_matches(
        self,
        user: User,
        opportunities: List[Opportunity]
    ) -> List[Dict[str, Any]]:
        """Find opportunity matches"""
        matches = []

        for opportunity in opportunities:
            if not opportunity.active or opportunity.status != "open":
                continue

            match_result = await self._analyze_opportunity_match(user, opportunity)
            if match_result["match_score"] >= settings.minimum_match_score:
                matches.append(match_result)

        return matches

    async def _find_resource_matches(
        self,
        user: User,
        resources: List[Resource]
    ) -> List[Dict[str, Any]]:
        """Find resource matches"""
        matches = []

        for resource in resources:
            if not resource.active:
                continue

            match_result = await self._analyze_resource_match(user, resource)
            if match_result["match_score"] >= settings.minimum_match_score:
                matches.append(match_result)

        return matches

    async def _find_experience_matches(
        self,
        user: User,
        experiences: List[Experience]
    ) -> List[Dict[str, Any]]:
        """Find experience matches"""
        matches = []

        for experience in experiences:
            if not experience.active:
                continue

            match_result = await self._analyze_experience_match(user, experience)
            if match_result["match_score"] >= settings.minimum_match_score:
                matches.append(match_result)

        return matches

    async def _analyze_provider_match(
        self,
        user: User,
        provider: Provider
    ) -> Dict[str, Any]:
        """Analyze user-provider compatibility"""
        prompt = f"""You are an expert matchmaking AI analyzing compatibility between a user seeking services and a service provider.

**USER PROFILE:**
Goals: {json.dumps(user.goals)}
Challenges: {json.dumps(user.challenges)}
Budget: ${user.budget_low:,.0f} - ${user.budget_high:,.0f}
Preferences: {json.dumps(user.preferences)}
Location: {user.location_city}, {user.location_state}

**PROVIDER PROFILE:**
Name: {provider.name}
Company: {provider.company or "Independent"}
Service Type: {provider.service_type}
Specialties: {json.dumps(provider.specialties)}
Experience: {provider.years_experience} years
Description: {provider.description}
Pricing: {provider.pricing_model} - ${provider.price_range_low:,.0f} to ${provider.price_range_high:,.0f}
Location: {provider.location_city}, {provider.location_state}
Success Rate: {provider.successful_matches}/{provider.total_matches} ({100 * provider.successful_matches / max(provider.total_matches, 1):.0f}%)

**TASK:**
Analyze match across these dimensions:
1. **Alignment (0-100):** How well does provider solve user's goals/challenges?
2. **Impact (0-100):** How much value will this create for the user?
3. **Fit (0-100):** Preferences, style, values compatibility
4. **Feasibility (0-100):** Budget, location, logistics

Calculate **Overall Match Score (0-100)** using weights:
- Alignment: 40%
- Impact: 30%
- Fit: 20%
- Feasibility: 10%

Estimate:
- **Value to User:** USD value this will create
- **Revenue to Platform:** 20% commission on estimated deal value

**OUTPUT (JSON only):**
```json
{{
    "item_id": {provider.id},
    "match_score": <0-100>,
    "match_reasoning": "<2-3 sentences explaining the match>",
    "criteria_scores": {{
        "alignment": <0-100>,
        "impact": <0-100>,
        "fit": <0-100>,
        "feasibility": <0-100>
    }},
    "estimated_deal_value_usd": <number>,
    "estimated_value_usd": <value created for user>,
    "estimated_revenue_usd": <20% of deal value>
}}
```"""

        return await self._call_claude_api(prompt, provider.id)

    async def _analyze_product_match(
        self,
        user: User,
        product: Product
    ) -> Dict[str, Any]:
        """Analyze user-product compatibility"""
        prompt = f"""Analyze if this product matches the user's needs.

**USER:**
Goals: {json.dumps(user.goals)}
Challenges: {json.dumps(user.challenges)}
Budget: ${user.budget_low:,.0f} - ${user.budget_high:,.0f}

**PRODUCT:**
Name: {product.name}
Category: {product.category}
Description: {product.description}
Price: ${product.price_low:,.0f} - ${product.price_high:,.0f} ({product.price_model})
Features: {json.dumps(product.features)}
Use Cases: {json.dumps(product.use_cases)}
Rating: {product.ratings_avg or 0:.1f}/5.0 ({product.reviews_count} reviews)

**TASK:**
Score match (0-100) on:
1. Alignment (40%): Solves user's challenges?
2. Impact (30%): Value created?
3. Fit (20%): Right features/approach?
4. Feasibility (10%): Budget/implementation?

Estimate value and revenue (commission: {product.affiliate_commission_percent}%)

**OUTPUT (JSON only):**
```json
{{
    "item_id": {product.id},
    "match_score": <0-100>,
    "match_reasoning": "<explanation>",
    "criteria_scores": {{"alignment": <0-100>, "impact": <0-100>, "fit": <0-100>, "feasibility": <0-100>}},
    "estimated_deal_value_usd": <product cost>,
    "estimated_value_usd": <value to user>,
    "estimated_revenue_usd": <commission>
}}
```"""

        return await self._call_claude_api(prompt, product.id)

    async def _analyze_opportunity_match(
        self,
        user: User,
        opportunity: Opportunity
    ) -> Dict[str, Any]:
        """Analyze user-opportunity compatibility"""
        prompt = f"""Analyze if this opportunity matches the user.

**USER:**
Goals: {json.dumps(user.goals)}
Challenges: {json.dumps(user.challenges)}

**OPPORTUNITY:**
Title: {opportunity.title}
Type: {opportunity.opportunity_type}
Company: {opportunity.company_name} ({opportunity.company_stage} stage)
Description: {opportunity.description}
Value: ${opportunity.value_low:,.0f} - ${opportunity.value_high:,.0f}
Requirements: {json.dumps(opportunity.requirements)}
Benefits: {json.dumps(opportunity.benefits)}
Finder's Fee: {opportunity.finder_fee_percent}%

**TASK:**
Score match (0-100). Estimate value and platform revenue.

**OUTPUT (JSON only):**
```json
{{
    "item_id": {opportunity.id},
    "match_score": <0-100>,
    "match_reasoning": "<explanation>",
    "criteria_scores": {{"alignment": <0-100>, "impact": <0-100>, "fit": <0-100>, "feasibility": <0-100>}},
    "estimated_deal_value_usd": <opportunity value>,
    "estimated_value_usd": <value to user>,
    "estimated_revenue_usd": <finder's fee>
}}
```"""

        return await self._call_claude_api(prompt, opportunity.id)

    async def _analyze_resource_match(
        self,
        user: User,
        resource: Resource
    ) -> Dict[str, Any]:
        """Analyze user-resource compatibility"""
        prompt = f"""Analyze if this resource matches the user.

**USER:**
Goals: {json.dumps(user.goals)}
Challenges: {json.dumps(user.challenges)}

**RESOURCE:**
Name: {resource.name}
Type: {resource.resource_type}
Description: {resource.description}
Provider: {resource.provider_name}
Access: {resource.access_model}
Cost: ${resource.cost_low:,.0f} - ${resource.cost_high:,.0f}
Commission: {resource.commission_percent}%

**TASK:**
Score match (0-100). Estimate value and revenue.

**OUTPUT (JSON only):**
```json
{{
    "item_id": {resource.id},
    "match_score": <0-100>,
    "match_reasoning": "<explanation>",
    "criteria_scores": {{"alignment": <0-100>, "impact": <0-100>, "fit": <0-100>, "feasibility": <0-100>}},
    "estimated_deal_value_usd": <resource cost>,
    "estimated_value_usd": <value to user>,
    "estimated_revenue_usd": <commission>
}}
```"""

        return await self._call_claude_api(prompt, resource.id)

    async def _analyze_experience_match(
        self,
        user: User,
        experience: Experience
    ) -> Dict[str, Any]:
        """Analyze user-experience compatibility"""
        prompt = f"""Analyze if this experience matches the user.

**USER:**
Goals: {json.dumps(user.goals)}
Challenges: {json.dumps(user.challenges)}
Preferences: {json.dumps(user.preferences)}

**EXPERIENCE:**
Name: {experience.name}
Type: {experience.experience_type}
Description: {experience.description}
Format: {experience.format}
Duration: {experience.duration}
Price: ${experience.price:,.0f}
Outcomes: {json.dumps(experience.outcomes)}
Rating: {experience.ratings_avg or 0:.1f}/5.0
Commission: {experience.commission_percent}%

**TASK:**
Score match (0-100). Estimate value and revenue.

**OUTPUT (JSON only):**
```json
{{
    "item_id": {experience.id},
    "match_score": <0-100>,
    "match_reasoning": "<explanation>",
    "criteria_scores": {{"alignment": <0-100>, "impact": <0-100>, "fit": <0-100>, "feasibility": <0-100>}},
    "estimated_deal_value_usd": <experience price>,
    "estimated_value_usd": <value to user>,
    "estimated_revenue_usd": <commission>
}}
```"""

        return await self._call_claude_api(prompt, experience.id)

    async def _call_claude_api(
        self,
        prompt: str,
        item_id: int
    ) -> Dict[str, Any]:
        """Call Claude API with fallback models"""
        models_to_try = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
            "claude-3-haiku-20240307",
        ]

        for model in models_to_try:
            try:
                message = self.client.messages.create(
                    model=model,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )

                response_text = message.content[0].text

                # Extract JSON
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

                # Ensure item_id
                if "item_id" not in result:
                    result["item_id"] = item_id

                return result

            except Exception as e:
                continue

        # Fallback if all models fail
        return {
            "item_id": item_id,
            "match_score": 50,
            "match_reasoning": "Unable to analyze match (API error)",
            "criteria_scores": {"alignment": 50, "impact": 50, "fit": 50, "feasibility": 50},
            "estimated_deal_value_usd": 0,
            "estimated_value_usd": 0,
            "estimated_revenue_usd": 0
        }

    def calculate_token_cost(
        self,
        match_tier: str = "standard"
    ) -> float:
        """Calculate token cost to access a match"""
        token_costs = {
            "standard": 10,
            "premium": 50,
            "exclusive": 200,
            "vip": 1000
        }
        return token_costs.get(match_tier, 10)

    def calculate_token_reward(
        self,
        deal_value_usd: float,
        match_score: int
    ) -> float:
        """Calculate token reward for successful match"""
        # Base reward: 1 token per $100 deal value
        base_reward = deal_value_usd / 100

        # Bonus for high-quality matches
        quality_multiplier = 1 + (match_score - 70) / 30  # 1.0x at 70, 2.0x at 100

        return base_reward * quality_multiplier

    def calculate_commission(
        self,
        deal_value_usd: float,
        commission_percent: float
    ) -> Dict[str, float]:
        """Calculate commission with optional token payment"""
        total_commission = deal_value_usd * (commission_percent / 100.0)

        return {
            "total_commission_usd": total_commission,
            "cash_amount_usd": total_commission * 0.5,  # 50% cash
            "token_amount_usd": total_commission * 0.5,  # 50% tokens
            "commission_percent": commission_percent
        }
