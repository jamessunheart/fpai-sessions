"""
AI Reasoning Engine
Per Spec - Gemini 2.5 Flash for intent understanding
Located in services/ per CODE_STANDARDS.md
Filename: app/services/reasoning.py
"""

import json
import re
import google.generativeai as genai
from typing import Dict, Any

from app.config import settings
from app.services.memory import ConversationMemory
from app.utils.logging import get_logger
from app.services.registry_info import build_system_context
from app.models.chat import ReasoningResult

log = get_logger(__name__)

# Configure Gemini
genai.configure(api_key=settings.get_gemini_api_key())
model = genai.GenerativeModel("gemini-2.5-flash")

log.info("gemini_model_configured", model="gemini-2.5-flash")


async def reason_about_intent(
    user_input: str,
    conversation: ConversationMemory
) -> ReasoningResult:
    """
    Use Gemini to reason about user intent with conversation context.
    Per Spec - AI-powered intent reasoning requirement.
    
    Args:
        user_input: User's natural language message
        conversation: ConversationMemory with context
        
    Returns:
        ReasoningResult with action_type and queries
        
    Example:
        >>> result = await reason_about_intent(
        ...     "show me all registered items",
        ...     conversation
        ... )
        >>> print(result.action_type)
        'single_query'
    """
    log.info("reasoning_started", input_length=len(user_input))
    
    # Build context
    system_context = build_system_context()
    conversation_context = conversation.get_context()
    
    reasoning_prompt = f"""
You are an intelligent API orchestrator. Analyze the user's request WITH CONVERSATION CONTEXT.

{system_context}

{conversation_context}

## Current User Request
"{user_input}"

## Critical Understanding Rules
1. "all droplets" / "every droplet" / "fetch all droplets" = User wants information FROM ALL available droplets
   - Query ALL droplets that have GET endpoints
   - Use action_type: "multiple_queries"
   - For each droplet, use its most informative GET endpoint (status, getAll, system, etc.)

2. "all items" / "all registered" / "getAll" = User wants the getAll endpoint specifically from Registry (droplet_1)
   - Use action_type: "single_query"
   - Target only droplet_1's getAll endpoint

3. "droplet X and droplet Y" = User wants info from specific droplets
   - Use action_type: "multiple_queries"
   - Query only the mentioned droplets with their GET endpoints

4. POST endpoints ALWAYS need data in "key:value" format
   - If no data provided, set needs_clarification=true

## Your Task
Respond with ONLY a JSON object (no markdown, no backticks):

{{
    "reasoning": "Brief explanation considering conversation context",
    "action_type": "single_query|multiple_queries|needs_clarification",
    "needs_clarification": true|false,
    "clarification_message": "What to ask user if needs_clarification is true",
    "queries": [
        {{
            "droplet": "droplet_X",
            "endpoint": "endpoint_name",
            "method": "GET|POST",
            "needs_data": true|false,
            "extracted_data": {{}},
            "confidence": 0.0-1.0
        }}
    ]
}}

Now analyze the request. Return ONLY the JSON object, no other text.
"""
    
    try:
        # Call Gemini
        response = model.generate_content(reasoning_prompt)
        response_text = response.text.strip()
        
        log.debug("gemini_raw_response", response_length=len(response_text))
        
        # Clean up response - remove markdown code blocks if present
        response_text = re.sub(r'```json\s*|\s*```', '', response_text).strip()
        
        # Parse JSON
        reasoning_data = json.loads(response_text)
        
        # Create ReasoningResult
        result = ReasoningResult(
            reasoning=reasoning_data.get("reasoning", ""),
            action_type=reasoning_data.get("action_type", "error"),
            needs_clarification=reasoning_data.get("needs_clarification", False),
            clarification_message=reasoning_data.get("clarification_message"),
            queries=reasoning_data.get("queries", [])
        )
        
        log.info(
            "reasoning_completed",
            action_type=result.action_type,
            needs_clarification=result.needs_clarification,
            query_count=len(result.queries)
        )
        
        return result
        
    except json.JSONDecodeError as e:
        log.error(
            "reasoning_json_parse_error",
            error=str(e),
            response_snippet=response_text[:200] if 'response_text' in locals() else "N/A"
        )
        
        return ReasoningResult(
            reasoning="Failed to parse AI response",
            action_type="error",
            needs_clarification=False,
            queries=[]
        )
        
    except Exception as e:
        log.error("reasoning_error", error=str(e), exc_info=True)
        
        return ReasoningResult(
            reasoning=f"Error during reasoning: {str(e)}",
            action_type="error",
            needs_clarification=False,
            queries=[]
        )


async def format_response(
    combined_data: Dict[str, Any],
    source: str = "chat"
) -> str:
    """
    Format API responses using Gemini.
    Per Spec - AI-powered response formatting.
    
    Args:
        combined_data: Dict of results from droplets
        source: Message source ("chat" or "voice")
        
    Returns:
        Formatted response string
        
    Example:
        >>> formatted = await format_response(
        ...     {"droplet_1": {"items": [...]}},
        ...     source="chat"
        ... )
    """
    log.info("formatting_response", data_keys=list(combined_data.keys()), source=source)
    
    try:
        # Source-specific formatting instructions
        source_context = ""
        if source == "voice":
            source_context = """
CRITICAL: Format this for VOICE output.
- Use natural spoken language only
- NO emojis, NO symbols, NO special characters
- NO markdown formatting
- Spell out "colon" instead of ":"
- Example: "Item one colon Registry. Item two colon Dashboard."
"""
        else:
            source_context = """
Format this for CHAT output.
- Use emojis for visual appeal (✅, 📊, ❌, etc.)
- Use markdown formatting (bold, lists, etc.)
- Use bullet points for lists
- Make it visually engaging
"""
        
        prompt = f"""
Convert this API response data into a clear, user-friendly summary.

{source_context}

Data from droplets:
{json.dumps(combined_data, indent=2)}

Provide a natural, readable summary that presents this information in the most helpful way.
"""
        
        response = model.generate_content(prompt)
        formatted = response.text.strip() if response and response.text else str(combined_data)
        
        log.info("response_formatted", length=len(formatted))
        
        return formatted
        
    except Exception as e:
        log.error("formatting_error", error=str(e))
        
        # Fallback to simple string representation
        return str(combined_data)


async def analyze_text(text: str) -> Dict[str, Any]:
    """
    Stateless text analysis.
    Per Spec - POST /analyze endpoint functionality.
    
    Args:
        text: Text to analyze
        
    Returns:
        Analysis result dict
    """
    log.info("analyzing_text", length=len(text))
    
    try:
        prompt = f"""
Analyze this text and provide insights:

Text: "{text}"

Provide a JSON response with:
- intent: What the user wants to do
- entities: Key entities mentioned
- sentiment: positive/negative/neutral
- confidence: 0.0-1.0
- suggested_action: What action to take

Return ONLY the JSON object.
"""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean and parse
        response_text = re.sub(r'```json\s*|\s*```', '', response_text).strip()
        analysis = json.loads(response_text)
        
        log.info("text_analysis_completed", intent=analysis.get("intent"))
        
        return analysis
        
    except Exception as e:
        log.error("text_analysis_error", error=str(e))
        
        return {
            "error": str(e),
            "intent": "unknown",
            "confidence": 0.0
        }