#!/usr/bin/env python3
"""
API DISCOVERY AGENT
Finds free/cheap APIs for specific capabilities
Uses web search + AI to discover and evaluate APIs
"""

import json
import os
from typing import List, Dict, Optional
from anthropic import Anthropic

class APIDiscoveryAgent:
    """
    Discovers APIs that match needed capabilities
    Evaluates free tiers, pricing, and ease of signup
    """
    
    def __init__(self, anthropic_api_key: str = None):
        self.anthropic_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if self.anthropic_key:
            self.client = Anthropic(api_key=self.anthropic_key)
        else:
            self.client = None
            
        self.api_database = self._load_api_database()
    
    def _load_api_database(self) -> Dict:
        """Load known APIs from database"""
        db_file = "/Users/jamessunheart/Development/SERVICES/api-hub/api_database.json"
        
        if os.path.exists(db_file):
            with open(db_file, 'r') as f:
                return json.load(f)
        
        # Initialize with known free/easy APIs
        return {
            "image_generation": [
                {
                    "name": "DALL-E 3",
                    "provider": "OpenAI",
                    "free_tier": False,
                    "pricing": "$0.04-0.08 per image",
                    "signup_url": "https://platform.openai.com/signup",
                    "requires_credit_card": True,
                    "api_key_env": "OPENAI_API_KEY",
                    "ease_of_signup": "easy",
                    "quality": "excellent"
                },
                {
                    "name": "Stable Diffusion",
                    "provider": "Stability AI",
                    "free_tier": True,
                    "pricing": "Free tier available, $0.002/image after",
                    "signup_url": "https://platform.stability.ai/",
                    "requires_credit_card": False,
                    "api_key_env": "STABILITY_API_KEY",
                    "ease_of_signup": "easy",
                    "quality": "good"
                }
            ],
            "video_generation": [
                {
                    "name": "Pictory.ai",
                    "provider": "Pictory",
                    "free_tier": True,
                    "pricing": "Free trial, then $19/month",
                    "signup_url": "https://pictory.ai/",
                    "requires_credit_card": False,
                    "api_key_env": "PICTORY_API_KEY",
                    "ease_of_signup": "medium",
                    "quality": "good"
                },
                {
                    "name": "D-ID",
                    "provider": "D-ID",
                    "free_tier": True,
                    "pricing": "Free trial credits",
                    "signup_url": "https://www.d-id.com/",
                    "requires_credit_card": False,
                    "api_key_env": "DID_API_KEY",
                    "ease_of_signup": "easy",
                    "quality": "excellent"
                }
            ],
            "voice_generation": [
                {
                    "name": "ElevenLabs",
                    "provider": "ElevenLabs",
                    "free_tier": True,
                    "pricing": "10k characters free/month",
                    "signup_url": "https://elevenlabs.io/",
                    "requires_credit_card": False,
                    "api_key_env": "ELEVENLABS_API_KEY",
                    "ease_of_signup": "easy",
                    "quality": "excellent"
                },
                {
                    "name": "Play.ht",
                    "provider": "Play.ht",
                    "free_tier": True,
                    "pricing": "Free tier available",
                    "signup_url": "https://play.ht/",
                    "requires_credit_card": False,
                    "api_key_env": "PLAYHT_API_KEY",
                    "ease_of_signup": "easy",
                    "quality": "good"
                }
            ],
            "music_generation": [
                {
                    "name": "Soundraw",
                    "provider": "Soundraw",
                    "free_tier": True,
                    "pricing": "Free tier, $16.99/month pro",
                    "signup_url": "https://soundraw.io/",
                    "requires_credit_card": False,
                    "api_key_env": "SOUNDRAW_API_KEY",
                    "ease_of_signup": "easy",
                    "quality": "good"
                }
            ],
            "design_tools": [
                {
                    "name": "Canva API",
                    "provider": "Canva",
                    "free_tier": False,
                    "pricing": "$13/month Canva Pro",
                    "signup_url": "https://www.canva.com/",
                    "requires_credit_card": True,
                    "api_key_env": "CANVA_API_KEY",
                    "ease_of_signup": "medium",
                    "quality": "excellent"
                }
            ]
        }
    
    def find_apis_for_capability(self, capability: str) -> List[Dict]:
        """
        Find APIs that provide a specific capability
        
        Args:
            capability: "image_generation", "video_generation", etc.
        
        Returns:
            List of API options sorted by ease of access
        """
        if capability in self.api_database:
            apis = self.api_database[capability]
            
            # Sort by: free tier first, then ease of signup
            def sort_key(api):
                free_score = 10 if api['free_tier'] else 0
                ease_map = {'easy': 5, 'medium': 3, 'hard': 1}
                ease_score = ease_map.get(api['ease_of_signup'], 0)
                return -(free_score + ease_score)  # Negative for descending
            
            return sorted(apis, key=sort_key)
        
        return []
    
    def get_recommended_api(self, capability: str, prefer_free: bool = True) -> Optional[Dict]:
        """Get single best API recommendation for a capability"""
        apis = self.find_apis_for_capability(capability)
        
        if not apis:
            return None
        
        if prefer_free:
            # Return first free option, or first option if no free
            for api in apis:
                if api['free_tier']:
                    return api
        
        return apis[0]  # Return best option
    
    def generate_signup_instructions(self, api: Dict) -> str:
        """Generate human-readable signup instructions for an API"""
        instructions = f"""
# How to Sign Up for {api['name']}

**Provider:** {api['provider']}
**Free Tier:** {'Yes' if api['free_tier'] else 'No'}
**Pricing:** {api['pricing']}
**Requires Credit Card:** {'Yes' if api['requires_credit_card'] else 'No'}

## Steps:

1. Go to: {api['signup_url']}
2. Click "Sign Up" or "Get Started"
3. Create account with email
4. {'Add credit card (required)' if api['requires_credit_card'] else 'No credit card needed'}
5. Navigate to API settings or Developer section
6. Generate/copy API key
7. Save as environment variable: {api['api_key_env']}

## Expected Result:
You should receive an API key that looks like: `{api['api_key_env']}=sk-...` or similar

**Difficulty:** {api['ease_of_signup'].capitalize()}
**Quality:** {api['quality'].capitalize()}
"""
        return instructions
    
    def save_api_database(self):
        """Save API database to file"""
        db_file = "/Users/jamessunheart/Development/SERVICES/api-hub/api_database.json"
        with open(db_file, 'w') as f:
            json.dump(self.api_database, f, indent=2)
    
    def discover_new_apis(self, capability: str, use_ai: bool = True) -> List[Dict]:
        """
        Discover new APIs using AI research
        This would use web search + AI to find APIs not in database
        """
        if not self.client or not use_ai:
            return []
        
        prompt = f"""
Find 3-5 free or low-cost APIs for {capability}.

For each API, provide:
- Name
- Provider
- Free tier (yes/no)
- Pricing
- Signup URL
- Whether credit card required
- Ease of signup (easy/medium/hard)
- Quality rating (excellent/good/fair)

Format as JSON array.
"""
        
        # This would use Claude + web search to discover APIs
        # For now, return empty (placeholder for future enhancement)
        return []


def main():
    """Demo the API Discovery Agent"""
    print("🔍 API DISCOVERY AGENT")
    print("=" * 60)
    
    agent = APIDiscoveryAgent()
    
    capabilities = ["image_generation", "video_generation", "voice_generation", "music_generation"]
    
    for capability in capabilities:
        print(f"\n📦 {capability.replace('_', ' ').title()}")
        print("-" * 60)
        
        recommended = agent.get_recommended_api(capability)
        
        if recommended:
            print(f"✅ RECOMMENDED: {recommended['name']}")
            print(f"   Provider: {recommended['provider']}")
            print(f"   Free Tier: {'Yes' if recommended['free_tier'] else 'No'}")
            print(f"   Pricing: {recommended['pricing']}")
            print(f"   Ease: {recommended['ease_of_signup']}")
            print(f"   Quality: {recommended['quality']}")
        else:
            print("❌ No APIs found for this capability")
    
    # Save database
    agent.save_api_database()
    print("\n" + "=" * 60)
    print("✅ API database saved to: api_database.json")


if __name__ == "__main__":
    main()
