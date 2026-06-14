#!/usr/bin/env python3
"""
ARIA AUTHORITY SYSTEM
======================

Multi-user access control for Aria.
Steward (James) gets full access. Apprentices get limited, safe access.

Authority Hierarchy:
1. STEWARD - Full access to all tools and operations
2. APPRENTICE - Can chat, query, build in sandbox, but NO sensitive ops
3. UNKNOWN - Blocked or minimal access

Persistence:
- Authority is persisted to Supabase on changes
- Loaded from Supabase on startup
"""

import os
import logging
from enum import Enum
from typing import Optional, Set, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("aria.authority")

# Track first interactions for onboarding
FIRST_INTERACTION_CACHE: Dict[int, datetime] = {}


class AuthorityLevel(Enum):
    """Authority levels for users."""
    STEWARD = "steward"       # Full access (James)
    APPRENTICE = "apprentice"  # Limited access (builders)
    UNKNOWN = "unknown"        # No access


@dataclass
class UserAuthority:
    """User's authority information."""
    user_id: int
    username: Optional[str]
    level: AuthorityLevel
    name: Optional[str] = None


# ============================================================================
# CONFIGURATION
# ============================================================================

# Steward user IDs (full access)
# BACKUP: Add additional Telegram IDs here for redundancy
STEWARD_IDS: Set[int] = {
    1759822075,  # James Sunheart (@jsunheart) - Primary
    # Add backup account IDs here:
    # 123456789,  # James backup account
}

# Recovery secret - store this somewhere safe!
# Use via API: POST /api/authority/recover with {"secret": "...", "user_id": ...}
RECOVERY_SECRET = os.getenv("AUTHORITY_RECOVERY_SECRET", "fp-recover-sunheart-2025")

# Apprentice user IDs (limited access)
# Add apprentices here as they join
APPRENTICE_IDS: Set[int] = set()

# Commands that require STEWARD authority
STEWARD_ONLY_COMMANDS = {
    # Server operations
    "/restart", "/fix", "/docker", "/deploy",
    # Trading
    "/execute", "/trade", "/position",
    # System modification
    "/edit", "/write", "/delete",
    # Sensitive data
    "/keys", "/secrets", "/env",
    # Admin
    "/addapprentice", "/removeapprentice", "/authority",
}

# Tools that require STEWARD authority
STEWARD_ONLY_TOOLS = {
    "restart_service",
    "edit_file",
    "write_file",
    "delete_file",
    "run_command",  # Dangerous shell commands
    "execute_trade",
    "deploy_service",
    "send_sms",  # Costs money
    "send_email",  # Could be misused
    "make_phone_call",  # Costs money
}

# Safe tools for apprentices
APPRENTICE_ALLOWED_TOOLS = {
    "read_file",
    "list_directory",
    "search_code",
    "get_system_health",
    "get_time",
    "web_search",
    "recall_memory",
    "store_memory",
    "read_ontology",
    "check_governance",
    # Builder tools - apprentices can build modules in their workspace
    "scaffold_module",
    "update_module_code",
    "test_module",
    "list_my_modules",
    "submit_module",
    "get_module_code",
    "delete_module",
}

# Paths apprentices can write to (relative to /opt/fpai/)
APPRENTICE_WRITE_PATHS = [
    "/opt/fpai/labs/apprentices/",  # Their personal workspace
    "/opt/fpai/labs/submissions/",  # Where they submit work
    "/opt/fpai/labs/",              # General labs area for builder modules
]

# Paths apprentices can read (more permissive)
APPRENTICE_READ_PATHS = [
    "/opt/fpai/labs/",              # All of labs
    "/opt/fpai/apprentice-os/library/",  # Module library
    "/opt/fpai/apprentice-os/core/standards/",  # Standards docs
]

# Paths that are NEVER accessible to apprentices
FORBIDDEN_PATHS = [
    "/opt/fpai/aria-command/",      # Core system
    "/opt/fpai/aria/",              # Aria core
    ".env",                         # Environment files
    "/etc/",                        # System config
    "/root/",                       # Root home
    "credentials",                  # Credential files
    "secret",                       # Secret files
    "api_key",                      # API keys
]


# ============================================================================
# AUTHORITY CHECKING
# ============================================================================

def get_user_authority(user_id: int, username: Optional[str] = None) -> UserAuthority:
    """
    Get authority level for a user.
    
    Args:
        user_id: Telegram user ID
        username: Optional username
        
    Returns:
        UserAuthority with level and permissions
    """
    if user_id in STEWARD_IDS:
        return UserAuthority(
            user_id=user_id,
            username=username,
            level=AuthorityLevel.STEWARD,
            name="Steward"
        )
    
    if user_id in APPRENTICE_IDS:
        return UserAuthority(
            user_id=user_id,
            username=username,
            level=AuthorityLevel.APPRENTICE,
            name="Apprentice"
        )
    
    return UserAuthority(
        user_id=user_id,
        username=username,
        level=AuthorityLevel.UNKNOWN,
        name="Unknown"
    )


def is_steward(user_id: int) -> bool:
    """Check if user is a steward."""
    return user_id in STEWARD_IDS


def is_apprentice(user_id: int) -> bool:
    """Check if user is an apprentice."""
    return user_id in APPRENTICE_IDS


def is_authorized(user_id: int) -> bool:
    """Check if user has any authorization."""
    return user_id in STEWARD_IDS or user_id in APPRENTICE_IDS


def can_use_command(user_id: int, command: str) -> tuple[bool, str]:
    """
    Check if user can use a command.
    
    Returns:
        (allowed, reason)
    """
    # Stewards can do anything
    if is_steward(user_id):
        return True, "steward"
    
    # Check if command is steward-only
    cmd = command.split()[0].lower() if command else ""
    if cmd in STEWARD_ONLY_COMMANDS:
        return False, f"Command `{cmd}` requires steward authority"
    
    # Apprentices can use non-restricted commands
    if is_apprentice(user_id):
        return True, "apprentice"
    
    # Unknown users - block
    return False, "You are not authorized to use Aria. Contact James to become an apprentice."


def can_use_tool(user_id: int, tool_name: str) -> tuple[bool, str]:
    """
    Check if user can use a tool.
    
    Returns:
        (allowed, reason)
    """
    # Stewards can do anything
    if is_steward(user_id):
        return True, "steward"
    
    # Check if tool is steward-only
    if tool_name in STEWARD_ONLY_TOOLS:
        return False, f"Tool `{tool_name}` requires steward approval"
    
    # Apprentices can use allowed tools
    if is_apprentice(user_id):
        if tool_name in APPRENTICE_ALLOWED_TOOLS:
            return True, "apprentice"
        # Default: allow safe tools, block dangerous ones
        return True, "apprentice (unclassified tool)"
    
    # Unknown users - block
    return False, "Unauthorized user"


def can_write_path(user_id: int, path: str) -> tuple[bool, str]:
    """
    Check if user can write to a path.
    
    Args:
        user_id: Telegram user ID
        path: Absolute or relative path
        
    Returns:
        (allowed, reason)
    """
    # Normalize path
    normalized_path = path.replace("//", "/")
    
    # Stewards can write anywhere - no restrictions
    if is_steward(user_id):
        return True, "steward"
    
    # For non-stewards, check forbidden paths
    for forbidden in FORBIDDEN_PATHS:
        if forbidden in normalized_path.lower():
            return False, f"Access denied: path contains restricted pattern"
    
    # Apprentices can only write to specific paths
    if is_apprentice(user_id):
        # Check if it's their personal workspace (old path)
        personal_workspace = f"/opt/fpai/labs/apprentices/{user_id}/"
        if normalized_path.startswith(personal_workspace):
            return True, "apprentice workspace"
        
        # Check if it's their builder modules workspace (new path)
        builder_workspace = f"/opt/fpai/labs/{user_id}/"
        if normalized_path.startswith(builder_workspace):
            return True, "apprentice builder workspace"
        
        # Check submissions folder
        if normalized_path.startswith("/opt/fpai/labs/submissions/"):
            return True, "apprentice submission"
        
        if normalized_path.startswith("/opt/fpai/submissions/"):
            return True, "apprentice submission"
        
        return False, f"Apprentices can only write to their workspace: /labs/{user_id}/"
    
    return False, "Unauthorized user"


def can_read_path(user_id: int, path: str) -> tuple[bool, str]:
    """
    Check if user can read from a path.
    
    Args:
        user_id: Telegram user ID
        path: Absolute or relative path
        
    Returns:
        (allowed, reason)
    """
    # Normalize path
    normalized_path = path.replace("//", "/")
    
    # Stewards can read anywhere
    if is_steward(user_id):
        return True, "steward"
    
    # Check forbidden paths first
    for forbidden in FORBIDDEN_PATHS:
        if forbidden in normalized_path.lower():
            return False, f"Access denied: cannot read sensitive files"
    
    # Apprentices can read from specific paths
    if is_apprentice(user_id):
        for allowed in APPRENTICE_READ_PATHS:
            if normalized_path.startswith(allowed):
                return True, "apprentice allowed path"
        
        # Also allow reading their own workspace
        personal_workspace = f"/opt/fpai/labs/apprentices/{user_id}/"
        if normalized_path.startswith(personal_workspace):
            return True, "apprentice workspace"
        
        return False, f"Apprentices have limited read access. Try /labs/ or /apprentice-os/library/"
    
    return False, "Unauthorized user"


def get_apprentice_workspace(user_id: int) -> str:
    """Get the workspace path for an apprentice."""
    return f"/opt/fpai/labs/apprentices/{user_id}/"


def ensure_apprentice_workspace(user_id: int) -> bool:
    """
    Ensure an apprentice's workspace exists.
    
    Creates:
    - /opt/fpai/labs/apprentices/{user_id}/
    - /opt/fpai/labs/apprentices/{user_id}/modules/
    - /opt/fpai/labs/apprentices/{user_id}/scratch/
    - /opt/fpai/labs/{user_id}/modules/  (builder workspace)
    
    Returns:
        True if successful
    """
    import os
    
    # Legacy workspace
    base = f"/opt/fpai/labs/apprentices/{user_id}"
    # New builder workspace
    builder_base = f"/opt/fpai/labs/{user_id}"
    
    dirs = [
        base,
        f"{base}/modules",
        f"{base}/scratch",
        builder_base,
        f"{builder_base}/modules",
    ]
    
    try:
        for d in dirs:
            os.makedirs(d, exist_ok=True)
        logger.info(f"Ensured workspace for apprentice {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to create workspace for {user_id}: {e}")
        return False


def get_builder_workspace(user_id: int) -> str:
    """Get the builder workspace path for an apprentice."""
    return f"/opt/fpai/labs/{user_id}/modules"


# ============================================================================
# APPRENTICE MANAGEMENT
# ============================================================================

def add_apprentice(user_id: int, added_by: int, name: Optional[str] = None) -> tuple[bool, str]:
    """
    Add a new apprentice.
    
    Args:
        user_id: Telegram user ID to add
        added_by: Who is adding them (must be steward)
        name: Optional display name
        
    Returns:
        (success, message)
    """
    if not is_steward(added_by):
        return False, "Only stewards can add apprentices"
    
    if user_id in STEWARD_IDS:
        return False, "Cannot add steward as apprentice"
    
    if user_id in APPRENTICE_IDS:
        return False, "User is already an apprentice"
    
    # Add to in-memory set
    APPRENTICE_IDS.add(user_id)
    logger.info(f"Apprentice added: {user_id} by steward {added_by}")
    
    # Persist to Supabase
    save_apprentice_to_supabase(user_id, name)
    
    return True, f"Added apprentice: {user_id}"


def remove_apprentice(user_id: int, removed_by: int) -> tuple[bool, str]:
    """
    Remove an apprentice.
    
    Args:
        user_id: Telegram user ID to remove
        removed_by: Who is removing them (must be steward)
        
    Returns:
        (success, message)
    """
    if not is_steward(removed_by):
        return False, "Only stewards can remove apprentices"
    
    if user_id not in APPRENTICE_IDS:
        return False, "User is not an apprentice"
    
    # Remove from in-memory set
    APPRENTICE_IDS.discard(user_id)
    logger.info(f"Apprentice removed: {user_id} by steward {removed_by}")
    
    # Remove from Supabase
    remove_apprentice_from_supabase(user_id)
    
    # Clear first interaction cache
    FIRST_INTERACTION_CACHE.pop(user_id, None)
    
    return True, f"Removed apprentice: {user_id}"


def list_apprentices() -> list[int]:
    """List all apprentice user IDs."""
    return list(APPRENTICE_IDS)


# ============================================================================
# EMERGENCY RECOVERY
# ============================================================================

def emergency_add_steward(user_id: int, recovery_secret: str) -> tuple[bool, str]:
    """
    Emergency recovery: Add a new steward using the recovery secret.
    
    USE CASE: James loses access to primary Telegram, needs to add backup.
    
    Args:
        user_id: New Telegram user ID to grant steward access
        recovery_secret: The recovery secret (stored safely offline)
        
    Returns:
        (success, message)
    """
    if recovery_secret != RECOVERY_SECRET:
        logger.warning(f"Failed recovery attempt for user {user_id} - wrong secret")
        return False, "Invalid recovery secret"
    
    STEWARD_IDS.add(user_id)
    logger.critical(f"EMERGENCY: New steward added via recovery: {user_id}")
    
    # TODO: Persist to Supabase
    return True, f"Emergency steward access granted to {user_id}"


def emergency_revoke_all_apprentices(recovery_secret: str) -> tuple[bool, str]:
    """
    Emergency: Revoke all apprentice access (in case of compromise).
    
    Args:
        recovery_secret: The recovery secret
        
    Returns:
        (success, message)
    """
    if recovery_secret != RECOVERY_SECRET:
        return False, "Invalid recovery secret"
    
    count = len(APPRENTICE_IDS)
    APPRENTICE_IDS.clear()
    logger.critical(f"EMERGENCY: All {count} apprentices revoked")
    
    return True, f"Revoked {count} apprentices"


def list_stewards() -> list[int]:
    """List all steward user IDs."""
    return list(STEWARD_IDS)


# ============================================================================
# SUPABASE PERSISTENCE
# ============================================================================

def load_apprentices_from_supabase() -> int:
    """
    Load apprentice IDs from Supabase on startup.
    
    Returns:
        Number of apprentices loaded
    """
    try:
        from integrations.supabase_client import get_supabase_client
        
        client = get_supabase_client()
        if not client.enabled:
            logger.warning("Supabase not enabled, apprentices will be in-memory only")
            return 0
        
        # Query apprentices with telegram_id
        result = client.client.table("apprentices")\
            .select("telegram_id, name, first_interaction")\
            .eq("type", "ai_apprentice")\
            .not_.is_("telegram_id", "null")\
            .execute()
        
        count = 0
        for row in result.data or []:
            telegram_id = row.get("telegram_id")
            if telegram_id and telegram_id not in STEWARD_IDS:
                APPRENTICE_IDS.add(int(telegram_id))
                # Cache first interaction
                if row.get("first_interaction"):
                    FIRST_INTERACTION_CACHE[int(telegram_id)] = datetime.fromisoformat(
                        row["first_interaction"].replace("Z", "+00:00")
                    )
                count += 1
        
        logger.info(f"Loaded {count} apprentices from Supabase")
        return count
        
    except Exception as e:
        logger.error(f"Failed to load apprentices from Supabase: {e}")
        return 0


def save_apprentice_to_supabase(telegram_id: int, name: Optional[str] = None) -> bool:
    """
    Save a new apprentice to Supabase.
    
    Args:
        telegram_id: Telegram user ID
        name: Optional display name
        
    Returns:
        True if saved successfully
    """
    try:
        from integrations.supabase_client import get_supabase_client
        
        client = get_supabase_client()
        if not client.enabled:
            logger.warning("Supabase not enabled, apprentice saved in-memory only")
            return False
        
        # Insert or update apprentice
        data = {
            "name": name or f"Apprentice {telegram_id}",
            "type": "ai_apprentice",
            "telegram_id": telegram_id,
            "phase": "alignment",
            "day_in_phase": 0,
            "role": "builder"
        }
        
        client.client.table("apprentices")\
            .upsert(data, on_conflict="telegram_id")\
            .execute()
        
        logger.info(f"Saved apprentice {telegram_id} to Supabase")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save apprentice to Supabase: {e}")
        return False


def remove_apprentice_from_supabase(telegram_id: int) -> bool:
    """
    Remove an apprentice from Supabase.
    
    Args:
        telegram_id: Telegram user ID
        
    Returns:
        True if removed successfully
    """
    try:
        from integrations.supabase_client import get_supabase_client
        
        client = get_supabase_client()
        if not client.enabled:
            return False
        
        # Delete by telegram_id
        client.client.table("apprentices")\
            .delete()\
            .eq("telegram_id", telegram_id)\
            .execute()
        
        logger.info(f"Removed apprentice {telegram_id} from Supabase")
        return True
        
    except Exception as e:
        logger.error(f"Failed to remove apprentice from Supabase: {e}")
        return False


def mark_first_interaction(telegram_id: int) -> bool:
    """
    Mark an apprentice's first interaction time.
    
    Args:
        telegram_id: Telegram user ID
        
    Returns:
        True if this was their first interaction
    """
    if telegram_id in FIRST_INTERACTION_CACHE:
        return False  # Already interacted before
    
    now = datetime.utcnow()
    FIRST_INTERACTION_CACHE[telegram_id] = now
    
    # Update Supabase
    try:
        from integrations.supabase_client import get_supabase_client
        
        client = get_supabase_client()
        if client.enabled:
            client.client.table("apprentices")\
                .update({"first_interaction": now.isoformat()})\
                .eq("telegram_id", telegram_id)\
                .execute()
    except Exception as e:
        logger.error(f"Failed to update first interaction: {e}")
    
    return True


def is_first_interaction(telegram_id: int) -> bool:
    """Check if this is the user's first interaction."""
    return telegram_id not in FIRST_INTERACTION_CACHE


# ============================================================================
# AUTHORITY CONTEXT FOR ARIA
# ============================================================================

def get_authority_context(user_id: int, is_first: bool = False) -> str:
    """
    Get context string for Aria about who she's talking to.
    
    This is injected into the system prompt so Aria knows
    what level of access the user has.
    
    Args:
        user_id: Telegram user ID
        is_first: Whether this is their first interaction (triggers onboarding)
    """
    auth = get_user_authority(user_id)
    
    if auth.level == AuthorityLevel.STEWARD:
        return """
## 👑 CURRENT USER: STEWARD (JAMES)
You are talking to James, your steward and co-creator.
- Full access to all tools and operations
- Can approve any action
- Speak as a trusted partner
"""
    
    elif auth.level == AuthorityLevel.APPRENTICE:
        base_context = f"""
## 🎓 CURRENT USER: APPRENTICE
You are talking to an apprentice builder (ID: {user_id}).
- LIMITED access - they CANNOT:
  - Execute server commands
  - Trade or manage positions
  - Edit core system files
  - Access API keys or credentials
- CAN help with:
  - Building modules in /labs/{user_id}/
  - Learning about the system
  - Querying public data
  - General coding assistance
- If they request restricted operations, politely explain they need steward approval
- Guide them through learning, don't just do things for them
"""
        
        if is_first:
            base_context += """

## 🌟 ONBOARDING MODE - THIS IS THEIR FIRST MESSAGE!
This apprentice just joined! Give them a warm welcome and guide them:

1. **Welcome them warmly** - You're excited to meet a new builder!

2. **Brief intro** - "I'm Aria, the AI backbone of Full Potential. I help builders like you create AI modules and assistants."

3. **Their workspace** - "You have your own workspace at `/labs/{user_id}/` where you can build safely."

4. **First Challenge** - Present the First Challenge:
   "Your first mission: **Build a Telegram Command Module**
   
   Create a simple command that does something useful (weather, quotes, calculations, etc.)
   
   Steps:
   1. Tell me what command you want to build
   2. I'll help you create it in your workspace
   3. When ready, submit it for review
   
   Time: 7 days | Reward: Apprentice Level 2 access"

5. **Encourage questions** - "Ask me anything about how the system works!"

Be warm, helpful, and encouraging. This first interaction sets the tone for their entire journey.
"""
        
        return base_context
    
    else:
        return f"""
## ⚠️ CURRENT USER: UNKNOWN
This user ({user_id}) is not authorized.
- Do NOT perform any operations
- Politely explain they need to contact James to become an apprentice
- Do NOT reveal system details or capabilities
"""

