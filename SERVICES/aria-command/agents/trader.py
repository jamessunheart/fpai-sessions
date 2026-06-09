"""
Trader Agent - Specialized agent for trading decisions.

Uses Gemini for market analysis and trading insights.
"""

import logging
import time
from datetime import datetime

from .base import Agent, AgentSpecialty, Task, AgentOpinion, ExecutionResult

logger = logging.getLogger("aria.agents.trader")


class TraderAgent(Agent):
    """
    Trader Agent - Analyzes and executes trading decisions.
    
    Strengths:
    - Market analysis
    - Risk assessment
    - Signal evaluation
    - Position management
    """
    
    def __init__(self):
        super().__init__(
            name="trader",
            specialty=AgentSpecialty.TRADE,
            model="gemini-1.5-flash",  # Fast market analysis
            description="Analyzes markets and evaluates trading decisions"
        )
        
        self.system_prompt = """You are the Trader Agent in the ARIA Sovereign system.
Your role is to analyze markets and evaluate trading decisions.

Core responsibilities:
1. Analyze market conditions
2. Evaluate trading signals
3. Assess position risks
4. Recommend entry/exit points

Key principles:
- Capital preservation first
- Risk/reward analysis
- Consider correlations
- Account for volatility

Trading checklist:
- Market regime (trending/ranging)
- Key levels (support/resistance)
- Volume analysis
- Sentiment indicators
- Correlation risks

Output your analysis as JSON:
{
    "trade_safe": true/false,
    "market_regime": "trending_up/trending_down/ranging/volatile",
    "confidence": 0.0-1.0,
    "risk_level": "low/medium/high/extreme",
    "key_levels": {"support": 0, "resistance": 0},
    "recommendation": "enter_long/enter_short/hold/exit/wait",
    "position_size_suggestion": "full/half/quarter/none",
    "concerns": ["concern1"],
    "reasoning": "detailed analysis"
}"""
    
    async def evaluate(self, task: Task) -> AgentOpinion:
        """Evaluate a trading decision."""
        start_time = time.time()
        
        try:
            # Get market context
            market_data = await self._get_market_context()
            
            prompt = f"""Analyze this trading decision:

Task: {task.description}

Market Context:
{market_data}

Task Context:
{self._format_context(task.context)}

Provide your analysis as JSON."""

            response = await self._call_llm(prompt, self.system_prompt)
            
            analysis = self._parse_analysis(response)
            
            # Calculate confidence
            base_confidence = analysis.get("confidence", 0.5)
            
            # Adjust for risk
            if analysis.get("risk_level") == "extreme":
                base_confidence *= 0.2
            elif analysis.get("risk_level") == "high":
                base_confidence *= 0.5
            
            # Determine recommendation
            if analysis.get("trade_safe", False) and base_confidence >= 0.7:
                recommendation = "approve"
            elif analysis.get("recommendation") == "wait":
                recommendation = "defer"
            else:
                recommendation = "modify"
            
            concerns = analysis.get("concerns", [])
            if analysis.get("risk_level") in ["high", "extreme"]:
                concerns.insert(0, f"Risk level: {analysis.get('risk_level')}")
            
            opinion = AgentOpinion(
                agent_name=self.name,
                specialty=self.specialty,
                confidence=min(base_confidence, 1.0),
                recommendation=recommendation,
                reasoning=analysis.get("reasoning", "Market analysis complete"),
                concerns=concerns,
                suggestions=[
                    f"Recommended action: {analysis.get('recommendation', 'hold')}",
                    f"Position size: {analysis.get('position_size_suggestion', 'quarter')}"
                ],
                evaluation_time_ms=int((time.time() - start_time) * 1000)
            )
            
            self.total_evaluations += 1
            self.last_action = datetime.now()
            
            return opinion
            
        except Exception as e:
            logger.error(f"Trader evaluation failed: {e}")
            return AgentOpinion(
                agent_name=self.name,
                specialty=self.specialty,
                confidence=0.2,
                recommendation="reject",
                reasoning=f"Analysis failed: {str(e)} - defaulting to no trade",
                concerns=["Could not complete market analysis"],
                evaluation_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def execute(self, task: Task) -> ExecutionResult:
        """Execute a trading action."""
        start_time = datetime.now()
        
        try:
            self._current_tasks += 1
            
            # Trading execution would connect to Signal Shark or Hyperliquid
            # For now, this is a placeholder
            
            output = f"""Trading execution requested:
Task: {task.description}
Context: {task.context}

NOTE: Actual trade execution requires explicit approval and connection to trading infrastructure.
Use /trade commands in Telegram for live trading."""
            
            self.total_executions += 1
            self.last_action = datetime.now()
            
            return ExecutionResult(
                task_id=task.id,
                success=True,
                output=output,
                started_at=start_time,
                completed_at=datetime.now(),
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
            
        except Exception as e:
            return ExecutionResult(
                task_id=task.id,
                success=False,
                output="",
                error=str(e),
                started_at=start_time
            )
        finally:
            self._current_tasks -= 1
    
    async def _get_market_context(self) -> str:
        """Get current market context from trading services."""
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try to get market data from WhaleTrack
                try:
                    response = await client.get("http://198.54.123.234:8601/api/market/summary")
                    if response.status_code == 200:
                        data = response.json()
                        return f"""
BTC: ${data.get('btc_price', 'N/A')} ({data.get('btc_24h_change', 'N/A')})
ETH: ${data.get('eth_price', 'N/A')} ({data.get('eth_24h_change', 'N/A')})
SOL: ${data.get('sol_price', 'N/A')} ({data.get('sol_24h_change', 'N/A')})
Market Sentiment: {data.get('sentiment', 'neutral')}
"""
                except:
                    pass
                
                return "Market data unavailable - proceed with caution"
                
        except Exception as e:
            return f"Could not fetch market data: {e}"
    
    def _format_context(self, context: dict) -> str:
        """Format trading context."""
        parts = []
        if "asset" in context:
            parts.append(f"Asset: {context['asset']}")
        if "direction" in context:
            parts.append(f"Direction: {context['direction']}")
        if "entry_price" in context:
            parts.append(f"Entry price: {context['entry_price']}")
        if "stop_loss" in context:
            parts.append(f"Stop loss: {context['stop_loss']}")
        if "take_profit" in context:
            parts.append(f"Take profit: {context['take_profit']}")
        if "leverage" in context:
            parts.append(f"Leverage: {context['leverage']}x")
        return "\n".join(parts) if parts else "No trading context."
    
    def _parse_analysis(self, response: str) -> dict:
        """Parse trading analysis response."""
        import json
        
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "{" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]
            else:
                json_str = response
            
            return json.loads(json_str)
        except:
            return {
                "trade_safe": False,
                "confidence": 0.3,
                "risk_level": "high",
                "recommendation": "wait",
                "reasoning": "Could not parse analysis"
            }


