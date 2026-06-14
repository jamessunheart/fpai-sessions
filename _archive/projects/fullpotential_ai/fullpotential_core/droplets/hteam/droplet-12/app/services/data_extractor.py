"""
Data Extraction Service
Per Spec - extract key:value data from user input
"""

import re
from typing import Dict
from app.utils.logging import get_logger

log = get_logger(__name__)


def extract_keyvalue_data(text: str) -> Dict[str, str]:
    """
    Extract data from "key:value" format.
    Per Spec - POST data extraction requirement.
    
    Args:
        text: User input with key:value pairs
        
    Returns:
        Dict of extracted key-value pairs
        
    Examples:
        >>> extract_keyvalue_data("name:John id:123")
        {'name': 'John', 'id': '123'}
        
        >>> extract_keyvalue_data("status:active age:25 email:test@example.com")
        {'status': 'active', 'age': '25', 'email': 'test@example.com'}
        
        >>> extract_keyvalue_data("name:John Doe id:456")
        {'name': 'John Doe', 'id': '456'}
    """
    log.debug("extracting_keyvalue_data", text=text)
    
    # Pattern: word:value (value can have spaces until next key or end)
    # Matches: key:value key2:value2 or key:multi word value key2:value2
    pattern = r'(\w+):\s*([^:\s]+(?:\s+(?![^\s]+:)[^:\s]+)*)'
    matches = re.findall(pattern, text)
    
    if not matches:
        log.debug("no_keyvalue_data_found", text=text)
        return {}
    
    # Build dict from matches
    data = {}
    for key, value in matches:
        key_clean = key.strip()
        value_clean = value.strip()
        data[key_clean] = value_clean
    
    log.info("keyvalue_data_extracted", keys=list(data.keys()), count=len(data))
    
    return data


def validate_required_fields(
    data: Dict[str, str],
    required_fields: list[str]
) -> tuple[bool, list[str]]:
    """
    Validate that required fields are present.
    
    Args:
        data: Extracted data dict
        required_fields: List of required field names
        
    Returns:
        Tuple of (is_valid, missing_fields)
        
    Example:
        >>> data = {"name": "John", "id": "123"}
        >>> is_valid, missing = validate_required_fields(
        ...     data,
        ...     ["name", "id", "email"]
        ... )
        >>> print(is_valid, missing)
        False ['email']
    """
    missing = [field for field in required_fields if field not in data]
    is_valid = len(missing) == 0
    
    if not is_valid:
        log.warning("missing_required_fields", missing=missing)
    
    return is_valid, missing


# app/services/data_extractor.py - ADD THIS FUNCTION

def parse_validation_error(error_response: dict) -> tuple[bool, list[str], str]:
    """
    Parse error response from target droplet to extract validation issues.
    
    Returns:
        (is_validation_error, missing_fields, error_message)
    
    Example:
        >>> error = {"error": "Missing required fields: name, id"}
        >>> parse_validation_error(error)
        (True, ["name", "id"], "Missing required fields: name, id")
    """
    # Check if it's an error response
    if not error_response or "error" not in error_response:
        return False, [], ""
    
    error_msg = str(error_response.get("error", ""))
    
    # Common validation error patterns
    validation_keywords = [
        "missing", "required", "field", "must provide", 
        "expected", "invalid", "needs", "mandatory"
    ]
    
    # Check if it's a validation error
    is_validation = any(keyword in error_msg.lower() for keyword in validation_keywords)
    
    if not is_validation:
        return False, [], error_msg
    
    # Try to extract field names
    # Pattern 1: "Missing required fields: name, id, status"
    import re
    
    pattern1 = r"field(?:s)?[:\s]+([a-zA-Z0-9_,\s]+)"
    match1 = re.search(pattern1, error_msg, re.IGNORECASE)
    
    if match1:
        fields_str = match1.group(1)
        # Split by comma and clean
        missing_fields = [f.strip() for f in fields_str.split(",")]
        return True, missing_fields, error_msg
    
    # Pattern 2: "Field 'name' is required"
    pattern2 = r"'([a-zA-Z0-9_]+)'.+required"
    matches2 = re.findall(pattern2, error_msg, re.IGNORECASE)
    
    if matches2:
        return True, matches2, error_msg
    
    # Couldn't parse specific fields, but it's a validation error
    return True, [], error_msg

def format_data_for_post(data: Dict[str, str]) -> Dict[str, any]:
    """
    Format extracted data for POST request.
    Attempts to convert values to appropriate types.
    
    Args:
        data: Raw extracted data (all strings)
        
    Returns:
        Formatted data with type conversion
        
    Example:
        >>> format_data_for_post({"id": "123", "active": "true", "name": "John"})
        {'id': 123, 'active': True, 'name': 'John'}
    """
    formatted = {}
    
    for key, value in data.items():
        # Try to convert to int
        if value.isdigit():
            formatted[key] = int(value)
        # Try to convert to float
        elif value.replace('.', '', 1).isdigit():
            formatted[key] = float(value)
        # Convert boolean strings
        elif value.lower() in ['true', 'false']:
            formatted[key] = value.lower() == 'true'
        # Keep as string
        else:
            formatted[key] = value
    
    log.debug("data_formatted_for_post", original=data, formatted=formatted)
    
    return formatted


def generate_data_prompt(endpoint: str, droplet_name: str) -> str:
    """
    Generate a user-friendly prompt asking for data.
    Per Spec - clarification message for POST requests.
    
    Args:
        endpoint: Endpoint name (e.g., "register")
        droplet_name: Droplet name (e.g., "Registry")
        
    Returns:
        Formatted prompt string
        
    Example:
        >>> prompt = generate_data_prompt("register", "Registry")
        >>> print(prompt)
        🔍 Ready to **register** on **Registry**!
        ...
    """
    prompt = f"🔍 Ready to **{endpoint}** on **{droplet_name}**!\n\n"
    prompt += "Please provide the data in this format:\n\n"
    prompt += "**Format:** key:value key2:value2\n\n"
    prompt += "**Example:** name:MyService id:123 status:active\n\n"
    prompt += "Type the data, or 'cancel' to abort."
    
    return prompt


def generate_voice_data_prompt(endpoint: str, droplet_name: str) -> str:
    """
    Generate voice-appropriate prompt asking for data.
    Per Spec - voice formatting without symbols.
    
    Args:
        endpoint: Endpoint name
        droplet_name: Droplet name
        
    Returns:
        Voice-formatted prompt string (no emojis/symbols)
    """
    prompt = f"Ready to {endpoint} on {droplet_name}. "
    prompt += "Please provide the data in this format: "
    prompt += "key colon value. "
    prompt += "For example: name colon MyService, id colon 123. "
    prompt += "Or say cancel to abort."
    
    return prompt