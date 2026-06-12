"""
FCF Handler for JAI Telegram
============================
Integrates Feel→Choice→Feel into JAI chat.
"""
import httpx
import logging
from typing import Optional, Dict

logger = logging.getLogger("jai.fcf")

FCF_API = "http://127.0.0.1:8780"

STATES = ["calm", "busy", "curious", "anxious", "sad", "angry", "tired", "energized"]

# User sessions for multi-step flow
fcf_sessions: Dict[str, Dict] = {}


async def handle_fcf_message(user_id: str, message: str) -> Optional[str]:
    """Handle FCF-related messages."""
    msg = message.lower().strip()
    user_key = str(user_id)
    
    # Check for FCF triggers
    if any(word in msg for word in ["feel", "feeling", "how am i", "check in", "state"]):
        if "anxious" in msg or "stressed" in msg:
            return await start_fcf(user_key, "anxious", 3)
        elif "tired" in msg or "exhausted" in msg:
            return await start_fcf(user_key, "tired", 3)
        elif "sad" in msg or "down" in msg:
            return await start_fcf(user_key, "sad", 3)
        elif "angry" in msg or "frustrated" in msg:
            return await start_fcf(user_key, "angry", 3)
        elif "busy" in msg or "overwhelmed" in msg:
            return await start_fcf(user_key, "busy", 3)
        elif "good" in msg or "great" in msg or "calm" in msg:
            return await start_fcf(user_key, "calm", 2)
        elif "curious" in msg or "interested" in msg:
            return await start_fcf(user_key, "curious", 2)
        elif "energized" in msg or "excited" in msg:
            return await start_fcf(user_key, "energized", 3)
        else:
            # Ask for state
            return """How are you feeling right now?

Pick one:
• calm
• busy  
• curious
• anxious
• sad
• angry
• tired
• energized

And rate intensity 1-5 (e.g. "anxious 4")"""
    
    # Check for state + intensity input
    for state in STATES:
        if state in msg:
            # Try to find intensity
            intensity = 3  # default
            for i in range(1, 6):
                if str(i) in msg:
                    intensity = i
                    break
            return await start_fcf(user_key, state, intensity)
    
    # Check if user is in FCF flow
    if user_key in fcf_sessions:
        sess = fcf_sessions[user_key]
        
        # Check for "done" or "skip" after choice
        if sess.get("awaiting") == "done":
            if "done" in msg or "did it" in msg or "yes" in msg:
                return await complete_fcf(user_key, accepted=True)
            elif "skip" in msg or "no" in msg or "later" in msg:
                return await complete_fcf(user_key, accepted=False)
        
        # Check for "helped?" response
        if sess.get("awaiting") == "helped":
            if "yes" in msg or "better" in msg or "helped" in msg:
                return await finish_fcf(user_key, "yes")
            elif "no" in msg or "worse" in msg:
                return await finish_fcf(user_key, "no")
            else:
                return await finish_fcf(user_key, "same")
    
    return None


async def start_fcf(user_id: str, state: str, intensity: int) -> str:
    """Start FCF loop."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Get session
            r = await client.post(f"{FCF_API}/feel", json={
                "user_id": user_id,
                "state": state,
                "intensity": intensity
            })
            sess = r.json()
            
            # Get choice
            r = await client.get(f"{FCF_API}/choice", params={"session_id": sess["session_id"]})
            choice = r.json()
            
            action = choice["action"]
            
            # Store session
            fcf_sessions[user_id] = {
                "session_id": sess["session_id"],
                "state": state,
                "intensity": intensity,
                "action": action,
                "awaiting": "done"
            }
            
            trigger_msg = ""
            if choice.get("trigger_type"):
                trigger_msg = f"\n(Detected: {choice['trigger_type']} pattern)"
            
            title = action.get('title', 'Pause')
            duration = action.get('duration_sec', 20)
            instructions = action.get('instructions', 'Take a breath.')
            
            return f"""📍 {state.upper()} (intensity {intensity}/5){trigger_msg}

Here is one thing to try:

**{title}** ({duration}s)
{instructions}

When done, say "done" or "skip" """
            
    except Exception as e:
        logger.error(f"FCF start error: {e}")
        return "FCF service not available right now."


async def complete_fcf(user_id: str, accepted: bool) -> str:
    """After user does/skips action."""
    if user_id not in fcf_sessions:
        return "No active check-in."
    
    sess = fcf_sessions[user_id]
    sess["accepted"] = accepted
    sess["awaiting"] = "helped"
    
    if accepted:
        return """Good! How do you feel now?

• better / yes
• same
• worse / no"""
    else:
        return """Okay, skipped.

How do you feel now?
• better / yes  
• same
• worse / no"""


async def finish_fcf(user_id: str, helped: str) -> str:
    """Complete the FCF loop."""
    if user_id not in fcf_sessions:
        return "No active check-in."
    
    sess = fcf_sessions[user_id]
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            new_intensity = max(1, sess["intensity"] - 1) if helped == "yes" else sess["intensity"]
            
            r = await client.post(f"{FCF_API}/feel_again", json={
                "session_id": sess["session_id"],
                "state": sess["state"],
                "intensity": new_intensity,
                "helped": helped,
                "accepted": sess.get("accepted", False)
            })
            result = r.json()
            
            del fcf_sessions[user_id]
            
            if helped == "yes":
                summary = result.get('summary', 'Nice work.')
                return f"Logged. {summary}"
            elif helped == "no":
                return "Logged. Next time I will try something different."
            else:
                return "Logged. We are learning what works for you."
                
    except Exception as e:
        logger.error(f"FCF finish error: {e}")
        if user_id in fcf_sessions:
            del fcf_sessions[user_id]
        return "Logged (with hiccup)."


async def check_proactive(user_id: str) -> Optional[str]:
    """Check if proactive popup should fire."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{FCF_API}/popups", params={"user_id": user_id})
            data = r.json()
            
            if data.get("should_show"):
                action = data.get("action", {})
                msg = data.get('message', 'Quick reset?')
                title = action.get('title', 'Pause')
                duration = action.get('duration_sec', 20)
                instructions = action.get('instructions', 'Take a breath.')
                
                return f"""{msg}

**{title}** ({duration}s)
{instructions}

Say "yes" to try or "no" to skip."""
    except:
        pass
    
    return None








