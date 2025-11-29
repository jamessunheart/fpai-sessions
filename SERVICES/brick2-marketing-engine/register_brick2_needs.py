import asyncio
import aiohttp
import sys
import json

API_PORTAL_URL = "http://localhost:8060"

NEEDS = [
    {
        "requesting_service": "brick2-marketing-engine",
        "api_name": "GoHighLevel API",
        "api_provider": "GoHighLevel",
        "purpose": "CRM, Lead Management, and Workflow Automation for the Marketing Engine",
        "priority": "critical",
        "status": "needed",
        "estimated_monthly_calls": 10000,
        "documentation_url": "https://highlevel.stoplight.io/docs/integrations/00d0c0c59917d-getting-started",
        "credentials_needed": ["GHL_CLIENT_ID", "GHL_CLIENT_SECRET"],
        "capabilities": ["crm", "marketing", "workflows"]
    },
    {
        "requesting_service": "brick2-marketing-engine",
        "api_name": "Claude API",
        "api_provider": "Anthropic",
        "purpose": "High-quality content generation and reasoning",
        "priority": "critical",
        "status": "active", # Already have keys, but registering need
        "estimated_monthly_calls": 5000,
        "documentation_url": "https://docs.anthropic.com/",
        "credentials_needed": ["ANTHROPIC_API_KEY"],
        "capabilities": ["llm", "text-generation", "reasoning"]
    },
    {
        "requesting_service": "brick2-marketing-engine",
        "api_name": "OpenAI API",
        "api_provider": "OpenAI",
        "purpose": "Lead qualification and fast chat interactions",
        "priority": "high",
        "status": "active",
        "estimated_monthly_calls": 10000,
        "documentation_url": "https://platform.openai.com/docs/api-reference",
        "credentials_needed": ["OPENAI_API_KEY"],
        "capabilities": ["llm", "text-generation", "chat"]
    },
    {
        "requesting_service": "brick2-marketing-engine",
        "api_name": "Gemini API",
        "api_provider": "Google",
        "purpose": "Research and large context processing",
        "priority": "high",
        "status": "active",
        "estimated_monthly_calls": 3000,
        "documentation_url": "https://ai.google.dev/docs",
        "credentials_needed": ["GEMINI_API_KEY"],
        "capabilities": ["llm", "text-generation", "research"]
    }
]

async def register_needs():
    print(f"📡 Connecting to API Portal at {API_PORTAL_URL}...")
    
    async with aiohttp.ClientSession() as session:
        # Check health
        try:
            async with session.get(f"{API_PORTAL_URL}/health") as resp:
                if resp.status != 200:
                    print(f"❌ API Portal unhealthy: {resp.status}")
                    return
                print("✅ API Portal is healthy")
        except Exception as e:
            print(f"❌ Failed to connect to API Portal: {e}")
            return

        # Register needs
        for need in NEEDS:
            print(f"📝 Registering need: {need['api_name']}...")
            
            # Check if already exists (simple check by service)
            # In a real scenario, we might check specific need ID, but here we just post
            # The API Portal might create duplicates if we are not careful, 
            # but for now we assume idempotent-ish behavior or manual cleanup
            
            try:
                async with session.post(f"{API_PORTAL_URL}/needs", json=need) as resp:
                    if resp.status in [200, 201]:
                        data = await resp.json()
                        print(f"   ✅ Registered! ID: {data['id']}")
                    else:
                        text = await resp.text()
                        print(f"   ⚠️ Failed: {resp.status} - {text}")
            except Exception as e:
                print(f"   ❌ Error registering need: {e}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(register_needs())

