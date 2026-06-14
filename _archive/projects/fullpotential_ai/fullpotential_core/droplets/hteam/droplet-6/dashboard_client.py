"""
HTTP client for communicating with Droplet 7 dashboard.
Handles transcript and response forwarding to the dashboard.
"""

import httpx
from datetime import datetime
from typing import Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Dashboard base URL - use HTTPS domain
DROPLET_7_BASE_URL = "https://drop7.fullpotential.ai"

# Timeout for HTTP requests (5 seconds)
REQUEST_TIMEOUT = 5.0


async def send_transcript(
    transcript: str,
    session_id: str,
    timestamp: Optional[str] = None
) -> bool:
    """
    Send transcript to Droplet 7 dashboard.
    
    Args:
        transcript: The user's spoken text or message
        session_id: Unique session identifier
        timestamp: Optional ISO timestamp (defaults to current time)
    
    Returns:
        True if successful, False otherwise
    """
    if not timestamp:
        timestamp = datetime.utcnow().isoformat()
    
    try:
        print(f"[Dashboard Client] Sending transcript to {DROPLET_7_BASE_URL}/voice/transcript")
        print(f"[Dashboard Client] Data: transcript='{transcript[:50]}...', session_id='{session_id}'")
        
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{DROPLET_7_BASE_URL}/voice/transcript",
                json={
                    "transcript": transcript,
                    "session_id": session_id,
                    "timestamp": timestamp
                }
            )
            print(f"[Dashboard Client] Response status: {response.status_code}")
            print(f"[Dashboard Client] Response body: {response.text}")
            response.raise_for_status()
            logger.info(f"✅ Transcript sent to Droplet 7: {transcript[:50]}...")
            print(f"[Dashboard Client] ✅ Transcript sent successfully")
            return True
    except httpx.TimeoutException:
        logger.warning(f"⏱️ Timeout sending transcript to Droplet 7")
        print(f"[Dashboard Client] ⏱️ Timeout sending transcript to Droplet 7")
        return False
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error sending transcript to Droplet 7: {e.response.status_code}")
        print(f"[Dashboard Client] ❌ HTTP error: {e.response.status_code} - {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"❌ Error sending transcript to Droplet 7: {e}")
        print(f"[Dashboard Client] ❌ Exception: {type(e).__name__}: {e}")
        import traceback
        print(f"[Dashboard Client] Traceback: {traceback.format_exc()}")
        return False


async def send_response(
    response_text: str,
    session_id: str,
    timestamp: Optional[str] = None
) -> bool:
    """
    Send AI response to Droplet 7 dashboard.
    
    Args:
        response_text: The AI's response text
        session_id: Unique session identifier (should match transcript session_id)
        timestamp: Optional ISO timestamp (defaults to current time)
    
    Returns:
        True if successful, False otherwise
    """
    if not timestamp:
        timestamp = datetime.utcnow().isoformat()
    
    try:
        print(f"[Dashboard Client] Sending response to {DROPLET_7_BASE_URL}/voice/response")
        print(f"[Dashboard Client] Data: response='{response_text[:50]}...', session_id='{session_id}'")
        
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{DROPLET_7_BASE_URL}/voice/response",
                json={
                    "response": response_text,
                    "session_id": session_id,
                    "timestamp": timestamp
                }
            )
            print(f"[Dashboard Client] Response status: {response.status_code}")
            print(f"[Dashboard Client] Response body: {response.text}")
            response.raise_for_status()
            logger.info(f"✅ Response sent to Droplet 7: {response_text[:50]}...")
            print(f"[Dashboard Client] ✅ Response sent successfully")
            return True
    except httpx.TimeoutException:
        logger.warning(f"⏱️ Timeout sending response to Droplet 7")
        print(f"[Dashboard Client] ⏱️ Timeout sending response to Droplet 7")
        return False
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error sending response to Droplet 7: {e.response.status_code}")
        print(f"[Dashboard Client] ❌ HTTP error: {e.response.status_code} - {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"❌ Error sending response to Droplet 7: {e}")
        print(f"[Dashboard Client] ❌ Exception: {type(e).__name__}: {e}")
        import traceback
        print(f"[Dashboard Client] Traceback: {traceback.format_exc()}")
        return False

