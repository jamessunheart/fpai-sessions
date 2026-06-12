"""
Domain-specific models for Multi-Cloud Manager
DigitalOcean, Hetzner, Vultr request/response models
"""

from typing import Optional, List, Literal
from pydantic import BaseModel


# ============================================================================
# DIGITALOCEAN MODELS
# ============================================================================

class DOCreateRequest(BaseModel):
    """DigitalOcean droplet creation request"""
    name: str
    region: str = "sfo3"
    size: str = "s-1vcpu-1gb"
    image: str = "ubuntu-22-04-x64"
    ssh_keys: Optional[List[int]] = None
    user_data: Optional[str] = None


# ============================================================================
# HETZNER MODELS
# ============================================================================

class HetznerCreateRequest(BaseModel):
    """Hetzner server creation request"""
    name: str
    region: str = "fsn1"
    size: str = "cpx11"
    image: str = "ubuntu-22.04"
    user_data: Optional[str] = None


# ============================================================================
# VULTR MODELS
# ============================================================================

class VultrCreateRequest(BaseModel):
    """Vultr instance creation request"""
    name: str
    region: str = "sea"
    size: str = "vc2-1c-1gb"
    image: str = "1743"  # Ubuntu 22.04
    user_data: Optional[str] = None


# ============================================================================
# SHARED MODELS
# ============================================================================

class PowerActionRequest(BaseModel):
    """Power action request for any provider"""
    action: Literal["reboot", "power_off", "power_on"]
