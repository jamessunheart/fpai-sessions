#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - OPUS TELEGRAM HANDLER
=============================================

Integrates Opus Brain into Telegram for intelligent conversations.
Now with Evolution Learning AND Ascension Protocol integration!
"""

import os
import logging
import time
import asyncio
from typing import Optional, Dict
import httpx

# Authority system
try:
    from ..access.authority import (
        get_user_authority,
        is_authorized,
        can_use_command,
        AuthorityLevel,
        get_authority_context,
        is_first_interaction,
        mark_first_interaction
    )
    from ..access.rate_limiter import check_rate_limit, record_request
    AUTHORITY_ENABLED = True
    RATE_LIMIT_ENABLED = True
except ImportError:
    try:
        from access.authority import (
            get_user_authority,
            is_authorized,
            can_use_command,
            AuthorityLevel,
            get_authority_context,
            is_first_interaction,
            mark_first_interaction
        )
        from access.rate_limiter import check_rate_limit, record_request
        AUTHORITY_ENABLED = True
        RATE_LIMIT_ENABLED = True
    except ImportError:
        AUTHORITY_ENABLED = False
        RATE_LIMIT_ENABLED = False

try:
    from ..brain import (
        get_brain,
        think,
        quick_think,
        get_brain_status,
        BrainResponse,
        get_conversation
    )
except ImportError:
    # Fallback for direct execution
    from brain import (
        get_brain,
        think,
        quick_think,
        get_brain_status,
        BrainResponse,
        get_conversation
    )

# Evolution learning integration
try:
    from sovereign.evolution import (
        log_interaction,
        record_capability_request,
        learn_proactive_pattern,
        record_efficiency_metrics,
        get_interaction_logger,
        on_aria_interaction,
        detect_patterns_single,
        notifier
    )
    from sovereign.evolution.learner import learn_from_error
    EVOLUTION_ENABLED = True
except ImportError:
    EVOLUTION_ENABLED = False

# ============================================================================
# ASCENSION PROTOCOL INTEGRATION
# ============================================================================

try:
    from sovereign.ascension import (
        # Phase 1: Continuous Learning
        process_interaction,
        get_memory_graph,
        learn_from_interaction,
        get_micro_learner,
        record_feedback,
        get_response_recommendations,
        
        # Phase 2: Predictive Intelligence
        analyze_context,
        get_rhythm_detector,
        record_activity,
        
        # Phase 3: Autonomous Execution
        record_interaction_metrics,
    )
    from sovereign.agents import get_orchestrator
    from sovereign.revenue import get_roi_tracker
    
    ASCENSION_ENABLED = True
except ImportError as e:
    ASCENSION_ENABLED = False
    import traceback
    traceback.print_exc()

logger = logging.getLogger("aria.telegram.opus")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


class OpusTelegramHandler:
    """
    Handle intelligent conversations via Telegram.
    
    Uses Opus Brain for Cursor-level intelligence.
    Now with:
    - Evolution Learning
    - Ascension Protocol (Multi-Agent, Memory Graph, Context Awareness)
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=120.0)
        self.brain = get_brain()
        
        # Initialize Ascension systems
        if ASCENSION_ENABLED:
            self.orchestrator = get_orchestrator()
            self.roi_tracker = get_roi_tracker()
            self.memory = get_memory_graph()
            self.micro = get_micro_learner()
            self.rhythm = get_rhythm_detector()
            logger.info("🚀 Ascension Protocol ENABLED - Multi-agent swarm active")
        else:
            logger.warning("⚠️ Ascension Protocol not available")
    
    async def close(self):
        await self.http.aclose()
    
    async def handle_message(self, chat_id: int, text: str) -> str:
        """
        Process a message through Opus brain with Ascension intelligence.
        
        Flow:
        0. CHECK AUTHORITY (Steward vs Apprentice vs Unknown)
        1. Analyze context (emotion, urgency, attention)
        2. Route to specialized agent if appropriate
        3. Process with Opus brain
        4. Learn from interaction
        5. Track ROI
        """
        start_time = time.time()
        response_text = ""
        success = True
        error_type = None
        error_msg = None
        model_used = "unknown"
        tools_used = []
        tokens = 0
        cost = 0.0
        
        # ====================================================================
        # AUTHORITY CHECK
        # ====================================================================
        authority_context = ""
        is_first_interaction = False
        if AUTHORITY_ENABLED:
            auth = get_user_authority(chat_id)
            
            # Block unknown users
            if auth.level == AuthorityLevel.UNKNOWN:
                logger.warning(f"Unauthorized user {chat_id} attempted access")
                return ("👋 Hello! I'm Aria, but I don't recognize you yet.\n\n"
                       "To use my capabilities, you need to be added as an **apprentice**.\n"
                       "Please contact James (@jsunheart) to join the Full Potential builder community.")
            
            # Check command authorization
            if text.startswith("/"):
                allowed, reason = can_use_command(chat_id, text)
                if not allowed:
                    logger.warning(f"User {chat_id} blocked from command: {text[:50]}")
                    return f"🚫 {reason}\n\nThis operation requires steward (James) approval."
            
            # Check if this is a first-time interaction (for onboarding)
            if AUTHORITY_ENABLED:
                is_first = is_first_interaction(chat_id)
                if is_first and auth.level == AuthorityLevel.APPRENTICE:
                    mark_first_interaction(chat_id)
                    logger.info(f"🌟 First interaction for apprentice {chat_id} - triggering onboarding")
                    is_first_interaction = True
                else:
                    is_first_interaction = False
            
            # Get context for Aria about who she's talking to
            authority_context = get_authority_context(chat_id, is_first=is_first_interaction)
            logger.info(f"Authority: {auth.level.value} for user {chat_id} (first={is_first_interaction})")
        
        # ====================================================================
        # RATE LIMIT CHECK
        # ====================================================================
        if RATE_LIMIT_ENABLED and AUTHORITY_ENABLED:
            allowed, message, retry_after = check_rate_limit(chat_id, "message")
            if not allowed:
                logger.warning(f"Rate limit exceeded for user {chat_id}")
                return message
            
            # Record the request
            record_request(chat_id, "message")
        
        # ====================================================================
        # ASCENSION: Pre-processing context analysis
        # ====================================================================
        context_analysis = None
        agent_response = None
        
        if ASCENSION_ENABLED:
            try:
                # Analyze emotional context and urgency
                context_analysis = analyze_context(text)
                
                # Record activity pattern for rhythm learning
                intent = self._classify_intent(text)
                record_activity(intent, self._extract_topic(text))
                
                # Get response recommendations based on learned patterns
                recommendations = get_response_recommendations(
                    urgency_score=context_analysis.urgency_score,
                    time_of_day=context_analysis.time_context.split("_")[-1] if "_" in context_analysis.time_context else None,
                    is_followup=context_analysis.repeated_queries > 0
                )
                
                # Log context for debugging
                if context_analysis.urgency_score > 0.7:
                    logger.info(f"⚡ HIGH URGENCY detected ({context_analysis.urgency_score:.2f})")
                if context_analysis.emotional_state.value in ["frustrated", "hurried"]:
                    logger.info(f"😤 User emotion: {context_analysis.emotional_state.value}")
                
            except Exception as e:
                logger.warning(f"Context analysis failed: {e}")
        
        try:
            # Send typing indicator
            await self._send_typing(chat_id)
            
            # ================================================================
            # SPECIAL COMMANDS
            # ================================================================
            if text.lower().startswith("/clear"):
                self.brain.clear(chat_id)
                response_text = "🧹 Conversation cleared. Starting fresh!"
                return response_text
            
            if text.lower().startswith("/status"):
                status = get_brain_status(chat_id)
                response_text = self._format_status(status)
                return response_text
            
            if text.lower().startswith("/continue"):
                response = await self.brain.continue_plan(chat_id)
                response_text = self._format_response(response)
                return response_text
            
            if text.lower().startswith("/quick "):
                message = text[7:].strip()
                response_text = await quick_think(message, chat_id)
                model_used = "quick"
                return response_text
            
            # ================================================================
            # ASCENSION: Try specialized agent routing first
            # ================================================================
            if ASCENSION_ENABLED and self._should_use_agent(text):
                try:
                    result = await self.orchestrator.process(text, {"chat_id": chat_id})
                    
                    if result.primary_response.success and result.primary_response.confidence > 0.7:
                        agent_response = result
                        response_text = result.final_content
                        model_used = f"agent:{result.primary_response.agent_name}"
                        
                        # If agent handled it well, we're done
                        if result.primary_response.confidence > 0.85:
                            logger.info(f"🤖 Agent '{result.primary_response.agent_name}' handled query (conf={result.primary_response.confidence:.2f})")
                            return response_text
                        
                        # Medium confidence - agent answered but might want more
                        logger.info(f"🤖 Agent provided partial answer, adding brain context")
                
                except Exception as e:
                    logger.warning(f"Agent routing failed: {e}")
            
            # ================================================================
            # MAIN BRAIN PROCESSING
            # ================================================================
            # Inject authority context for non-steward users
            enriched_text = text
            if authority_context and AUTHORITY_ENABLED:
                auth = get_user_authority(chat_id)
                if auth.level != AuthorityLevel.STEWARD:
                    # For apprentices/limited users, prepend context
                    enriched_text = f"[CONTEXT: User is {auth.level.value}. Apply appropriate access restrictions.]\n\n{text}"
            
            if self._is_simple_query(text):
                response_text = await quick_think(enriched_text, chat_id)
                model_used = "quick"
            else:
                # Full brain processing
                response = await think(enriched_text, chat_id)
                
                # If agent already provided partial answer, append brain response
                if agent_response and response.message:
                    response_text = response_text + "\n\n---\n\n" + self._format_response(response)
                else:
                    response_text = self._format_response(response)
                
                model_used = response.model_used or "opus"
                cost = response.cost or 0
                if response.tool_results:
                    tools_used = [r.tool_name for r in response.tool_results]
            
            return response_text
            
        except Exception as e:
            success = False
            error_type = type(e).__name__
            error_msg = str(e)
            response_text = f"❌ I encountered an error: {str(e)[:200]}"
            logger.error(f"Opus handler error for chat {chat_id}: {e}")
            
            # Log error for evolution learning
            if EVOLUTION_ENABLED:
                try:
                    learn_from_error(
                        error_type=error_type,
                        error_message=error_msg,
                        context=f"chat_id={chat_id}, message={text[:100]}"
                    )
                except:
                    pass
            
            return response_text
            
        finally:
            duration_ms = (time.time() - start_time) * 1000
            
            # ================================================================
            # ASCENSION: Post-processing learning
            # ================================================================
            if ASCENSION_ENABLED and response_text:
                try:
                    # Process through stream processor for feature extraction
                    interaction_id = f"{chat_id}-{int(time.time())}"
                    features = await process_interaction(
                        interaction_id=interaction_id,
                        user_message=text,
                        response=response_text,
                        response_time_ms=duration_ms,
                        tools_used=tools_used,
                        success=success,
                        chat_id=chat_id
                    )
                    
                    # Learn patterns in memory graph
                    topic = self._extract_topic(text)
                    intent = self._classify_intent(text)
                    outcome = "success" if success else "failure"
                    learn_from_interaction(
                        topic=topic,
                        action=intent,
                        outcome=outcome,
                        time_of_day=features.time_of_day
                    )
                    
                    # Record metrics for degradation monitoring
                    record_interaction_metrics(
                        response_time_ms=duration_ms,
                        success=success
                    )
                    
                    # Track ROI - every interaction saves James ~2 minutes
                    self.roi_tracker.track_interaction()
                    
                    # Track API cost if any
                    if cost > 0:
                        self.roi_tracker.track_api_cost("anthropic", tokens, cost * 1000)
                    
                except Exception as e:
                    logger.warning(f"Ascension post-processing failed: {e}")
            
            # Evolution System Integration
            if EVOLUTION_ENABLED and response_text:
                try:
                    insights = asyncio.create_task(on_aria_interaction(
                        user_id=str(chat_id),
                        message=text,
                        response=response_text,
                        model=model_used,
                        tools=tools_used,
                        time_ms=duration_ms,
                        tokens=tokens,
                        cost=cost,
                        success=success,
                        was_cached=False,
                        was_correction=False
                    ))
                    
                    interaction_data = {
                        "user_message": text,
                        "response": response_text,
                        "tool_count": len(tools_used),
                        "total_time_ms": duration_ms,
                        "id": 0
                    }
                    patterns = detect_patterns_single(interaction_data)
                    
                    high_severity = [p for p in patterns if p.severity == "high"]
                    if high_severity:
                        for p in high_severity:
                            logger.warning(f"High severity pattern: {p.detector} - {p.problem_description}")
                    
                except Exception as log_error:
                    logger.warning(f"Evolution logging failed: {log_error}")
            
            # ================================================================
            # APPRENTICE ACTIVITY LOGGING (Supabase)
            # ================================================================
            if AUTHORITY_ENABLED:
                try:
                    auth = get_user_authority(chat_id)
                    if auth.level == AuthorityLevel.APPRENTICE:
                        from integrations.supabase_client import get_supabase_client
                        client = get_supabase_client()
                        
                        # Determine activity type
                        activity_type = "message"
                        if tools_used:
                            activity_type = "tool_use"
                        if is_first_interaction:
                            activity_type = "onboarding"
                        
                        await client.log_apprentice_activity(
                            telegram_id=chat_id,
                            activity_type=activity_type,
                            details={
                                "message_preview": text[:100],
                                "tools_used": tools_used,
                                "duration_ms": duration_ms,
                                "success": success
                            }
                        )
                except Exception as e:
                    logger.warning(f"Apprentice activity logging failed: {e}")
            
            # ================================================================
            # COST ATTRIBUTION (Supabase)
            # ================================================================
            if cost > 0:
                try:
                    from integrations.supabase_client import get_supabase_client
                    client = get_supabase_client()
                    
                    await client.log_usage_cost(
                        telegram_id=chat_id,
                        operation="claude_api",
                        tokens=tokens,
                        cost_usd=cost,
                        model=model_used,
                        details={
                            "tools_used": tools_used,
                            "duration_ms": duration_ms
                        }
                    )
                except Exception as e:
                    logger.warning(f"Cost logging failed: {e}")
    
    def _should_use_agent(self, text: str) -> bool:
        """Check if this query should go to a specialized agent first."""
        text_lower = text.lower()
        
        # Trading queries -> Trader Agent
        if any(w in text_lower for w in ['signal', 'trade', 'position', 'sol', 'btc', 'eth', 'xrp', 'market']):
            return True
        
        # Server/status queries -> Monitor Agent
        if any(w in text_lower for w in ['server', 'service', 'status', 'health', 'memory', 'restart']):
            return True
        
        # Research queries -> Researcher Agent
        if any(w in text_lower for w in ['what is', 'how to', 'explain', 'search']):
            return True
        
        return False
    
    def _extract_topic(self, text: str) -> str:
        """Extract main topic from message."""
        text_lower = text.lower()
        
        # Trading assets
        for asset in ['sol', 'btc', 'eth', 'xrp', 'bitcoin', 'ethereum', 'solana']:
            if asset in text_lower:
                return asset
        
        # System topics
        if any(w in text_lower for w in ['server', 'service', 'docker', 'deploy']):
            return "system"
        
        if any(w in text_lower for w in ['build', 'code', 'file', 'create']):
            return "development"
        
        return "general"
    
    def _classify_intent(self, text: str) -> str:
        """Classify the user's intent."""
        text_lower = text.lower()
        
        if any(t in text_lower for t in ['trade', 'buy', 'sell', 'position', 'btc', 'eth', 'sol', 'signal']):
            return "trading"
        if any(s in text_lower for s in ['server', 'service', 'restart', 'deploy', 'docker', 'memory']):
            return "server"
        if any(b in text_lower for b in ['build', 'code', 'file', 'create', 'implement', 'fix']):
            return "build"
        if '?' in text:
            return "question"
        
        return "conversation"
    
    def _is_simple_query(self, text: str) -> bool:
        """Detect if query is simple (no tool use needed)."""
        text_lower = text.lower()
        
        complex_indicators = [
            "look at", "analyze", "read", "check", "build", "create", 
            "fix", "improve", "code", "file", "your code", "yourself",
            "what can you do", "your capabilities", "your powers",
            "deploy", "run", "execute", "search", "find", "show me"
        ]
        if any(w in text_lower for w in complex_indicators):
            return False
        
        simple_messages = [
            "hi", "hello", "hey", "thanks", "thank you",
            "ok", "okay", "got it", "cool", "nice", "great", "awesome",
            "yes", "no", "sure", "yep", "nope"
        ]
        if text_lower.strip() in simple_messages:
            return True
        
        if len(text) < 15 and not any(c in text for c in ["?", "!", "/"]):
            return True
        
        return False
    
    def _format_response(self, response: BrainResponse) -> str:
        """Format BrainResponse for Telegram."""
        parts = []
        
        if response.message:
            parts.append(response.message)
        
        if response.tool_results:
            successful = [r for r in response.tool_results if r.success]
            failed = [r for r in response.tool_results if not r.success]
            
            if successful:
                parts.append(f"\n\n✅ **Actions completed:** {len(successful)}")
                for r in successful[:3]:
                    parts.append(f"  • {r.tool_name}")
            
            if failed:
                parts.append(f"\n⚠️ **Issues:** {len(failed)}")
                for r in failed[:2]:
                    parts.append(f"  • {r.tool_name}: {r.error[:50]}...")
        
        if response.plan_created:
            parts.append("\n\n📋 Plan created. Use /continue to proceed step by step.")
        
        if response.awaiting_input:
            parts.append("\n\n⏳ Waiting for your response...")
        
        if response.cost > 0.01:
            parts.append(f"\n\n💰 Cost: ${response.cost:.4f} ({response.model_used})")
        
        return "\n".join(parts)
    
    def _format_status(self, status: Dict) -> str:
        """Format status for Telegram."""
        parts = ["**🧠 Brain Status**\n"]
        
        parts.append(f"Messages: {status['message_count']}")
        
        if status['working_files']:
            parts.append(f"Working files: {len(status['working_files'])}")
            for f in status['working_files'][:5]:
                parts.append(f"  • {f}")
        
        if status['modified_files']:
            parts.append(f"Modified: {', '.join(status['modified_files'][:3])}")
        
        if status['plan_progress']:
            p = status['plan_progress']
            parts.append(f"\n**Plan:** {p['description'][:50]}")
            parts.append(f"Progress: {p['current_step']}/{p['total_steps']}")
        
        stats = status['router_stats']
        parts.append(f"\n**API Usage:**")
        parts.append(f"Total cost: ${stats['total_cost']:.4f}")
        calls = stats['call_count']
        if any(calls.values()):
            parts.append(f"Calls: " + ", ".join(f"{k}={v}" for k, v in calls.items() if v > 0))
        
        # Ascension status
        if ASCENSION_ENABLED:
            parts.append(f"\n**🚀 Ascension:** Enabled")
            parts.append(f"  • Multi-Agent: 4 agents active")
            parts.append(f"  • Memory Graph: Learning")
            parts.append(f"  • Context Analysis: Active")
        
        if EVOLUTION_ENABLED:
            parts.append(f"\n**🧬 Evolution:** Enabled")
        
        return "\n".join(parts)
    
    async def _send_typing(self, chat_id: int):
        """Send typing indicator."""
        try:
            await self.http.post(
                f"{TELEGRAM_API}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"}
            )
        except:
            pass
    
    async def send_message(self, chat_id: int, text: str, buttons: list = None) -> bool:
        """Send a message to Telegram."""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        
        try:
            response = await self.http.post(f"{TELEGRAM_API}/sendMessage", json=payload)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Send failed: {e}")
            return False


# ============================================================================
# CONVENIENCE
# ============================================================================

_handler: Optional[OpusTelegramHandler] = None


def get_handler() -> OpusTelegramHandler:
    """Get global handler."""
    global _handler
    if _handler is None:
        _handler = OpusTelegramHandler()
    return _handler


async def process_telegram_message(chat_id: int, text: str) -> str:
    """Process a Telegram message through Opus brain."""
    handler = get_handler()
    return await handler.handle_message(chat_id, text)
