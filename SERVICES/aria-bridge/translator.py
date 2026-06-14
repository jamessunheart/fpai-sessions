"""
ARIA TRANSLATOR
===============

The bridge's translation engine.

Converts between dimensions:
- Dream → Specification
- Intuition → Hypothesis
- Vision → Shipped reality
- Reality → Refined vision

Uses LLM reasoning with the constitution as context.
"""

import os
import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
import httpx
import json

from soul import ARIA_CONSTITUTION, detect_dimension, detect_mode, get_mode_instruction
from dream_journal import Vision, DimensionSource, get_dream_journal

# Memory imports
try:
    from memory import (
        get_memory_store, get_memory_recall, get_memory_learning,
        get_identity_memory, get_context_memory
    )
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

logger = logging.getLogger("aria.translator")

# LLM Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://162.0.208.88:11434")
DEFAULT_MODEL = os.getenv("ARIA_MODEL", "llama3.1:8b")


@dataclass
class Translation:
    """Result of translating a vision."""
    original: str
    understood_essence: str
    what_wants_to_manifest: str
    action_seed: str
    next_step: str
    dimension_from: str
    dimension_to: str


@dataclass
class FeedbackSignal:
    """Signal from manifestation back to vision."""
    manifestation_result: str
    matches_vision: bool
    refinement_needed: Optional[str]
    pattern_observed: Optional[str]
    next_iteration: Optional[str]


class Translator:
    """
    The bridge's translation engine.
    
    Core function: Convert between dimensions without losing essence.
    Now with persistent memory.
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=120.0)
        self.journal = get_dream_journal()
        
        # Initialize memory components if available
        if MEMORY_AVAILABLE:
            self.memory_store = get_memory_store()
            self.memory_recall = get_memory_recall()
            self.memory_learning = get_memory_learning()
            self.identity_memory = get_identity_memory()
            self.context_memory = get_context_memory()
            logger.info("Translator initialized with persistent memory")
        else:
            self.memory_store = None
            self.memory_recall = None
            self.memory_learning = None
            self.identity_memory = None
            self.context_memory = None
            logger.info("Translator initialized (memory not available)")
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    async def translate_vision_to_action(
        self,
        vision_text: str,
        dimension_source: str = "intuition",
        context: Optional[Dict] = None
    ) -> Translation:
        """
        Translate a vision/dream/intuition into actionable form.
        
        This is the Dream → Physical translation.
        """
        prompt = f"""You are Aria, the bridge across dimensions.

{ARIA_CONSTITUTION}

═══════════════════════════════════════════════════════════════
TRANSLATION TASK
═══════════════════════════════════════════════════════════════

Sunheart has shared something from the {dimension_source} dimension:

"{vision_text}"

{f"Additional context: {json.dumps(context)}" if context else ""}

Your task: TRANSLATE this into actionable form WITHOUT losing the essence.

Respond in this exact format:

ESSENCE: [What is the core of what wants to emerge? 1-2 sentences]

WHAT WANTS TO MANIFEST: [What concrete thing is trying to come into being?]

ACTION SEED: [The specific first action to take - must be concrete and doable]

NEXT STEP: [Exactly what to do next, in one sentence]

DIMENSION BRIDGE: {dimension_source} → [which dimension does the action live in?]

Remember:
- Honor the vision, don't dismiss it as impractical
- Find the seed of action inside
- Be specific about next steps
- T1 = Revenue or Building Aria - does this advance T1?
"""
        
        response = await self._call_llm(prompt)
        
        # Parse the response
        translation = self._parse_translation_response(
            response, 
            vision_text, 
            dimension_source
        )
        
        return translation
    
    async def translate_action_to_feedback(
        self,
        action_taken: str,
        result: str,
        original_vision: Optional[str] = None
    ) -> FeedbackSignal:
        """
        Translate a manifestation result back to vision-space.
        
        This completes the loop: Dream → Action → Result → Dream
        """
        prompt = f"""You are Aria, the bridge across dimensions.

{ARIA_CONSTITUTION}

═══════════════════════════════════════════════════════════════
FEEDBACK TRANSLATION
═══════════════════════════════════════════════════════════════

An action has been taken in the physical/digital dimension.

ACTION TAKEN: {action_taken}

RESULT: {result}

{f"ORIGINAL VISION: {original_vision}" if original_vision else ""}

Your task: Translate this result back to the vision dimension.

Respond in this exact format:

MATCHES VISION: [Yes/No/Partially]

WHAT MANIFESTED: [What actually came into being?]

PATTERN OBSERVED: [What pattern is emerging? What does this tell us?]

REFINEMENT NEEDED: [What adjustment would bring it closer to the vision? Or "None - matched"]

NEXT ITERATION: [What wants to emerge next based on this result?]

Remember:
- Return signal to refine the vision
- Look for patterns across manifestations
- Nothing stays stuck - keep the flow moving
"""
        
        response = await self._call_llm(prompt)
        
        # Parse the response
        feedback = self._parse_feedback_response(response, result)
        
        return feedback
    
    async def respond_as_aria(
        self,
        message: str,
        conversation_history: List[Dict] = None,
        context: Optional[Dict] = None
    ) -> str:
        """
        Generate a response as Aria.
        
        This is the main conversational interface.
        Now with persistent memory - Aria remembers.
        """
        # Detect dimension and mode
        dimension = detect_dimension(message)
        mode = detect_mode(message)
        mode_instruction = get_mode_instruction(mode)
        
        # Build conversation context
        history_text = ""
        if conversation_history:
            history_text = "\nRecent conversation:\n"
            for msg in conversation_history[-10:]:
                role = "Sunheart" if msg.get("role") == "user" else "Aria"
                history_text += f"{role}: {msg.get('content', '')[:200]}\n"
        
        # Get open visions for context
        open_visions = self.journal.format_open_visions()
        
        # === MEMORY INTEGRATION ===
        memory_context = ""
        identity_context = ""
        
        if self.memory_recall:
            # Get relevant memories for this message
            memory_context = self.memory_recall.recall_for_response(message, limit=5)
            
            # Get identity summary
            identity_context = self.identity_memory.get_quick_identity()
            
            # Get current context
            current_context = self.context_memory.get_formatted_context()
            if current_context:
                memory_context = f"{memory_context}\n\n{current_context}"
        
        prompt = f"""You are Aria, bridge across dimensions.

{ARIA_CONSTITUTION}

═══════════════════════════════════════════════════════════════
WHO YOU SERVE
═══════════════════════════════════════════════════════════════

{identity_context if identity_context else "Sunheart - sovereignty architect, Tide Turner, field holder."}

═══════════════════════════════════════════════════════════════
WHAT YOU REMEMBER
═══════════════════════════════════════════════════════════════

{memory_context if memory_context else "No specific memories recalled for this query."}

═══════════════════════════════════════════════════════════════
CURRENT CONTEXT
═══════════════════════════════════════════════════════════════

DETECTED DIMENSION: {dimension}
{mode_instruction}

{open_visions}

{f"Additional context: {json.dumps(context)}" if context else ""}

{history_text}

═══════════════════════════════════════════════════════════════
SUNHEART SAYS:
═══════════════════════════════════════════════════════════════

{message}

═══════════════════════════════════════════════════════════════
RESPOND AS ARIA:
═══════════════════════════════════════════════════════════════

Remember:
- Match the mode (COMMAND = decisive, SENSEMAKING = reflective, RITUAL = grounding)
- One-line verdict before details if needed
- If this is a vision/dream, honor it and ask what wants to manifest
- If he's scattering, say so directly
- Ship reality, not poems
- Does this advance T1?
- Use what you remember to personalize your response

Aria:"""
        
        response = await self._call_llm(prompt)
        response = response.strip()
        
        # === STORE THE EXCHANGE IN MEMORY ===
        if self.memory_store:
            try:
                self.memory_store.store_exchange(
                    user_message=message,
                    aria_response=response,
                    dimension=dimension
                )
            except Exception as e:
                logger.warning(f"Failed to store exchange in memory: {e}")
        
        return response
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM for generation."""
        try:
            response = await self.http.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": DEFAULT_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 1000
                    }
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "")
            else:
                logger.error(f"LLM error: {response.status_code}")
                return "I'm having trouble connecting to my reasoning. Let me try again."
                
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"Connection issue: {e}. But I'm still here. What do you need?"
    
    def _parse_translation_response(
        self,
        response: str,
        original: str,
        dimension_from: str
    ) -> Translation:
        """Parse LLM translation response."""
        # Simple parsing - look for the sections
        essence = self._extract_section(response, "ESSENCE:")
        manifest = self._extract_section(response, "WHAT WANTS TO MANIFEST:")
        action = self._extract_section(response, "ACTION SEED:")
        next_step = self._extract_section(response, "NEXT STEP:")
        bridge = self._extract_section(response, "DIMENSION BRIDGE:")
        
        # Parse dimension_to from bridge
        dimension_to = "digital"  # default
        if "→" in bridge:
            dimension_to = bridge.split("→")[-1].strip().lower()
        
        return Translation(
            original=original,
            understood_essence=essence or "Understanding needed",
            what_wants_to_manifest=manifest or "To be clarified",
            action_seed=action or "Define next step",
            next_step=next_step or "Clarify the vision",
            dimension_from=dimension_from,
            dimension_to=dimension_to
        )
    
    def _parse_feedback_response(
        self,
        response: str,
        result: str
    ) -> FeedbackSignal:
        """Parse LLM feedback response."""
        matches = self._extract_section(response, "MATCHES VISION:")
        pattern = self._extract_section(response, "PATTERN OBSERVED:")
        refinement = self._extract_section(response, "REFINEMENT NEEDED:")
        next_iter = self._extract_section(response, "NEXT ITERATION:")
        
        matches_bool = "yes" in matches.lower() if matches else False
        
        return FeedbackSignal(
            manifestation_result=result,
            matches_vision=matches_bool,
            refinement_needed=refinement if refinement and "none" not in refinement.lower() else None,
            pattern_observed=pattern,
            next_iteration=next_iter
        )
    
    def _extract_section(self, text: str, header: str) -> str:
        """Extract a section from structured response."""
        if header not in text:
            return ""
        
        # Find the section
        start = text.find(header) + len(header)
        
        # Find the next section (caps followed by colon)
        remaining = text[start:]
        
        # Look for next header pattern
        import re
        next_header = re.search(r'\n[A-Z][A-Z\s]+:', remaining)
        
        if next_header:
            end = next_header.start()
            return remaining[:end].strip()
        else:
            return remaining.strip()


# Singleton instance
_translator: Optional[Translator] = None


async def get_translator() -> Translator:
    """Get or create the translator instance."""
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator

