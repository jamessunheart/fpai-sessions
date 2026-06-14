#!/usr/bin/env python3
"""
API HUB - Central API Key Management
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class APIHub:
    def __init__(self, vault_path: str = None):
        self.vault_path = vault_path or "/Users/jamessunheart/Development/agents/services/api-hub/api_vault.json"
        self.vault = self._load_vault()
        
    def _load_vault(self) -> Dict:
        if os.path.exists(self.vault_path):
            with open(self.vault_path, 'r') as f:
                return json.load(f)
        
        return {
            "apis": {},
            "metadata": {
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
        }
    
    def _save_vault(self):
        self.vault["metadata"]["last_updated"] = datetime.now().isoformat()
        with open(self.vault_path, 'w') as f:
            json.dump(self.vault, f, indent=2)
    
    def add_api_key(self, service: str, api_key: str, metadata: Dict = None):
        self.vault["apis"][service] = {
            "key": api_key,
            "key_preview": api_key[:10] + "..." if len(api_key) > 10 else "***",
            "added_date": datetime.now().isoformat(),
            "status": "active",
            "metadata": metadata or {}
        }
        self._save_vault()
        print(f"✅ Added API key for: {service}")
    
    def get_api_key(self, service: str) -> Optional[str]:
        if service in self.vault["apis"]:
            return self.vault["apis"][service]["key"]
        return None
    
    def has_api(self, service: str) -> bool:
        return service in self.vault["apis"]
    
    def list_apis(self) -> List[Dict]:
        apis = []
        for service, data in self.vault["apis"].items():
            apis.append({
                "service": service,
                "status": data["status"],
                "added_date": data["added_date"],
                "key_preview": data["key_preview"]
            })
        return apis
    
    def get_missing_capabilities(self, needed_capabilities: List[str]) -> List[str]:
        capability_to_service = {
            "image_generation": ["openai", "stability", "midjourney"],
            "video_generation": ["d-id", "pictory", "runway"],
            "voice_generation": ["elevenlabs", "playht"],
            "music_generation": ["soundraw"]
        }
        
        missing = []
        for capability in needed_capabilities:
            services = capability_to_service.get(capability, [])
            has_any = any(self.has_api(svc) for svc in services)
            if not has_any:
                missing.append(capability)
        
        return missing


def main():
    print("🏢 API HUB - Central Management")
    print("=" * 60)
    
    hub = APIHub()
    
    # Add Stripe key
    stripe_key = os.getenv("STRIPE_API_KEY", "YOUR_STRIPE_API_KEY_HERE")
    hub.add_api_key("stripe", stripe_key, {"tier": "live", "usage": "payments"})
    
    print("\n📋 Current APIs in vault:")
    for api in hub.list_apis():
        print(f"  ✅ {api['service']:15s} - {api['key_preview']}")
    
    # Check missing capabilities
    needed = ["image_generation", "video_generation", "voice_generation", "music_generation"]
    missing = hub.get_missing_capabilities(needed)
    
    if missing:
        print(f"\n⚠️  Missing {len(missing)} capabilities:")
        for cap in missing:
            print(f"  ❌ {cap}")
    
    print(f"\n✅ API Hub vault saved to: {hub.vault_path}")


if __name__ == "__main__":
    main()
