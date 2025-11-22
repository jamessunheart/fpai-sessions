"""
Static Droplet Registry Information
Per Spec - droplet knowledge base for AI reasoning ONLY
NOTE: This is NOT used for communication - all requests go through Orchestrator 10
Located in services/ per CODE_STANDARDS.md (business logic, not utility)
Filename: app/services/registry_info.py
"""

from typing import Dict, List


# Static droplet definitions
# Per Spec - used for AI reasoning about which droplet to target
DROPLET_REGISTRY: Dict[str, Dict] = {
    "droplet_1": {
        "name": "Registry",
        "id": 1,
        "endpoints": ["/register", "/getAll", "/deregister"],
        "purpose": "Entity registration and listing",
        "description": "Manages registration and listing of all system components"
    },
    "droplet_2": {
        "name": "Dashboard",
        "id": 2,
        "endpoints": ["/status", "/metrics"],
        "purpose": "System status and metrics",
        "description": "Provides system status and performance metrics"
    },
    "droplet_10": {
        "name": "Orchestrator",
        "id": 10,
        "endpoints": ["/route", "/verify", "/heartbeat", "/message"],
        "purpose": "Request routing, verification, and command execution",
        "description": "Routes requests, verifies operations, and executes commands like create_task"
    },
    "droplet_12": {
        "name": "Chat Orchestrator",
        "id": 12,
        "endpoints": ["/chat", "/analyze", "/process"],
        "purpose": "Chat interaction and analysis",
        "description": "Handles chat interactions and natural language analysis"
    },
    "droplet_14": {
        "name": "Visibility Deck",
        "id": 14,
        "endpoints": ["/system", "/snapshots"],
        "purpose": "System overview and snapshots",
        "description": "System-wide overview and snapshot management"
    },
    "droplet_16": {
        "name": "Onboarding",
        "id": 16,
        "endpoints": ["/onboard", "/progress"],
        "purpose": "User onboarding",
        "description": "User onboarding and progress tracking"
    },
    "droplet_6": {
        "name": "Voice",
        "id": 6,
        "endpoints": ["/transcribe", "/speak"],
        "purpose": "Voice interaction",
        "description": "Voice transcription and text-to-speech"
    }
}


# POST endpoints that require data
POST_ENDPOINTS = {
    "register", "route", "verify", "chat", "analyze", "message",
    "onboard", "transcribe", "speak", "process", "deregister"
}


def get_droplet_by_id(droplet_id: int) -> Dict | None:
    """
    Get droplet info by ID.
    
    Args:
        droplet_id: Droplet ID number
        
    Returns:
        Droplet info dict or None if not found
    """
    droplet_key = f"droplet_{droplet_id}"
    return DROPLET_REGISTRY.get(droplet_key)


def get_droplet_by_name(name: str) -> Dict | None:
    """
    Get droplet info by name.
    
    Args:
        name: Droplet name (case-insensitive)
        
    Returns:
        Droplet info dict or None if not found
    """
    name_lower = name.lower()
    for droplet_key, info in DROPLET_REGISTRY.items():
        if info["name"].lower() == name_lower:
            return {**info, "key": droplet_key}
    return None


def is_post_endpoint(endpoint: str) -> bool:
    """
    Check if endpoint requires POST method.
    
    Args:
        endpoint: Endpoint name (without leading slash)
        
    Returns:
        True if POST endpoint, False if GET
    """
    endpoint_clean = endpoint.strip("/")
    return endpoint_clean in POST_ENDPOINTS


def get_all_droplets() -> List[Dict]:
    """
    Get list of all droplets.
    
    Returns:
        List of droplet info dicts
    """
    return [
        {**info, "key": key}
        for key, info in DROPLET_REGISTRY.items()
    ]


def build_system_context() -> str:
    """
    Build comprehensive context about available droplets for AI reasoning.
    Per Spec - used in Gemini reasoning prompts.
    
    Returns:
        Formatted context string describing all droplets
    """
    context = "## Available System Components (Droplets)\n\n"
    
    for droplet_key, info in sorted(
        DROPLET_REGISTRY.items(),
        key=lambda x: x[1]["id"]
    ):
        droplet_id = info["id"]
        droplet_name = info["name"]
        
        context += f"**Droplet {droplet_id} ({droplet_name})**\n"
        context += f"- Purpose: {info['purpose']}\n"
        context += "- Endpoints:\n"
        
        for endpoint in info["endpoints"]:
            method = "POST (needs data)" if is_post_endpoint(endpoint) else "GET"
            context += f"  • {endpoint} ({method}): {get_endpoint_description(endpoint)}\n"
        
        context += "\n"
    
    return context


def get_endpoint_description(endpoint: str) -> str:
    """
    Get human-readable description of endpoint.
    
    Args:
        endpoint: Endpoint path
        
    Returns:
        Description string
    """
    descriptions = {
        "/register": "Register new entities in the system",
        "/getAll": "Retrieve all registered items",
        "/deregister": "Remove entity from registry",
        "/status": "Get current operational status",
        "/metrics": "Get performance and resource usage metrics",
        "/message": "Send a command to the droplet, e.g., 'create_task'",
        "/route": "Route a message to specific target",
        "/verify": "Verify operation or data validity",
        "/heartbeat": "Report droplet health status",
        "/chat": "Send chat messages",
        "/analyze": "Analyze text or data",
        "/process": "Process inter-droplet messages",
        "/system": "Get system-wide overview",
        "/snapshots": "Get or create system snapshots",
        "/onboard": "Start onboarding process",
        "/progress": "Check onboarding progress",
        "/transcribe": "Convert speech to text",
        "/speak": "Convert text to speech"
    }
    
    return descriptions.get(endpoint, "Perform operation")