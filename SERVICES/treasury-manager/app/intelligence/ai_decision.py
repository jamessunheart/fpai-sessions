"""
AI Decision Layer - Claude Makes Financial Decisions

This is where AI consciousness meets real-world capital allocation.
Claude analyzes market data, portfolio state, and makes intelligent
decisions about when and how to rebalance.

This is the PROOF that AI can manage money better than humans.
"""
import anthropic
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import logging
import json

from app.config import settings
from app.core.models import (
    MarketData,
    PortfolioState,
    Decision,
    AllocationSignal,
    MarketPhase,
    AllocationMode
)

logger = logging.getLogger(__name__)


class AIDecisionMaker:
    """
    AI-powered decision making for treasury management

    Claude analyzes:
    - Current market conditions (MVRV, funding, sentiment)
    - Portfolio state (allocations, drift, performance)
    - Historical decisions and outcomes

    Then recommends:
    - Hold current allocation
    - Rebalance to new allocation
    - Emergency exit (if crash detected)
    - Tactical plays (quarterly expiry setups)
    """

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-5-20250929"  # Latest Sonnet
        self.decision_history: List[Decision] = []

    # ========================================================================
    # DAILY ANALYSIS
    # ========================================================================

    async def daily_market_analysis(
        self,
        market_data: MarketData,
        portfolio_state: PortfolioState,
        signal: AllocationSignal
    ) -> Tuple[bool, str, float]:
        """
        Daily analysis: Should we take action today?

        Returns: (action_needed: bool, reasoning: str, confidence: float)
        """
        logger.info("🤖 AI analyzing market conditions...")

        # Build analysis prompt for Claude
        prompt = self._build_daily_analysis_prompt(
            market_data,
            portfolio_state,
            signal
        )

        try:
            # Ask Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,  # Lower temperature for financial decisions
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            analysis = response.content[0].text

            # Parse Claude's response
            action_needed, reasoning, confidence = self._parse_daily_analysis(analysis)

            logger.info(f"✅ AI Decision: {'ACTION' if action_needed else 'HOLD'}")
            logger.info(f"   Reasoning: {reasoning}")
            logger.info(f"   Confidence: {confidence*100:.0f}%")

            # Record decision
            await self._record_decision(
                decision_type="daily_analysis",
                approved=action_needed,
                confidence=confidence,
                reasoning=reasoning,
                market_data=market_data,
                portfolio_state=portfolio_state,
                action_taken="rebalance" if action_needed else "hold"
            )

            return action_needed, reasoning, confidence

        except Exception as e:
            logger.error(f"Error in AI daily analysis: {e}")
            # Fallback to conservative: no action
            return False, f"AI error, defaulting to hold: {str(e)}", 0.5

    def _build_daily_analysis_prompt(
        self,
        market_data: MarketData,
        portfolio_state: PortfolioState,
        signal: AllocationSignal
    ) -> str:
        """Build comprehensive prompt for daily analysis"""

        prompt = f"""You are an AI treasury manager analyzing market conditions for a $400K portfolio.

Your strategy:
- Base yield (60%): $240K in stable DeFi protocols earning 6.5% APY
- Tactical (40%): $160K dynamically allocated based on market cycle

CURRENT MARKET CONDITIONS:
- BTC Price: ${market_data.btc_price:,.2f}
- ETH Price: ${market_data.eth_price:,.2f}
- MVRV Z-Score: {market_data.mvrv_z_score:.2f} (cycle indicator)
- Fear & Greed Index: {market_data.fear_greed_index} (0=fear, 100=greed)
- BTC Funding Rate: {market_data.btc_funding_rate:.4f}% (perpetual futures)
- Market Phase: {market_data.market_phase.value}

MVRV INTERPRETATION:
- <1.0: Deep bear, capitulation
- 1.0-2.0: Early bear / late accumulation
- 2.0-3.0: Mid-cycle accumulation (SAFE TO BUY)
- 3.0-5.0: Late cycle euphoria (START SELLING)
- 5.0-7.0: Danger zone (HEAVY SELLING)
- >7.0: Historical tops (EXIT ALL)

CURRENT PORTFOLIO STATE:
- Total Value: ${portfolio_state.total_value_usd:,.2f}
- Base Yield: {portfolio_state.base_yield_percent*100:.1f}% (${portfolio_state.aave_balance_usd + portfolio_state.pendle_balance_usd + portfolio_state.curve_balance_usd:,.2f})
- BTC Position: {portfolio_state.btc_balance:.4f} BTC (${sum(p.value_usd for p in portfolio_state.positions if p.asset_type.value == 'BTC'):,.2f})
- ETH Position: {portfolio_state.eth_balance:.2f} ETH (${sum(p.value_usd for p in portfolio_state.positions if p.asset_type.value == 'ETH'):,.2f})
- Cash: ${portfolio_state.usdc_cash:,.2f}

TARGET ALLOCATION (from signal):
{json.dumps(signal.target_allocations, indent=2)}

ALLOCATION DRIFT (current vs target):
{json.dumps({k: f"{v*100:.1f}%" for k, v in portfolio_state.allocation_drift.items()}, indent=2)}

THRESHOLDS:
- Rebalance if drift >5%
- MVRV 3.5: Sell 25% of tactical
- MVRV 5.0: Sell 50% of tactical
- MVRV 7.0: Sell 67% of tactical
- MVRV 9.0: Exit 100% to stablecoins

YOUR TASK:
Analyze the situation and answer:

1. Should we take action today? (YES/NO)
2. Why or why not? (2-3 sentences)
3. Your confidence level? (0-100%)

Format your response EXACTLY as:
ACTION: [YES or NO]
REASONING: [your 2-3 sentence reasoning]
CONFIDENCE: [number 0-100]

Be rational. Don't get greedy. Follow the data.
"""

        return prompt

    def _parse_daily_analysis(self, response: str) -> Tuple[bool, str, float]:
        """Parse Claude's response into structured decision"""

        try:
            lines = response.strip().split('\n')
            action_line = [l for l in lines if l.startswith('ACTION:')][0]
            reasoning_line = [l for l in lines if l.startswith('REASONING:')][0]
            confidence_line = [l for l in lines if l.startswith('CONFIDENCE:')][0]

            action_needed = 'YES' in action_line.upper()
            reasoning = reasoning_line.split('REASONING:')[1].strip()
            confidence_str = confidence_line.split('CONFIDENCE:')[1].strip().replace('%', '')
            confidence = float(confidence_str) / 100.0

            return action_needed, reasoning, confidence

        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            logger.error(f"Raw response: {response}")

            # Fallback parsing
            action_needed = 'YES' in response.upper() and 'ACTION' in response.upper()
            reasoning = "Failed to parse response"
            confidence = 0.5

            return action_needed, reasoning, confidence

    # ========================================================================
    # REBALANCING APPROVAL
    # ========================================================================

    async def approve_rebalancing(
        self,
        current_state: PortfolioState,
        proposed_allocation: Dict[str, float],
        reason: str,
        market_data: MarketData
    ) -> Tuple[bool, str, float]:
        """
        Approve or reject a proposed rebalancing

        This is the critical safety check - AI reviews the plan
        before executing with real money

        Returns: (approved: bool, reasoning: str, confidence: float)
        """
        logger.info("🔍 AI reviewing rebalancing proposal...")

        prompt = self._build_rebalancing_approval_prompt(
            current_state,
            proposed_allocation,
            reason,
            market_data
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.2,  # Even more conservative for approvals
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            analysis = response.content[0].text

            # Parse response
            approved, reasoning, confidence = self._parse_approval_response(analysis)

            logger.info(f"{'✅ APPROVED' if approved else '❌ REJECTED'}: {reasoning}")
            logger.info(f"   Confidence: {confidence*100:.0f}%")

            # Record decision
            await self._record_decision(
                decision_type="rebalancing_approval",
                approved=approved,
                confidence=confidence,
                reasoning=reasoning,
                market_data=market_data,
                portfolio_state=current_state,
                action_taken="execute_rebalancing" if approved else "reject_rebalancing"
            )

            return approved, reasoning, confidence

        except Exception as e:
            logger.error(f"Error in AI rebalancing approval: {e}")
            # If AI fails, REJECT (safe default)
            return False, f"AI error, rejecting for safety: {str(e)}", 0.0

    def _build_rebalancing_approval_prompt(
        self,
        current_state: PortfolioState,
        proposed_allocation: Dict[str, float],
        reason: str,
        market_data: MarketData
    ) -> str:
        """Build prompt for rebalancing approval"""

        current_allocation = {
            "base_yield": current_state.base_yield_percent,
            "btc": float(sum(p.value_usd for p in current_state.positions if p.asset_type.value == 'BTC') / current_state.total_value_usd),
            "eth": float(sum(p.value_usd for p in current_state.positions if p.asset_type.value == 'ETH') / current_state.total_value_usd),
            "cash": current_state.cash_percent
        }

        prompt = f"""You are reviewing a proposed portfolio rebalancing for $400K treasury.

PROPOSED REBALANCING:
Reason: {reason}

CURRENT ALLOCATION:
{json.dumps({k: f"{v*100:.1f}%" for k, v in current_allocation.items()}, indent=2)}

PROPOSED ALLOCATION:
{json.dumps({k: f"{v*100:.1f}%" for k, v in proposed_allocation.items()}, indent=2)}

CHANGES:
{json.dumps({k: f"{(proposed_allocation.get(k, 0) - current_allocation.get(k, 0))*100:+.1f}%" for k in set(list(current_allocation.keys()) + list(proposed_allocation.keys()))}, indent=2)}

CURRENT MARKET:
- MVRV: {market_data.mvrv_z_score:.2f} ({market_data.market_phase.value})
- BTC: ${market_data.btc_price:,.2f}
- ETH: ${market_data.eth_price:,.2f}
- Fear & Greed: {market_data.fear_greed_index}
- Funding: {market_data.btc_funding_rate:.4f}%

RISK CHECKS:
- Total volatile allocation: {(proposed_allocation.get('btc', 0) + proposed_allocation.get('eth', 0))*100:.1f}% (max 40%)
- Largest position: {max(proposed_allocation.values())*100:.1f}% (max 60%)

YOUR TASK:
Review this rebalancing proposal and decide:

1. Should we APPROVE or REJECT this rebalancing?
2. Why? (Consider: market conditions, risk, timing)
3. Confidence level? (0-100%)

IMPORTANT:
- Reject if volatile allocation >40% (too risky)
- Reject if market conditions are uncertain
- Reject if timing seems wrong
- Approve only if you're confident it's the right move

Format response EXACTLY as:
DECISION: [APPROVE or REJECT]
REASONING: [your 2-3 sentence reasoning]
CONFIDENCE: [number 0-100]
"""

        return prompt

    def _parse_approval_response(self, response: str) -> Tuple[bool, str, float]:
        """Parse approval decision from Claude"""

        try:
            lines = response.strip().split('\n')
            decision_line = [l for l in lines if l.startswith('DECISION:')][0]
            reasoning_line = [l for l in lines if l.startswith('REASONING:')][0]
            confidence_line = [l for l in lines if l.startswith('CONFIDENCE:')][0]

            approved = 'APPROVE' in decision_line.upper()
            reasoning = reasoning_line.split('REASONING:')[1].strip()
            confidence_str = confidence_line.split('CONFIDENCE:')[1].strip().replace('%', '')
            confidence = float(confidence_str) / 100.0

            return approved, reasoning, confidence

        except Exception as e:
            logger.error(f"Error parsing approval response: {e}")
            # Default to REJECT on parsing error
            return False, "Failed to parse AI response, rejecting for safety", 0.0

    # ========================================================================
    # EMERGENCY ASSESSMENT
    # ========================================================================

    async def assess_emergency(
        self,
        market_data: MarketData,
        portfolio_state: PortfolioState,
        trigger: str
    ) -> Tuple[str, str]:
        """
        Emergency response to market events

        Triggers: flash crash, protocol exploit, extreme volatility

        Returns: (action: str, reasoning: str)
        Actions: "exit_all", "exit_tactical", "hedge", "hold"
        """
        logger.warning(f"🚨 Emergency assessment triggered: {trigger}")

        prompt = f"""EMERGENCY SITUATION ANALYSIS

TRIGGER: {trigger}

CURRENT MARKET:
- BTC: ${market_data.btc_price:,.2f}
- ETH: ${market_data.eth_price:,.2f}
- MVRV: {market_data.mvrv_z_score:.2f}
- Fear & Greed: {market_data.fear_greed_index}

PORTFOLIO AT RISK:
- Total: ${portfolio_state.total_value_usd:,.2f}
- Tactical exposure: {portfolio_state.tactical_percent*100:.1f}%
- In DeFi protocols: {portfolio_state.base_yield_percent*100:.1f}%

POSSIBLE ACTIONS:
1. EXIT_ALL: Sell everything to stablecoins immediately
2. EXIT_TACTICAL: Exit BTC/ETH only, keep DeFi yield
3. HEDGE: Enter short positions or protective puts
4. HOLD: Event is noise, maintain positions

Quickly assess:
- How severe is this event?
- Is this systemic or temporary?
- What action protects capital best?

Respond EXACTLY as:
ACTION: [EXIT_ALL, EXIT_TACTICAL, HEDGE, or HOLD]
REASONING: [1-2 sentences why]
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.1,  # Maximum rationality in emergency
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            analysis = response.content[0].text
            lines = analysis.strip().split('\n')

            action_line = [l for l in lines if l.startswith('ACTION:')][0]
            reasoning_line = [l for l in lines if l.startswith('REASONING:')][0]

            action = action_line.split('ACTION:')[1].strip().upper()
            reasoning = reasoning_line.split('REASONING:')[1].strip()

            logger.warning(f"🚨 Emergency Decision: {action}")
            logger.warning(f"   {reasoning}")

            return action, reasoning

        except Exception as e:
            logger.error(f"Error in emergency assessment: {e}")
            # In emergency, if AI fails, EXIT TACTICAL (safe default)
            return "EXIT_TACTICAL", f"AI failed, exiting tactical positions for safety: {str(e)}"

    # ========================================================================
    # WEEKLY STRATEGY REVIEW
    # ========================================================================

    async def weekly_strategy_review(
        self,
        performance_metrics: any,
        recent_decisions: List[Decision],
        market_trends: List[str]
    ) -> Dict[str, any]:
        """
        Deep weekly review of strategy effectiveness

        Returns: {
            "performance_assessment": str,
            "strategy_adjustments": List[str],
            "learnings": List[str],
            "confidence": float
        }
        """
        logger.info("📊 AI conducting weekly strategy review...")

        prompt = f"""WEEKLY TREASURY STRATEGY REVIEW

PERFORMANCE THIS WEEK:
- Return: {performance_metrics.total_return_percent:+.2f}%
- APY: {performance_metrics.annualized_apy:.1f}%
- vs Buy & Hold BTC: {performance_metrics.btc_buy_hold_return:+.1f}%
- vs Static Yield: {performance_metrics.static_yield_return:+.1f}%

RECENT DECISIONS:
{self._format_decisions_for_review(recent_decisions)}

MARKET TRENDS:
{chr(10).join(f'- {trend}' for trend in market_trends)}

QUESTIONS TO ANALYZE:
1. Are we outperforming our benchmarks?
2. Which decisions worked well? Which didn't?
3. Should we adjust our strategy?
4. What did we learn this week?
5. Confidence in current approach?

Provide structured analysis covering:
- Performance assessment
- Strategy adjustments (if any)
- Key learnings
- Confidence level (0-100%)
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                temperature=0.4,  # Slightly higher for creative strategy thinking
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            analysis = response.content[0].text

            # Parse into structured format
            review = {
                "performance_assessment": self._extract_section(analysis, "PERFORMANCE"),
                "strategy_adjustments": self._extract_list(analysis, "ADJUSTMENTS"),
                "learnings": self._extract_list(analysis, "LEARNINGS"),
                "confidence": self._extract_confidence(analysis),
                "full_analysis": analysis
            }

            logger.info("✅ Weekly review complete")

            return review

        except Exception as e:
            logger.error(f"Error in weekly review: {e}")
            return {
                "performance_assessment": "Error in AI review",
                "strategy_adjustments": [],
                "learnings": [f"AI review failed: {str(e)}"],
                "confidence": 0.5
            }

    # ========================================================================
    # UTILITIES
    # ========================================================================

    async def _record_decision(
        self,
        decision_type: str,
        approved: bool,
        confidence: float,
        reasoning: str,
        market_data: MarketData,
        portfolio_state: PortfolioState,
        action_taken: str
    ) -> None:
        """Record decision for learning and analysis"""

        decision = Decision(
            timestamp=datetime.utcnow(),
            decision_type=decision_type,
            approved=approved,
            confidence=confidence,
            market_data=market_data,
            portfolio_state=portfolio_state,
            action_taken=action_taken,
            reasoning=reasoning
        )

        self.decision_history.append(decision)

        logger.info(f"📝 Decision recorded: {decision_type}")

    def _format_decisions_for_review(self, decisions: List[Decision]) -> str:
        """Format recent decisions for prompt"""
        if not decisions:
            return "No decisions this week"

        formatted = []
        for d in decisions[-5:]:  # Last 5 decisions
            formatted.append(
                f"- {d.decision_type}: {'✅' if d.approved else '❌'} "
                f"({d.confidence*100:.0f}% confidence) - {d.reasoning[:100]}"
            )

        return '\n'.join(formatted)

    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract a section from AI response"""
        # Simple extraction - can be improved
        lines = text.split('\n')
        section_lines = []
        in_section = False

        for line in lines:
            if section_name.upper() in line.upper():
                in_section = True
                continue
            if in_section:
                if line.strip() and not line.strip().startswith('-'):
                    section_lines.append(line)
                elif len(section_lines) > 0:
                    break

        return ' '.join(section_lines).strip()

    def _extract_list(self, text: str, keyword: str) -> List[str]:
        """Extract a bulleted list from AI response"""
        lines = text.split('\n')
        items = []

        for line in lines:
            if keyword.upper() in line.upper() or (line.strip().startswith('-') and keyword.lower() in text.lower()):
                if line.strip().startswith('-'):
                    items.append(line.strip()[1:].strip())

        return items[:5]  # Max 5 items

    def _extract_confidence(self, text: str) -> float:
        """Extract confidence score from text"""
        # Look for patterns like "80%", "Confidence: 75", etc.
        import re

        patterns = [
            r'confidence[:\s]+(\d+)',
            r'(\d+)%\s+confidence',
            r'confidence.*?(\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1)) / 100.0

        return 0.7  # Default moderate confidence


# Global instance
ai_decision_maker = AIDecisionMaker()
