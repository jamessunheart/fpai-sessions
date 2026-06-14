"""
Response Formatting Service
Per Spec - format API responses for different sources
"""

from typing import Dict, Any
from app.services.reasoning import format_response
from app.utils.logging import get_logger

log = get_logger(__name__)


async def format_combined_response(
    combined_data: Dict[str, Any],
    source: str = "chat"
) -> str:
    """
    Format combined responses from multiple droplets.
    Per Spec - different formatting for chat vs voice.
    
    Args:
        combined_data: Dict mapping droplet_key to response data
        source: "chat" or "voice"
        
    Returns:
        Formatted response string
    """
    log.info(
        "formatting_combined_response",
        droplet_count=len(combined_data),
        source=source
    )
    
    # Use AI formatting
    formatted = await format_response(combined_data, source)
    
    return formatted


def format_error_response(error_msg: str, source: str = "chat") -> str:
    """
    Format error messages appropriately for source.
    
    Args:
        error_msg: Error message
        source: "chat" or "voice"
        
    Returns:
        Formatted error message
    """
    if source == "voice":
        return f"Error: {error_msg}"
    else:
        return f"❌ **Error:** {error_msg}"


def format_success_response(message: str, source: str = "chat") -> str:
    """
    Format success messages appropriately for source.
    
    Args:
        message: Success message
        source: "chat" or "voice"
        
    Returns:
        Formatted success message
    """
    if source == "voice":
        return f"Success: {message}"
    else:
        return f"✅ **Success:** {message}"