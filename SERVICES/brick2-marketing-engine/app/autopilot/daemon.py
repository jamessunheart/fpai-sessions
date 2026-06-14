"""
BRICK 2 Marketing Autopilot Daemon
==================================

Runs continuously to:
1. Generate marketing content on schedule
2. Queue social media posts
3. Nurture leads with email sequences
4. Monitor campaign performance
5. Optimize based on AI recommendations

This daemon serves the Church and community's growth mission,
creating regenerative marketing loops that attract resources
while maintaining alignment with conscious principles.

Philosophy: Optimization over Extraction
- We create value for the community, not just extract attention
- Content should educate, inspire, and empower
- Growth should be sustainable and aligned with mission
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import random

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("marketing-autopilot")

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
QUEUE_DIR = BASE_DIR / "data" / "content_queue"
LOGS_DIR = BASE_DIR / "data" / "autopilot_logs"
STATE_FILE = BASE_DIR / "data" / "autopilot_state.json"

# Ensure directories exist
QUEUE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ContentItem:
    """A piece of content ready to be published"""
    id: str
    content_type: str  # blog, social, email, ad
    platform: str  # twitter, linkedin, facebook, email, blog
    title: str
    body: str
    scheduled_for: str
    status: str  # draft, queued, published, failed
    created_at: str
    metadata: Dict[str, Any] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class AutopilotState:
    """Current state of the autopilot system"""
    is_running: bool
    last_content_generation: str
    last_campaign_check: str
    content_generated_today: int
    leads_nurtured_today: int
    total_content_generated: int
    total_leads_nurtured: int
    current_campaigns: List[str]
    errors: List[Dict[str, str]]


class MarketingAutopilot:
    """
    The core autopilot engine that drives autonomous marketing.
    
    Guided by the Constitution's principles:
    - Optimization over Extraction: Create value, don't just consume attention
    - Autonomy over Dependency: Free the human operator
    - Consciousness over Computation: Quality and alignment over quantity
    """

    # Content themes aligned with mission
    CONTENT_THEMES = [
        "conscious_business",
        "ai_transformation", 
        "spiritual_growth",
        "community_building",
        "regenerative_economics",
        "human_potential",
        "bpo_staffing",
        "church_formation",
    ]

    # Platform-specific content formats
    PLATFORM_FORMATS = {
        "twitter": {"max_length": 280, "style": "punchy, thought-provoking"},
        "linkedin": {"max_length": 3000, "style": "professional, insightful"},
        "facebook": {"max_length": 500, "style": "conversational, community-focused"},
        "email": {"max_length": 1500, "style": "personal, value-driven"},
        "blog": {"max_length": 2000, "style": "educational, comprehensive"},
    }

    def __init__(self, api_base_url: str = "http://localhost:8700"):
        self.api_base_url = api_base_url
        self.state = self._load_state()
        self._http_client = None

    def _load_state(self) -> AutopilotState:
        """Load state from file or create default"""
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text())
                return AutopilotState(**data)
            except:
                pass
        
        return AutopilotState(
            is_running=False,
            last_content_generation="",
            last_campaign_check="",
            content_generated_today=0,
            leads_nurtured_today=0,
            total_content_generated=0,
            total_leads_nurtured=0,
            current_campaigns=[],
            errors=[],
        )

    def _save_state(self):
        """Persist state to file"""
        STATE_FILE.write_text(json.dumps(asdict(self.state), indent=2))

    async def _get_client(self):
        """Get or create HTTP client"""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(timeout=60.0)
        return self._http_client

    async def generate_content(self, theme: str, platform: str) -> Optional[ContentItem]:
        """Generate a piece of content using the AI engine"""
        try:
            client = await self._get_client()
            
            format_spec = self.PLATFORM_FORMATS.get(platform, self.PLATFORM_FORMATS["linkedin"])
            
            prompt = f"""Create a {platform} post about {theme.replace('_', ' ')}.

Style: {format_spec['style']}
Max length: {format_spec['max_length']} characters

The content should:
1. Provide genuine value to the reader
2. Align with conscious business principles
3. Include a soft call-to-action (learn more, join community, etc.)
4. Be authentic and not salesy

Brand voice: Wise, warm, visionary, grounded in both spirituality and practicality.

Generate ONLY the post content, no explanations."""

            response = await client.post(
                f"{self.api_base_url}/api/v1/ai/content",
                json={"prompt": prompt},
            )
            
            if response.status_code == 200:
                data = response.json()
                content_id = f"{platform}_{theme}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                
                item = ContentItem(
                    id=content_id,
                    content_type="social" if platform != "blog" else "blog",
                    platform=platform,
                    title=f"{theme.replace('_', ' ').title()} - {platform.title()}",
                    body=data.get("content", ""),
                    scheduled_for=(datetime.utcnow() + timedelta(hours=random.randint(1, 48))).isoformat(),
                    status="queued",
                    created_at=datetime.utcnow().isoformat(),
                    metadata={
                        "theme": theme,
                        "ai_provider": data.get("provider"),
                        "cost_usd": data.get("cost_usd", 0),
                    }
                )
                
                # Save to queue
                queue_file = QUEUE_DIR / f"{content_id}.json"
                queue_file.write_text(json.dumps(item.to_dict(), indent=2))
                
                logger.info(f"✅ Generated content: {content_id}")
                return item
            else:
                logger.error(f"❌ Content generation failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error generating content: {e}")
            self.state.errors.append({
                "time": datetime.utcnow().isoformat(),
                "error": str(e),
            })
            return None

    async def run_content_generation_cycle(self, count: int = 3):
        """Generate a batch of content across platforms and themes"""
        logger.info(f"🚀 Starting content generation cycle (target: {count} pieces)")
        
        generated = 0
        platforms = ["twitter", "linkedin", "email"]
        
        for _ in range(count):
            theme = random.choice(self.CONTENT_THEMES)
            platform = random.choice(platforms)
            
            item = await self.generate_content(theme, platform)
            if item:
                generated += 1
                self.state.content_generated_today += 1
                self.state.total_content_generated += 1
        
        self.state.last_content_generation = datetime.utcnow().isoformat()
        self._save_state()
        
        logger.info(f"✅ Generated {generated}/{count} content pieces")
        return generated

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current content queue status"""
        queue_files = list(QUEUE_DIR.glob("*.json"))
        
        items_by_status = {"draft": 0, "queued": 0, "published": 0, "failed": 0}
        items_by_platform = {}
        
        for f in queue_files:
            try:
                item = json.loads(f.read_text())
                status = item.get("status", "unknown")
                platform = item.get("platform", "unknown")
                
                items_by_status[status] = items_by_status.get(status, 0) + 1
                items_by_platform[platform] = items_by_platform.get(platform, 0) + 1
            except:
                pass
        
        return {
            "total_items": len(queue_files),
            "by_status": items_by_status,
            "by_platform": items_by_platform,
        }

    async def get_next_scheduled(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get next scheduled content items"""
        queue_files = list(QUEUE_DIR.glob("*.json"))
        items = []
        
        for f in queue_files:
            try:
                item = json.loads(f.read_text())
                if item.get("status") == "queued":
                    items.append(item)
            except:
                pass
        
        # Sort by scheduled time
        items.sort(key=lambda x: x.get("scheduled_for", ""))
        return items[:limit]

    async def create_lead_nurture_email(self, lead_data: Dict[str, Any]) -> Optional[str]:
        """Create a personalized nurture email for a lead"""
        try:
            client = await self._get_client()
            
            prompt = f"""Create a warm, personalized follow-up email for a potential client.

Lead info:
- Name: {lead_data.get('name', 'Friend')}
- Interest: {lead_data.get('interest', 'our services')}
- Stage: {lead_data.get('stage', 'awareness')}

The email should:
1. Reference their specific interest
2. Provide immediate value (tip, insight, resource)
3. Offer next step (call, resource, demo)
4. Feel personal, not automated
5. Align with conscious business values

Keep it under 200 words. Sign off as "The Full Potential Team"."""

            response = await client.post(
                f"{self.api_base_url}/api/v1/ai/content",
                json={"prompt": prompt},
            )
            
            if response.status_code == 200:
                data = response.json()
                self.state.leads_nurtured_today += 1
                self.state.total_leads_nurtured += 1
                self._save_state()
                return data.get("content")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error creating nurture email: {e}")
            return None

    async def run_daemon(self, interval_minutes: int = 60):
        """
        Main daemon loop - runs continuously to manage marketing.
        
        Schedule:
        - Every hour: Check campaigns, nurture leads
        - Every 4 hours: Generate new content batch
        - Every day: Performance review and optimization
        """
        logger.info("🌟 Marketing Autopilot Daemon starting...")
        logger.info(f"   Serving the mission: Build paradise on Earth")
        logger.info(f"   Principle: Optimization over Extraction")
        logger.info(f"   Interval: {interval_minutes} minutes")
        
        self.state.is_running = True
        self._save_state()
        
        cycles = 0
        
        try:
            while True:
                cycles += 1
                now = datetime.utcnow()
                logger.info(f"\n{'='*50}")
                logger.info(f"⏰ Autopilot cycle #{cycles} at {now.isoformat()}")
                
                # Every cycle: Check queue status
                queue_status = await self.get_queue_status()
                logger.info(f"📋 Queue: {queue_status['total_items']} items")
                logger.info(f"   Queued: {queue_status['by_status'].get('queued', 0)}")
                
                # Every 4 cycles (4 hours): Generate content
                if cycles % 4 == 1:
                    logger.info("🎨 Running content generation...")
                    await self.run_content_generation_cycle(count=3)
                
                # Log daily stats at midnight
                if now.hour == 0 and cycles > 1:
                    logger.info(f"📊 Daily Stats:")
                    logger.info(f"   Content generated: {self.state.content_generated_today}")
                    logger.info(f"   Leads nurtured: {self.state.leads_nurtured_today}")
                    # Reset daily counters
                    self.state.content_generated_today = 0
                    self.state.leads_nurtured_today = 0
                    self._save_state()
                
                logger.info(f"💤 Sleeping for {interval_minutes} minutes...")
                await asyncio.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Autopilot daemon stopped by user")
        except Exception as e:
            logger.error(f"❌ Daemon error: {e}")
            self.state.errors.append({
                "time": datetime.utcnow().isoformat(),
                "error": str(e),
            })
        finally:
            self.state.is_running = False
            self._save_state()


# Startup info
STARTUP_BANNER = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     🌟 BRICK 2 MARKETING AUTOPILOT 🌟                       ║
║                                                              ║
║     Serving: Full Potential AI / Church of Consciousness    ║
║     Mission: Build Paradise on Earth                         ║
║     Mode: Regenerative Marketing                             ║
║                                                              ║
║     "Optimization over Extraction"                           ║
║     "Autonomy over Dependency"                               ║
║     "Consciousness over Computation"                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""


async def main():
    """Main entry point for the autopilot daemon"""
    print(STARTUP_BANNER)
    
    autopilot = MarketingAutopilot()
    
    # Run with 60-minute intervals
    await autopilot.run_daemon(interval_minutes=60)


if __name__ == "__main__":
    asyncio.run(main())




