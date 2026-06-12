# Content Studio - Quick Start Guide

## 🎯 What We're Building

Transform your Ad Portal into a **complete AI content creation suite**:

```
User Input: "Create ads for my coaching offer"
    ↓
AI Generates:
  ✅ Ad copy (3 variations) - DONE ✅
  ✅ Images (multiple sizes) - NEW 🆕
  ✅ Landing page (HTML) - NEW 🆕
    ↓
Auto-Creates:
  ✅ Meta campaign - NEW 🆕
  ✅ Ad sets with targeting - NEW 🆕
  ✅ Launches ads - NEW 🆕
    ↓
Tracks:
  ✅ Conversions → ROAS → Profit - DONE ✅
    ↓
Auto-Optimizes:
  ✅ Regenerates underperformers - NEW 🆕
```

---

## ✅ What's Already Working

1. **Ad Copy Generation** - `CreativeAIGenerator` generates headlines, primary text, descriptions
2. **Meta Ads Integration** - Can create campaigns, ad sets, ads
3. **Conversion Tracking** - Meta Pixel + Stripe webhooks
4. **Profit Calculation** - ROAS → Profit tracking

---

## 🆕 What We Need to Add

### Phase 1: Image Generation (Start Here)

**Goal**: Generate actual images from the `image_prompt` that `CreativeAIGenerator` creates.

**Options**:
1. **Stable Diffusion** (via Replicate) - **FREE tier available** ✅ Recommended
2. **DALL-E 3** (via OpenAI) - $0.04/image, better quality
3. **FI-Art Service** - Check if it has image generation

**Implementation**:
```python
# New file: app/services/image_generator.py
class ImageGenerator:
    async def generate_for_creative(
        self, 
        creative: Creative,
        variants: List[str] = ["square", "portrait"]
    ) -> List[GeneratedImage]:
        # Use creative.image_prompt
        # Call Stable Diffusion API
        # Store images, return URLs
```

**API Endpoint**:
```python
POST /api/content/generate-images
{
    "creative_id": "uuid",
    "variants": ["square", "portrait"],
    "num_variations": 2
}
```

---

### Phase 2: Landing Page Generation

**Goal**: Generate HTML landing pages from offer + creative, auto-deploy.

**Implementation**:
```python
# New file: app/services/landing_page_generator.py
class LandingPageGenerator:
    async def generate(
        self,
        offer: Offer,
        primary_creative: Creative
    ) -> LandingPage:
        # Generate HTML using AI Brain
        # Include Meta Pixel automatically
        # Mobile-responsive, conversion-optimized
        # Deploy to /opt/fpai/.../landing-pages/
```

**API Endpoint**:
```python
POST /api/content/generate-landing-page
{
    "offer_id": "uuid",
    "template": "coaching"
}
```

---

### Phase 3: Auto-Campaign Creation

**Goal**: One-click campaign creation from generated content.

**Implementation**:
```python
# New file: app/services/auto_campaign.py
class AutoCampaignCreator:
    async def create_from_content(
        self,
        offer: Offer,
        creatives: List[Creative],
        images: List[Image],
        landing_page: LandingPage,
        budget_daily: float = 50.00
    ) -> Campaign:
        # Create campaign
        # Create ad sets with targeting
        # Create ads with creatives + images
        # Link to landing page
        # Launch campaign
```

**API Endpoint**:
```python
POST /api/content/auto-campaign
{
    "offer_id": "uuid",
    "budget_daily": 50.00,
    "auto_launch": true
}
```

---

### Phase 4: Full Pipeline

**Goal**: One API call = Complete content suite + Campaign launch.

**API Endpoint**:
```python
POST /api/content/generate-full
{
    "offer_id": "uuid",
    "num_creative_variations": 3,
    "generate_images": true,
    "generate_landing_page": true,
    "auto_create_campaign": true,
    "budget_daily": 50.00
}

Response:
{
    "job_id": "uuid",
    "status": "completed",
    "creatives": [...],
    "images": [...],
    "landing_page": {...},
    "campaign": {...},
    "campaign_url": "https://business.facebook.com/adsmanager/..."
}
```

---

## 🚀 Quick Start: Phase 1 (Image Generation)

### Step 1: Choose Image Provider

**Option A: Stable Diffusion (Recommended - FREE)**
```bash
# Sign up at: https://replicate.com
# Get API key
# Add to .env: REPLICATE_API_KEY=your_key
```

**Option B: DALL-E 3 (Better Quality)**
```bash
# Already have OpenAI API key?
# Add to .env: OPENAI_API_KEY=your_key
```

### Step 2: Create Image Generator Service

```python
# app/services/image_generator.py
import httpx
from replicate import Client

class ImageGenerator:
    def __init__(self):
        self.replicate = Client(api_token=settings.REPLICATE_API_KEY)
    
    async def generate_for_creative(self, creative, variants):
        # Use creative.image_prompt
        prompt = creative.image_prompt
        
        # Generate for each variant
        images = []
        for variant in variants:
            output = self.replicate.run(
                "stability-ai/stable-diffusion:...",
                input={"prompt": prompt, "aspect_ratio": variant}
            )
            # Store image, save URL
            images.append(...)
        
        return images
```

### Step 3: Add API Endpoint

```python
# app/api/content.py
@router.post("/generate-images")
async def generate_images(request: ImageGenerateRequest):
    creative = await get_creative(request.creative_id)
    generator = ImageGenerator()
    images = await generator.generate_for_creative(
        creative, 
        request.variants
    )
    return {"images": images}
```

### Step 4: Test

```bash
# Generate images for existing creative
curl -X POST https://fullpotential.ai/ads/api/content/generate-images \
  -H "Content-Type: application/json" \
  -d '{
    "creative_id": "your-creative-id",
    "variants": ["square", "portrait"],
    "num_variations": 2
  }'
```

---

## 📊 Current Status

| Component | Status | Next Step |
|-----------|--------|-----------|
| Ad Copy Generation | ✅ Done | - |
| Image Generation | ⏳ Ready to build | Choose provider, implement |
| Landing Page Gen | ⏳ Ready to build | Design templates, implement |
| Auto-Campaign | ⏳ Ready to build | Wire up Meta API |
| Full Pipeline | ⏳ Ready to build | Orchestrate all services |
| Auto-Optimization | ⏳ Ready to build | Add regeneration logic |

---

## 🎯 Recommended Order

1. **Week 1**: Image Generation (Phase 1)
   - Choose Stable Diffusion (free) or DALL-E
   - Implement `ImageGenerator`
   - Test with real creative

2. **Week 2**: Landing Page Generation (Phase 2)
   - Design coaching template
   - Implement `LandingPageGenerator`
   - Deploy to nginx

3. **Week 3**: Auto-Campaign (Phase 3)
   - Implement `AutoCampaignCreator`
   - Wire up Meta Ads API
   - Test end-to-end

4. **Week 4**: Full Pipeline (Phase 4)
   - Create `ContentPipeline` orchestrator
   - One-click generation + launch

5. **Week 5**: Auto-Optimization (Phase 5)
   - Performance analysis
   - Auto-regeneration
   - A/B testing

---

## 💡 Quick Win: Start with Image Generation

**Why**: You already have `image_prompt` in creatives, just need to generate actual images.

**Time**: 2-3 hours to implement

**Impact**: Immediate visual improvement for ads

**Next**: Once images work, landing pages are easy (just HTML generation).

---

## 🔗 Resources

- **Stable Diffusion (Replicate)**: https://replicate.com/stability-ai
- **DALL-E 3**: https://platform.openai.com/docs/guides/images
- **Meta Ads API**: https://developers.facebook.com/docs/marketing-apis
- **Landing Page Templates**: Check `SERVICES/seo-landing-generator/` for examples

---

## ❓ Questions?

1. **Which image provider?** → Start with Stable Diffusion (free), upgrade to DALL-E if needed
2. **Where to host landing pages?** → Use existing nginx (`/opt/fpai/.../landing-pages/`)
3. **How to store images?** → Start local, move to S3 later
4. **When to auto-launch?** → Make it optional (flag in API)

---

**Ready to start?** Let's build Phase 1 (Image Generation) first! 🚀

