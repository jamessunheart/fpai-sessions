#!/usr/bin/env python3
"""
CIS Handler - Integrates CIS with JAI
=====================================
Handles state captures, outcomes, and pause/resume via chat.
"""
import asyncio
import re
import logging
from typing import Optional, Dict

logger = logging.getLogger("jai.cis")

# State keywords for detection
STATES = ["calm", "busy", "overloaded", "overwhelmed", "stuck", "open", "ready", "stressed", "anxious"]

async def handle_cis_message(user_id: str, message: str) -> Optional[str]:
    """
    Handle CIS-related messages.
    Returns None if not a CIS message (let brain handle it).
    """
    from cis import get_cis, parse_outcome_input
    
    msg = message.lower().strip()
    cis = get_cis()
    
    # PAUSE commands
    if msg in ["pause", "pause cis", "stop pings", "quiet", "/pause"]:
        cis.pause(user_id)
        return "Paused. Say 'resume' when ready."
    
    # RESUME commands
    if msg in ["resume", "unpause", "resume cis", "/resume"]:
        cis.resume(user_id)
        return "Resumed. I'm watching."
    
    # STATUS commands
    if msg in ["status", "cis status", "/status", "how am i"]:
        status = cis.get_status(user_id)
        current = status["current_state"]
        if current:
            response = f"State: {current.state} ({current.intensity}/5)\n"
            response += f"Entries today: {status['states_last_24h']}\n"
            if status["active_fuses"]:
                response += f"Fuses: {len(status['active_fuses'])} active"
            else:
                response += "Fuses: None"
            return response
        return "No state captured yet. Tell me how you're feeling."
    
    # OUTCOME responses (after an intervention)
    if msg in ["helped", "same", "no", "better", "worse", "yes", "y", "n"]:
        outcome = parse_outcome_input(msg)
        cis.capture_outcome(user_id, outcome)
        
        if outcome == "helped":
            return "Good. Noted that pattern."
        elif outcome == "no":
            return "Noted. Will try something different."
        else:
            return "Logged."
    
    # STATE capture: "busy 3", "stuck", "overloaded 4", etc.
    # Check if message contains a state word
    state_found = None
    for s in STATES:
        if s in msg:
            state_found = s
            break
    
    if state_found:
        # Check for intensity number
        intensity_match = re.search(r"\b([1-5])\b", msg)
        intensity = int(intensity_match.group(1)) if intensity_match else 3
        
        # Map similar words
        state_map = {
            "overwhelmed": "overloaded",
            "stressed": "overloaded", 
            "anxious": "overloaded",
            "ready": "open"
        }
        state = state_map.get(state_found, state_found)
        
        # Only trigger if this looks like a state report, not just conversation
        # Must be short (< 10 words) and contain state word prominently
        words = msg.split()
        if len(words) <= 10:
            result = await cis.capture_state(user_id, state, intensity, "high", "explicit")
            
            response = f"Logged: {state} {intensity}/5"
            
            if result.get("intervention"):
                # Intervention was sent, no need to echo
                return None  # Let the intervention message speak
            
            return response
    
    # Not a CIS message
    return None


async def proactive_check(user_id: str) -> Optional[str]:
    """
    Called periodically to check if proactive intervention needed.
    Returns message to send, or None.
    """
    from cis import get_cis
    
    cis = get_cis()
    
    # Get current state
    status = cis.get_status(user_id)
    current = status["current_state"]
    
    if not current:
        return None
    
    # Evaluate triggers
    trigger = cis.triggers.evaluate(user_id, current)
    
    if trigger.should_fire:
        # Decide
        decision = cis.decisions.decide(user_id, current, trigger.trigger_type)
        
        if decision.type != "silence" and decision.action_id:
            # Get action
            actions = cis.db.get_actions()
            action = next((a for a in actions if a.id == decision.action_id), None)
            
            if action:
                # Deliver
                delivery = await cis.delivery.deliver(
                    user_id, decision, action, trigger.trigger_type, current
                )
                
                if delivery["delivered"]:
                    return None  # Already sent via telegram
    
    return None








