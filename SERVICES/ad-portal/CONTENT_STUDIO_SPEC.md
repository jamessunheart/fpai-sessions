# Content Studio - Full AI Content Creation Suite

## 🎯 Vision

Transform Ad Portal into a complete **AI-powered content creation and advertising suite** that:
1. **Generates** content (copy, images, landing pages) using AI
2. **Creates** ad campaigns automatically from generated content
3. **Launches** ads on Meta
4. **Tracks** performance end-to-end (ROAS → Profit)
5. **Optimizes** by regenerating underperforming content

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTENT STUDIO                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Content    │───▶│   Creative   │───▶│   Landing     │ │
│  │  Generator   │    │   Generator  │    │   Page Gen    │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                   │                     │          │
│         └───────────────────┴─────────────────────┘          │
│                           │                                  │
│                           ▼                                  │
│              ┌────────────────────────┐                      │
│              │  Campaign Auto-Creator │                      │
│              └────────────────────────┘                      │
│                           │                                  │
│                           ▼                                  │
│              ┌────────────────────────┐                      │
│              │   Meta Ads API         │                      │
│              │   (Launch Campaigns)   │                      │
│              └────────────────────────┘                      │
│                           │                                  │
│                           ▼                                  │
│              ┌────────────────────────┐                      │
│              │   Performance Tracker │                      │
│              │   (ROAS → Profit)      │                      │
│              └────────────────────────┘                      │
│                           │                                  │
│                           ▼                                  │
│              ┌────────────────────────┐                      │
│              │   Auto-Optimizer       │                      │
│              │   (Regenerate losers) │                      │
│              └────────────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 New Components

### 1. **Image Generator Service** (`app/services/image_generator.py`)
- Generates ad images using AI (DALL-E, Midjourney API, Stable Diffusion)
- Creates multiple variations per creative
- Optimizes for Meta ad specs (1:1, 4:5, 9:16, 16:9)
- Stores images in S3/CDN

### 2. **Landing Page Generator** (`app/services/landing_page_generator.py`)
- Generates HTML/CSS landing pages from offer details
- Includes Meta Pixel tracking automatically
- Mobile-responsive, conversion-optimized
- Deploys to static hosting (S3 + CloudFront or Vercel)

### 3. **Content Pipeline** (`app/services/content_pipeline.py`)
- Orchestrates full content creation flow
- Generates copy → Images → Landing page → Campaign
- Handles dependencies and error recovery

### 4. **Auto-Campaign Creator** (`app/services/auto_campaign.py`)
- Automatically creates Meta campaigns from generated content
- Sets up ad sets, targeting, budgets
- Launches campaigns programmatically

### 5. **Performance Optimizer** (`app/services/optimizer.py` - Enhanced)
- Analyzes creative performance
- Auto-regenerates underperforming content
- A/B tests variations automatically

---

## 🔌 Integration Points

### AI Brain Service (Existing)
- **URL**: `http://162.0.208.88:8101`
- **Endpoints**:
  - `POST /api/generate` - Text generation (copy, landing page HTML)
  - `POST /api/generate/image` - Image generation (if available)

### Image Generation Options
1. **DALL-E 3** (via OpenAI API)
2. **Stable Diffusion** (via Replicate API)
3. **Midjourney** (via unofficial API or manual)
4. **FI-Art Service** (if it has image generation)

### Landing Page Hosting
- **Option 1**: Deploy to `/opt/fpai/core/applications/website-ai/frontend/landing-pages/`
- **Option 2**: S3 + CloudFront (better for scale)
- **Option 3**: Vercel/Netlify (easiest)

---

## 📊 Data Model Extensions

### New Tables

```sql
-- Generated Images
CREATE TABLE generated_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creative_id UUID REFERENCES creatives(id),
    image_url TEXT NOT NULL,
    image_prompt TEXT,
    variant_type VARCHAR(20), -- 'square', 'portrait', 'landscape'
    storage_path TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Landing Pages
CREATE TABLE landing_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    offer_id UUID REFERENCES offers(id),
    url TEXT NOT NULL UNIQUE,
    html_content TEXT NOT NULL,
    meta_pixel_id VARCHAR(50),
    conversion_event VARCHAR(50), -- 'Purchase', 'Lead', etc.
    deployed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Content Generation Jobs
CREATE TABLE content_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    offer_id UUID REFERENCES offers(id),
    job_type VARCHAR(50), -- 'full_suite', 'images_only', 'landing_page_only'
    status VARCHAR(20), -- 'pending', 'generating', 'completed', 'failed'
    generated_creatives UUID[],
    generated_images UUID[],
    landing_page_id UUID REFERENCES landing_pages(id),
    campaign_id UUID REFERENCES campaigns(id),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

---

## 🚀 API Endpoints

### Content Generation

```python
# Generate full content suite (copy + images + landing page)
POST /api/content/generate-full
{
    "offer_id": "uuid",
    "num_creative_variations": 3,
    "generate_images": true,
    "generate_landing_page": true,
    "auto_create_campaign": false  # Set true to auto-launch
}

# Generate images for existing creative
POST /api/content/generate-images
{
    "creative_id": "uuid",
    "variants": ["square", "portrait", "landscape"],
    "num_variations": 2
}

# Generate landing page
POST /api/content/generate-landing-page
{
    "offer_id": "uuid",
    "template": "coaching" | "product" | "service",
    "include_pixel": true
}

# Auto-create campaign from generated content
POST /api/content/auto-campaign
{
    "offer_id": "uuid",
    "budget_daily": 50.00,
    "targeting": {...},
    "use_generated_content": true
}
```

### Landing Pages

```python
# List landing pages
GET /api/landing-pages

# Get landing page by ID
GET /api/landing-pages/{id}

# Preview landing page HTML
GET /api/landing-pages/{id}/preview

# Deploy landing page
POST /api/landing-pages/{id}/deploy
```

---

## 🎨 Content Generation Flow

### Step 1: Generate Ad Copy (Existing ✅)
```python
# Already implemented in creative_ai.py
generator = CreativeAIGenerator()
creatives = await generator.generate_variations(
    offer=offer,
    tone="professional",
    num_variations=3
)
```

### Step 2: Generate Images (New)
```python
# New service
image_gen = ImageGenerator()
for creative in creatives:
    images = await image_gen.generate_for_creative(
        creative=creative,
        variants=["square", "portrait"],
        num_variations=2
    )
    # Store images, link to creative
```

### Step 3: Generate Landing Page (New)
```python
# New service
page_gen = LandingPageGenerator()
landing_page = await page_gen.generate(
    offer=offer,
    primary_creative=creatives[0],  # Use best-performing creative
    include_pixel=True,
    template="coaching"
)
# Deploy to hosting
url = await page_gen.deploy(landing_page)
```

### Step 4: Auto-Create Campaign (New)
```python
# New service
campaign_creator = AutoCampaignCreator()
campaign = await campaign_creator.create_from_content(
    offer=offer,
    creatives=creatives,
    images=all_images,
    landing_page=landing_page,
    budget_daily=50.00,
    targeting={
        "age_min": 25,
        "age_max": 55,
        "genders": [1, 2],  # All
        "interests": ["coaching", "personal development"]
    }
)
# Launch campaign
await campaign_creator.launch(campaign.id)
```

---

## 🤖 AI Prompts

### Landing Page Generation Prompt
```python
LANDING_PAGE_PROMPT = """
Generate a complete, conversion-optimized landing page HTML for this coaching offer:

OFFER:
- Name: {offer_name}
- Description: {offer_description}
- Price: ${offer_price}
- Key Benefits: {benefits}

REQUIREMENTS:
1. Hero section with compelling headline (from creative: {headline})
2. Benefits section (3-5 key points)
3. Social proof section (testimonials placeholder)
4. Pricing section with clear CTA
5. FAQ section (3-5 questions)
6. Footer with contact info

TECHNICAL:
- Mobile-responsive (Tailwind CSS)
- Include Meta Pixel tracking code (pixel_id: {pixel_id})
- Conversion event: 'Purchase' on CTA click
- Fast loading, SEO-friendly
- Professional, trustworthy design

OUTPUT:
- Complete HTML file (inline CSS, no external dependencies)
- Include <head> with meta tags, pixel code
- Include <body> with all sections
- Use Tailwind CDN for styling
- Include JavaScript for pixel tracking

Format as complete, ready-to-deploy HTML.
"""
```

### Image Generation Prompt Enhancement
```python
IMAGE_PROMPT_TEMPLATE = """
Create a professional, high-converting Facebook/Instagram ad image for:

PRODUCT: {offer_name}
HEADLINE: {headline}
TONE: {tone}

REQUIREMENTS:
- Professional, trustworthy aesthetic
- Clear focal point (person or product)
- Warm, inviting colors
- Text overlay area (for headline)
- No text in image (we'll add via Meta)
- High contrast for mobile visibility
- {variant} aspect ratio ({dimensions})

STYLE: Modern, clean, aspirational. Avoid clichés. Focus on transformation/outcome.
"""
```

---

## 🔄 Auto-Optimization Flow

```python
# Runs daily via scheduler
async def optimize_underperformers():
    # Find creatives with low CTR (< 1%) or high CPA (> $50)
    underperformers = await db.execute(
        select(Creative)
        .join(AdMetrics)
        .where(
            (AdMetrics.ctr < 1.0) | (AdMetrics.cpa > 50.0)
        )
        .group_by(Creative.id)
    )
    
    for creative in underperformers:
        # Generate improved version
        improved = await generator.improve_creative(
            creative=creative,
            metrics=metrics,
            suggestion_type="ctr"  # or "cpa"
        )
        
        # Create new creative variation
        new_creative = await create_creative(
            campaign_id=creative.campaign_id,
            headline=improved.headline,
            primary_text=improved.primary_text,
            ...
        )
        
        # Pause old creative, activate new one
        creative.active = False
        new_creative.active = True
        
        # Generate new images for improved creative
        await image_gen.generate_for_creative(new_creative)
```

---

## 📁 File Structure

```
SERVICES/ad-portal/
├── app/
│   ├── services/
│   │   ├── creative_ai.py          # ✅ Existing
│   │   ├── image_generator.py       # 🆕 New
│   │   ├── landing_page_generator.py # 🆕 New
│   │   ├── content_pipeline.py     # 🆕 New
│   │   ├── auto_campaign.py         # 🆕 New
│   │   └── optimizer.py             # 🔄 Enhanced
│   ├── models/
│   │   ├── image.py                 # 🆕 New
│   │   ├── landing_page.py          # 🆕 New
│   │   └── content_job.py           # 🆕 New
│   ├── api/
│   │   ├── content.py               # 🆕 New endpoints
│   │   └── landing_pages.py         # 🆕 New endpoints
│   └── integrations/
│       └── image_apis.py            # 🆕 DALL-E, Stable Diffusion
├── static/
│   └── landing-pages/               # Generated landing pages
└── templates/
    └── landing-page/                # Landing page templates
```

---

## 🎯 Implementation Phases

### Phase 1: Image Generation (Week 1)
- [ ] Create `ImageGenerator` service
- [ ] Integrate DALL-E 3 or Stable Diffusion
- [ ] Store images in S3 or local storage
- [ ] Link images to creatives
- [ ] API endpoint: `POST /api/content/generate-images`

### Phase 2: Landing Page Generation (Week 2)
- [ ] Create `LandingPageGenerator` service
- [ ] Generate HTML from offer + creative
- [ ] Auto-include Meta Pixel
- [ ] Deploy to hosting
- [ ] API endpoints for landing pages

### Phase 3: Auto-Campaign Creation (Week 3)
- [ ] Create `AutoCampaignCreator` service
- [ ] Auto-generate campaigns from content
- [ ] Set targeting, budgets, schedules
- [ ] Launch campaigns via Meta API
- [ ] API endpoint: `POST /api/content/auto-campaign`

### Phase 4: Full Pipeline (Week 4)
- [ ] Create `ContentPipeline` orchestrator
- [ ] End-to-end flow: Offer → Content → Campaign → Launch
- [ ] Error handling and recovery
- [ ] Job tracking system
- [ ] API endpoint: `POST /api/content/generate-full`

### Phase 5: Auto-Optimization (Week 5)
- [ ] Enhance optimizer with content regeneration
- [ ] A/B testing framework
- [ ] Performance-based auto-improvement
- [ ] Scheduled optimization jobs

---

## 💰 Cost Considerations

### Image Generation
- **DALL-E 3**: ~$0.04/image (1024x1024)
- **Stable Diffusion**: ~$0.002/image (via Replicate)
- **Recommendation**: Start with Stable Diffusion, upgrade to DALL-E for quality

### Landing Page Hosting
- **S3 + CloudFront**: ~$0.50/month per 1000 pages
- **Vercel**: Free tier (good for MVP)
- **Local hosting**: Free (use existing nginx)

### AI Brain Calls
- Already configured, uses existing credits

---

## 🚦 Success Metrics

1. **Content Generation Speed**: < 2 minutes for full suite
2. **Image Quality**: > 80% approval rate (Meta)
3. **Landing Page Conversion**: > 3% (industry avg: 2-5%)
4. **Auto-Campaign Success**: > 70% launch success rate
5. **Optimization Impact**: 20%+ improvement in CTR/CPA

---

## 🔗 Next Steps

1. **Choose image generation provider** (DALL-E vs Stable Diffusion)
2. **Set up image storage** (S3 vs local)
3. **Design landing page templates** (coaching, product, service)
4. **Build Phase 1** (Image generation)
5. **Test with real offer** (coaching service)

---

## 📚 References

- Meta Ads API: https://developers.facebook.com/docs/marketing-apis
- DALL-E API: https://platform.openai.com/docs/guides/images
- Stable Diffusion (Replicate): https://replicate.com/stability-ai
- Landing Page Best Practices: Conversion optimization guides

