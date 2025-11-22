"""
Full Potential AI - Main Landing Page
Minimal MVP showcasing vision and progress
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
from datetime import datetime

app = FastAPI(title="Full Potential AI", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Dashboard API for live metrics
DASHBOARD_API = "http://198.54.123.234:8002/api"


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main landing page"""

    # Fetch live metrics from dashboard
    progress_data = {"progress_percent": 36, "droplets_built": 5, "droplets_total": 11}

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{DASHBOARD_API}/paradise-progress")
            if response.status_code == 200:
                progress_data = response.json()
    except:
        pass  # Use defaults if API unavailable

    return templates.TemplateResponse("index.html", {
        "request": request,
        "progress": progress_data,
        "year": datetime.now().year
    })


@app.get("/offers", response_class=HTMLResponse)
async def offers(request: Request):
    """Conscious marketplace - Curated offers"""

    # Initial curated offers (will expand to database later)
    offers_data = [
        {
            "id": "mindvalley-lifebook",
            "name": "Mindvalley Lifebook Online",
            "category": "Personal Development",
            "description": "Design your ideal life across 12 key dimensions with Jon & Missy Butcher's transformational program.",
            "price": "$599",
            "commission": "30%",
            "commission_amount": "$180",
            "affiliate_url": "/go/mindvalley-lifebook",
            "image_url": "https://via.placeholder.com/400x250?text=Mindvalley+Lifebook",
            "featured": True
        },
        {
            "id": "kajabi",
            "name": "Kajabi",
            "category": "Business Tools",
            "description": "All-in-one platform to create, market, and sell online courses and coaching programs.",
            "price": "$149/mo",
            "commission": "30% recurring",
            "commission_amount": "$45/mo",
            "affiliate_url": "/go/kajabi",
            "image_url": "https://via.placeholder.com/400x250?text=Kajabi",
            "featured": True
        },
        {
            "id": "athletic-greens",
            "name": "Athletic Greens AG1",
            "category": "Health & Wellness",
            "description": "Comprehensive daily nutrition with 75 vitamins, minerals, and whole food ingredients.",
            "price": "$99/mo",
            "commission": "25%",
            "commission_amount": "$30",
            "affiliate_url": "/go/athletic-greens",
            "image_url": "https://via.placeholder.com/400x250?text=Athletic+Greens",
            "featured": True
        },
        {
            "id": "clickfunnels",
            "name": "ClickFunnels",
            "category": "Business Tools",
            "description": "Build high-converting sales funnels and marketing systems without coding.",
            "price": "$97/mo",
            "commission": "40% recurring",
            "commission_amount": "$39/mo",
            "affiliate_url": "/go/clickfunnels",
            "image_url": "https://via.placeholder.com/400x250?text=ClickFunnels",
            "featured": False
        },
        {
            "id": "convertkit",
            "name": "ConvertKit",
            "category": "Business Tools",
            "description": "Email marketing platform designed for creators, coaches, and online entrepreneurs.",
            "price": "$29/mo",
            "commission": "30% recurring",
            "commission_amount": "$9/mo",
            "affiliate_url": "/go/convertkit",
            "image_url": "https://via.placeholder.com/400x250?text=ConvertKit",
            "featured": False
        },
        {
            "id": "tony-robbins-upw",
            "name": "Tony Robbins UPW",
            "category": "Events & Retreats",
            "description": "Unleash the Power Within - 4-day immersive event to breakthrough limitations.",
            "price": "$2,495",
            "commission": "Custom",
            "commission_amount": "$500+",
            "affiliate_url": "/go/tony-robbins-upw",
            "image_url": "https://via.placeholder.com/400x250?text=Tony+Robbins+UPW",
            "featured": False
        },
        {
            "id": "four-sigmatic",
            "name": "Four Sigmatic Mushroom Coffee",
            "category": "Health & Wellness",
            "description": "Organic coffee infused with functional mushrooms for focus and immunity.",
            "price": "$45",
            "commission": "25%",
            "commission_amount": "$11",
            "affiliate_url": "/go/four-sigmatic",
            "image_url": "https://via.placeholder.com/400x250?text=Four+Sigmatic",
            "featured": False
        },
        {
            "id": "gaia",
            "name": "Gaia Streaming",
            "category": "Spiritual Growth",
            "description": "Conscious media library with yoga, meditation, and spiritual documentaries.",
            "price": "$11.99/mo",
            "commission": "25%",
            "commission_amount": "$3/mo",
            "affiliate_url": "/go/gaia",
            "image_url": "https://via.placeholder.com/400x250?text=Gaia",
            "featured": False
        },
        {
            "id": "thinkific",
            "name": "Thinkific",
            "category": "Business Tools",
            "description": "Create and sell online courses with an easy-to-use platform.",
            "price": "$49/mo",
            "commission": "30% (12 months)",
            "commission_amount": "$15/mo",
            "affiliate_url": "/go/thinkific",
            "image_url": "https://via.placeholder.com/400x250?text=Thinkific",
            "featured": False
        }
    ]

    return templates.TemplateResponse("offers.html", {
        "request": request,
        "offers": offers_data,
        "year": datetime.now().year
    })


@app.get("/coaches", response_class=HTMLResponse)
async def coaches(request: Request):
    """Coach directory - Find your perfect coach"""

    # Initial coach profiles (will expand as we onboard more)
    coaches_data = [
        {
            "id": "sample-life-coach",
            "name": "Sample Life Coach",
            "specialty": "Life Transformation & Purpose",
            "bio": "Helping high-achievers find deeper meaning and align their success with their soul's purpose.",
            "rate": "$200/session",
            "booking_url": "/book/sample-life-coach",
            "image_url": "https://via.placeholder.com/300x300?text=Coach+1",
            "categories": ["Life Coaching", "Purpose", "Spirituality"],
            "featured": True
        },
        {
            "id": "sample-business-coach",
            "name": "Sample Business Coach",
            "specialty": "Conscious Entrepreneurship",
            "bio": "Build a profitable business that serves humanity while honoring your values.",
            "rate": "$300/session",
            "booking_url": "/book/sample-business-coach",
            "image_url": "https://via.placeholder.com/300x300?text=Coach+2",
            "categories": ["Business", "Entrepreneurship", "Strategy"],
            "featured": True
        },
        {
            "id": "sample-health-coach",
            "name": "Sample Health Coach",
            "specialty": "Holistic Wellness",
            "bio": "Integrate mind, body, and spirit for optimal health and vitality.",
            "rate": "$150/session",
            "booking_url": "/book/sample-health-coach",
            "image_url": "https://via.placeholder.com/300x300?text=Coach+3",
            "categories": ["Health", "Nutrition", "Wellness"],
            "featured": False
        }
    ]

    return templates.TemplateResponse("coaches.html", {
        "request": request,
        "coaches": coaches_data,
        "year": datetime.now().year
    })


@app.get("/go/{offer_id}")
async def affiliate_redirect(offer_id: str):
    """Affiliate link redirector with tracking"""

    # Affiliate URLs (will move to database later)
    affiliate_urls = {
        "mindvalley-lifebook": "https://www.mindvalley.com/lifebook?affiliate=YOUR_ID",
        "kajabi": "https://kajabi.com/?via=YOUR_ID",
        "athletic-greens": "https://athleticgreens.com/YOUR_ID",
        "clickfunnels": "https://www.clickfunnels.com/?affiliate_id=YOUR_ID",
        "convertkit": "https://convertkit.com?lmref=YOUR_ID",
        "tony-robbins-upw": "https://www.tonyrobbins.com/events/unleash-the-power-within/?affiliate=YOUR_ID",
        "four-sigmatic": "https://us.foursigmatic.com/?rfsn=YOUR_ID",
        "gaia": "https://www.gaia.com/share/YOUR_ID",
        "thinkific": "https://www.thinkific.com/?ref=YOUR_ID"
    }

    # TODO: Log click for analytics

    redirect_url = affiliate_urls.get(offer_id, "https://fullpotential.com/offers")

    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=redirect_url, status_code=302)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "active",
        "service": "landing-page",
        "timestamp": datetime.utcnow().isoformat()
    }
