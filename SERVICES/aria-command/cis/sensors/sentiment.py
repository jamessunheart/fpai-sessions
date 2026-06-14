#!/usr/bin/env python3
"""
Real Sentiment Analysis
=======================
Uses Claude to understand actual message sentiment, not just keywords.

This upgrades the message sensor from keyword matching to true understanding.
"""
import os
import json
import httpx
import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger("cis.sensors.sentiment")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

@dataclass
class SentimentAnalysis:
    state: str  # calm, busy, overloaded, stuck, open
    intensity: int  # 1-5
    confidence: str  # low, medium, high
    emotions: list  # detected emotions
    energy_level: str  # low, medium, high
    needs_support: bool
    reasoning: str


ANALYSIS_PROMPT = """Analyze this message from James and determine his current state.

Message: "{message}"

Respond with ONLY a JSON object (no markdown, no explanation):
{{
    "state": "calm|busy|overloaded|stuck|open",
    "intensity": 1-5,
    "confidence": "low|medium|high",
    "emotions": ["list", "of", "emotions"],
    "energy_level": "low|medium|high",
    "needs_support": true/false,
    "reasoning": "brief explanation"
}}

State definitions:
- calm: relaxed, at ease, no pressure
- busy: active, productive, moving fast
- overloaded: too much, stressed, overwhelmed
- stuck: blocked, confused, can't progress
- open: receptive, curious, available

Intensity: 1=barely, 3=moderate, 5=extreme

Be honest. If the message is neutral or ambiguous, say so."""


async def analyze_sentiment(message: str) -> Optional[SentimentAnalysis]:
    """
    Use Claude to analyze actual sentiment of a message.
    Falls back to keyword analysis if Claude unavailable.
    """
    if not ANTHROPIC_API_KEY:
        logger.debug("No API key, using fallback")
        return _fallback_analysis(message)
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-haiku-20240307",  # Fast, cheap model for sensing
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": ANALYSIS_PROMPT.format(message=message)}]
                }
            )
            
            if response.status_code != 200:
                logger.warning(f"Claude error: {response.status_code}")
                return _fallback_analysis(message)
            
            result = response.json()
            text = result.get("content", [{}])[0].get("text", "")
            
            # Parse JSON response
            try:
                # Clean up response if needed
                text = text.strip()
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                
                data = json.loads(text)
                
                return SentimentAnalysis(
                    state=data.get("state", "calm"),
                    intensity=int(data.get("intensity", 3)),
                    confidence=data.get("confidence", "medium"),
                    emotions=data.get("emotions", []),
                    energy_level=data.get("energy_level", "medium"),
                    needs_support=data.get("needs_support", False),
                    reasoning=data.get("reasoning", "")
                )
            except json.JSONDecodeError:
                logger.warning(f"Could not parse Claude response: {text[:100]}")
                return _fallback_analysis(message)
                
    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}")
        return _fallback_analysis(message)


def _fallback_analysis(message: str) -> SentimentAnalysis:
    """Fallback keyword-based analysis."""
    msg_lower = message.lower()
    
    # Simple keyword matching
    state = "calm"
    intensity = 2
    emotions = []
    
    frustration_words = ["frustrated", "stuck", "can't", "won't", "broken", "ugh"]
    overwhelm_words = ["overwhelmed", "too much", "drowning", "exhausted"]
    calm_words = ["good", "great", "nice", "done", "thanks"]
    busy_words = ["quick", "fast", "busy", "rushing"]
    
    if any(w in msg_lower for w in frustration_words):
        state = "stuck"
        intensity = 3
        emotions.append("frustrated")
    elif any(w in msg_lower for w in overwhelm_words):
        state = "overloaded"
        intensity = 4
        emotions.append("overwhelmed")
    elif any(w in msg_lower for w in busy_words):
        state = "busy"
        intensity = 3
    elif any(w in msg_lower for w in calm_words):
        state = "calm"
        intensity = 2
        emotions.append("content")
    
    return SentimentAnalysis(
        state=state,
        intensity=intensity,
        confidence="low",  # Keyword matching is low confidence
        emotions=emotions,
        energy_level="medium",
        needs_support=state in ["stuck", "overloaded"],
        reasoning="keyword-based fallback analysis"
    )


def sync_analyze_sentiment(message: str) -> SentimentAnalysis:
    """Synchronous wrapper for sentiment analysis."""
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(analyze_sentiment(message))








