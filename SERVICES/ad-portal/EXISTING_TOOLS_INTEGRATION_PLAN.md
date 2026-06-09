# 🔌 Existing Tools Integration Plan

## ✅ WHAT EXISTS & CAN BE USED

### 1. **Image Generation** - 3 OPTIONS AVAILABLE

#### Option A: FI-Art Content Studio ✅ (RECOMMENDED)
**Status**: ✅ Working in FI-Art
**Location**: `FI-Art/server/fpaiIntegration.ts::generateHighFidelityImage()`
**URL**: `http://localhost:8901` (default) or check env `CONTENT_URL`
**Endpoint**: `POST /api/generate`
**Payload**:
```json
{
  "content_type": "social_post",
  "brief": {
    "topic": "image prompt here",
    "generate_image": true
  },
  "platform": "web"
}
```
**Response**: `{ "content": { "image_url": "...", "image_prompt": "..." } }`

**Integration Time**: 1-2 hours
**Steps**:
1. Check if Content Studio is running (port 8901 or env var)
2. Create `app/integrations/content_studio.py` wrapper
3. Call from `app/services/image_generator.py`

---

#### Option B: Direct OpenAI DALL-E ✅
**Status**: ⚠️ API key exists, no wrapper
**Location**: API keys at `/opt/fpai/api_keys.json` (secondary server)
**Key**: `sk-proj-eqU5C27...` (OpenAI key)
**API**: `https://api.openai.com/v1/images/generations`
**Cost**: $0.04-0.08/image

**Integration Time**: 2-3 hours
**Steps**:
1. Create `app/integrations/image_apis.py`
2. Add OpenAI client
3. Call DALL-E API directly

---

#### Option C: Stable Diffusion (Replicate) ⚠️
**Status**: ❌ Need API key
**Location**: Info in `SERVICES/api-hub/api_database.json`
**Cost**: $0.002/image (cheapest)
**API**: Replicate API

**Integration Time**: 2-3 hours (after getting API key)

**Recommendation**: **Use FI-Art Content Studio** (fastest, already working)

---

### 2. **Landing Page Generation** - AI BRAIN CAN DO THIS ✅

**Status**: ✅ Already integrated!
**Location**: `SERVICES/ad-portal/app/services/creative_ai.py` (already uses AI Brain)
**URL**: `http://162.0.208.88:8101` (already configured)
**Endpoint**: `POST /api/generate`

**What AI Brain can do**:
- ✅ Generate HTML (just need right prompt)
- ✅ Already integrated in Ad Portal
- ✅ Already working for ad copy generation

**Integration Time**: 2-3 hours (just prompt engineering)

**Example Prompt**:
```python
prompt = f"""
Generate a complete, conversion-optimized HTML landing page:

OFFER: {offer.name}
PRICE: ${offer.price}
HEADLINE: {creative.headline}
DESCRIPTION: {offer.description}

REQUIREMENTS:
- Complete HTML with inline CSS (use Tailwind CDN)
- Hero section with headline
- Benefits section (3-5 points)
- Pricing section with CTA
- Meta Pixel tracking (pixel_id: {pixel_id})
- Mobile-responsive
- Fast loading

Output complete HTML ready to deploy.
"""
```

**Steps**:
1. Create `app/services/landing_page_generator.py`
2. Use existing `AI_BRAIN_URL` (already configured)
3. Structure prompt for HTML generation
4. Deploy HTML to `/opt/fpai/core/applications/website-ai/frontend/landing-pages/`
5. Return URL

---

### 3. **Auto-Campaign Creation** - ALREADY EXISTS ✅

**Status**: ✅ Fully implemented!
**Location**: `SERVICES/ad-portal/app/integrations/meta.py`

**What exists**:
- ✅ `create_campaign()` - Creates campaign on Meta
- ✅ `create_ad()` - Creates ads from creatives
- ✅ `update_campaign_status()` - Pause/resume
- ✅ Launch endpoint: `POST /api/campaigns/{id}/launch`

**What's missing** (to make it "auto"):
- ⚠️ Auto-targeting logic (currently manual)
- ⚠️ Auto-budget optimization
- ⚠️ One-click "Create & Launch" flow

**Integration Time**: 2-3 hours (add auto-targeting)

**Steps**:
1. Add `auto_targeting()` helper function
2. Add `auto_create_campaign()` method
3. Create endpoint: `POST /api/campaigns/auto-create`

---

## 🎯 RECOMMENDED INTEGRATION ORDER

### Phase 1: Image Generation (1-2 hours)
**Use**: FI-Art Content Studio
**Why**: Already working, fastest path

**Files to create**:
- `app/integrations/content_studio.py` - Wrapper
- `app/services/image_generator.py` - Main service
- `app/api/content.py` - Endpoint

**Code**:
```python
# app/integrations/content_studio.py
async def generate_image(prompt: str) -> str:
    url = os.getenv("CONTENT_STUDIO_URL", "http://localhost:8901")
    response = await client.post(
        f"{url}/api/generate",
        json={
            "content_type": "social_post",
            "brief": {"topic": prompt, "generate_image": True},
            "platform": "web"
        }
    )
    return response.json()["content"]["image_url"]
```

---

### Phase 2: Landing Page Generation (2-3 hours)
**Use**: AI Brain (already integrated!)
**Why**: No new dependencies, just prompt engineering

**Files to create**:
- `app/services/landing_page_generator.py` - Main service
- `app/models/landing_page.py` - Database model
- `app/api/landing_pages.py` - Endpoints

**Code**:
```python
# app/services/landing_page_generator.py
class LandingPageGenerator:
    def __init__(self):
        self.brain_url = settings.AI_BRAIN_URL  # Already configured!
        self.client = httpx.AsyncClient()
    
    async def generate(self, offer, creative, pixel_id):
        prompt = f"""Generate complete HTML landing page..."""
        response = await self.client.post(
            f"{self.brain_url}/api/generate",
            json={"prompt": prompt, "max_tokens": 3000}
        )
        html = response.json()["content"]
        # Deploy to /opt/fpai/.../landing-pages/
        return url
```

---

### Phase 3: Auto-Campaign Creation (2-3 hours)
**Use**: Existing Meta API integration
**Why**: Just add auto-targeting logic

**Files to modify**:
- `app/integrations/meta.py` - Add auto-targeting
- `app/services/auto_campaign.py` - Orchestrator
- `app/api/campaigns.py` - Add auto-create endpoint

**Code**:
```python
# app/integrations/meta.py
def auto_targeting(offer_type: str) -> dict:
    """Auto-generate targeting based on offer type"""
    if offer_type == "coaching":
        return {
            "age_min": 25,
            "age_max": 55,
            "interests": ["personal development", "coaching"],
            "behaviors": ["small_business_owners"]
        }
    # ... more logic
```

---

## 📊 TOTAL TIME TO FULL AUTOMATION

| Phase | Tool | Time | Status |
|-------|------|------|--------|
| Phase 1 | FI-Art Content Studio | 1-2h | ✅ Available |
| Phase 2 | AI Brain | 2-3h | ✅ Already integrated |
| Phase 3 | Meta API (enhance) | 2-3h | ✅ Already integrated |
| **TOTAL** | | **5-8 hours** | vs 18-24h from scratch |

---

## 🔍 WHAT TO CHECK FIRST

### 1. Content Studio Service
```bash
# Check if running
curl http://localhost:8901/api/health
# Or check SERVICE_REGISTRY.md
# Or check brick2-marketing-engine (might be integrated there)
```

### 2. AI Brain HTML Generation
```bash
# Test HTML generation
curl -X POST http://162.0.208.88:8101/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Generate a complete HTML landing page for a coaching offer...",
    "max_tokens": 3000
  }'
```

### 3. Meta API Campaign Creation
```bash
# Already working - test launch endpoint
curl -X POST https://fullpotential.ai/ads/api/campaigns/{id}/launch
```

---

## 💡 BOTTOM LINE

**You have 80% of what you need already built!**

- ✅ Image generation exists (FI-Art Content Studio)
- ✅ HTML generation exists (AI Brain - already integrated!)
- ✅ Campaign creation exists (Meta API - already integrated!)

**Just need to wire them together** (5-8 hours) instead of building from scratch (18-24 hours).

**Next step**: Check Content Studio URL and start Phase 1!







