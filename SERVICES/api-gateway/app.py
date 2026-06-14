"""
Full Potential AI - Centralized API Gateway
============================================
Single point of control for all AI API calls with:
- Usage metering per user/service
- Cost tracking and budgets
- Rate limiting
- Billing integration
- API key management (one place for all providers)

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway (Port 8400)                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ Claude  │  │  GPT    │  │ Gemini  │  │ Future  │        │
│  │ Adapter │  │ Adapter │  │ Adapter │  │ APIs... │        │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘        │
│       └────────────┴────────────┴────────────┘              │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Metering & Billing Engine               │   │
│  │  • Track tokens/requests per user                    │   │
│  │  • Apply rate limits                                 │   │
│  │  • Calculate costs                                   │   │
│  │  • Enforce budgets                                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
"""

import os
import json
import time
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict
from functools import wraps

from fastapi import FastAPI, HTTPException, Depends, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Load environment
from dotenv import load_dotenv
load_dotenv()

# ============================================================
# Configuration
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# API Keys (centralized)
API_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY"),
    "anthropic": os.getenv("ANTHROPIC_API_KEY"),
    "gemini": os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
}

# Pricing per 1M tokens (as of Nov 2024)
PRICING = {
    # Claude
    "claude-opus-4-5": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-haiku": {"input": 0.25, "output": 1.25},
    # OpenAI
    "gpt-5.1": {"input": 10.00, "output": 30.00},  # Estimated
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "o3": {"input": 15.00, "output": 60.00},  # Estimated
    # Gemini
    "gemini-3-pro": {"input": 1.25, "output": 5.00},  # Estimated
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
}

# Default rate limits
DEFAULT_RATE_LIMITS = {
    "requests_per_minute": 60,
    "tokens_per_minute": 100000,
    "daily_budget_usd": 10.00,
}


# ============================================================
# Data Models
# ============================================================

class Provider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class ChatRequest(BaseModel):
    """Unified chat request format"""
    provider: Provider
    model: str
    messages: List[Dict[str, str]]
    max_tokens: int = 4096
    temperature: float = 0.7
    system: Optional[str] = None
    
    # Metering metadata
    user_id: Optional[str] = "anonymous"
    service_id: Optional[str] = "default"
    project_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Unified chat response format"""
    content: str
    model: str
    provider: str
    usage: Dict[str, int]
    cost_usd: float
    request_id: str
    timestamp: str


@dataclass
class UsageRecord:
    """Track usage for billing"""
    user_id: str
    service_id: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    timestamp: str
    request_id: str
    project_id: Optional[str] = None


@dataclass
class UserBudget:
    """User budget and limits"""
    user_id: str
    daily_budget_usd: float = 10.00
    monthly_budget_usd: float = 100.00
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000
    is_active: bool = True
    tier: str = "free"  # free, pro, enterprise


# ============================================================
# Storage (JSON-based, upgrade to DB later)
# ============================================================

class UsageStore:
    """Simple JSON-based usage tracking"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.usage_file = data_dir / "usage.json"
        self.budgets_file = data_dir / "budgets.json"
        self.rate_limits_file = data_dir / "rate_limits.json"
        self._load()
    
    def _load(self):
        """Load data from files"""
        self.usage: List[Dict] = []
        self.budgets: Dict[str, Dict] = {}
        self.rate_limits: Dict[str, List] = {}  # user_id -> list of request timestamps
        
        if self.usage_file.exists():
            self.usage = json.loads(self.usage_file.read_text())
        if self.budgets_file.exists():
            self.budgets = json.loads(self.budgets_file.read_text())
    
    def _save(self):
        """Persist data to files"""
        self.usage_file.write_text(json.dumps(self.usage, indent=2))
        self.budgets_file.write_text(json.dumps(self.budgets, indent=2))
    
    def record_usage(self, record: UsageRecord):
        """Record a usage event"""
        self.usage.append(asdict(record))
        self._save()
    
    def get_user_usage(self, user_id: str, since: datetime = None) -> Dict[str, Any]:
        """Get usage stats for a user"""
        if since is None:
            since = datetime.now() - timedelta(days=30)
        
        user_usage = [u for u in self.usage 
                      if u["user_id"] == user_id 
                      and datetime.fromisoformat(u["timestamp"]) >= since]
        
        total_cost = sum(u["cost_usd"] for u in user_usage)
        total_tokens = sum(u["input_tokens"] + u["output_tokens"] for u in user_usage)
        
        return {
            "user_id": user_id,
            "period_start": since.isoformat(),
            "total_requests": len(user_usage),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "by_provider": self._group_by_provider(user_usage),
            "by_model": self._group_by_model(user_usage),
        }
    
    def _group_by_provider(self, records: List[Dict]) -> Dict:
        """Group usage by provider"""
        result = {}
        for r in records:
            provider = r["provider"]
            if provider not in result:
                result[provider] = {"requests": 0, "tokens": 0, "cost_usd": 0}
            result[provider]["requests"] += 1
            result[provider]["tokens"] += r["input_tokens"] + r["output_tokens"]
            result[provider]["cost_usd"] += r["cost_usd"]
        return result
    
    def _group_by_model(self, records: List[Dict]) -> Dict:
        """Group usage by model"""
        result = {}
        for r in records:
            model = r["model"]
            if model not in result:
                result[model] = {"requests": 0, "tokens": 0, "cost_usd": 0}
            result[model]["requests"] += 1
            result[model]["tokens"] += r["input_tokens"] + r["output_tokens"]
            result[model]["cost_usd"] += r["cost_usd"]
        return result
    
    def get_budget(self, user_id: str) -> UserBudget:
        """Get user budget, create default if not exists"""
        if user_id not in self.budgets:
            self.budgets[user_id] = asdict(UserBudget(user_id=user_id))
            self._save()
        return UserBudget(**self.budgets[user_id])
    
    def set_budget(self, budget: UserBudget):
        """Set user budget"""
        self.budgets[budget.user_id] = asdict(budget)
        self._save()
    
    def check_rate_limit(self, user_id: str, limits: UserBudget) -> bool:
        """Check if user is within rate limits"""
        now = time.time()
        window = 60  # 1 minute window
        
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = []
        
        # Clean old entries
        self.rate_limits[user_id] = [t for t in self.rate_limits[user_id] if now - t < window]
        
        # Check limit
        if len(self.rate_limits[user_id]) >= limits.requests_per_minute:
            return False
        
        # Record this request
        self.rate_limits[user_id].append(now)
        return True
    
    def check_budget(self, user_id: str) -> tuple[bool, float]:
        """Check if user is within budget, return (ok, remaining)"""
        budget = self.get_budget(user_id)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        usage = self.get_user_usage(user_id, since=today)
        
        remaining = budget.daily_budget_usd - usage["total_cost_usd"]
        return remaining > 0, remaining


# ============================================================
# API Adapters
# ============================================================

class APIAdapter:
    """Base adapter for AI APIs"""
    
    async def chat(self, request: ChatRequest) -> tuple[str, Dict[str, int]]:
        raise NotImplementedError


class OpenAIAdapter(APIAdapter):
    """OpenAI API adapter"""
    
    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=API_KEYS["openai"]) if API_KEYS["openai"] else None
    
    async def chat(self, request: ChatRequest) -> tuple[str, Dict[str, int]]:
        if not self.client:
            raise HTTPException(503, "OpenAI not configured")
        
        messages = request.messages.copy()
        if request.system:
            messages.insert(0, {"role": "system", "content": request.system})
        
        response = self.client.chat.completions.create(
            model=request.model,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        
        content = response.choices[0].message.content
        usage = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        }
        return content, usage


class AnthropicAdapter(APIAdapter):
    """Anthropic Claude API adapter"""
    
    def __init__(self):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=API_KEYS["anthropic"]) if API_KEYS["anthropic"] else None
        except:
            self.client = None
    
    async def chat(self, request: ChatRequest) -> tuple[str, Dict[str, int]]:
        if not self.client:
            raise HTTPException(503, "Anthropic not configured")
        
        response = self.client.messages.create(
            model=request.model,
            max_tokens=request.max_tokens,
            system=request.system or "You are a helpful assistant.",
            messages=request.messages,
        )
        
        content = response.content[0].text
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return content, usage


class GeminiAdapter(APIAdapter):
    """Google Gemini API adapter"""
    
    def __init__(self):
        try:
            import google.generativeai as genai
            if API_KEYS["gemini"]:
                genai.configure(api_key=API_KEYS["gemini"])
                self.genai = genai
            else:
                self.genai = None
        except:
            self.genai = None
    
    async def chat(self, request: ChatRequest) -> tuple[str, Dict[str, int]]:
        if not self.genai:
            raise HTTPException(503, "Gemini not configured")
        
        model = self.genai.GenerativeModel(request.model)
        
        # Convert messages to Gemini format
        prompt = ""
        if request.system:
            prompt = f"System: {request.system}\n\n"
        for msg in request.messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            prompt += f"{role}: {msg['content']}\n\n"
        
        response = model.generate_content(prompt)
        
        content = response.text
        # Gemini doesn't always return token counts
        usage = {
            "input_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0) if hasattr(response, 'usage_metadata') else 0,
            "output_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0) if hasattr(response, 'usage_metadata') else 0,
        }
        return content, usage


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title="Full Potential AI - API Gateway",
    description="Centralized API gateway with metering and billing",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
store = UsageStore(DATA_DIR)
adapters = {
    Provider.OPENAI: OpenAIAdapter(),
    Provider.ANTHROPIC: AnthropicAdapter(),
    Provider.GEMINI: GeminiAdapter(),
}


def calculate_cost(model: str, usage: Dict[str, int]) -> float:
    """Calculate cost based on token usage"""
    # Find matching pricing
    pricing = None
    for key, price in PRICING.items():
        if key in model.lower():
            pricing = price
            break
    
    if not pricing:
        # Default pricing estimate
        pricing = {"input": 1.00, "output": 3.00}
    
    cost = (usage["input_tokens"] * pricing["input"] + 
            usage["output_tokens"] * pricing["output"]) / 1_000_000
    return round(cost, 6)


def generate_request_id() -> str:
    """Generate unique request ID"""
    import uuid
    return f"req_{uuid.uuid4().hex[:12]}"


# ============================================================
# API Endpoints
# ============================================================

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "1.0.0",
        "providers": {
            "openai": API_KEYS["openai"] is not None,
            "anthropic": API_KEYS["anthropic"] is not None,
            "gemini": API_KEYS["gemini"] is not None,
        }
    }


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    """
    Unified chat endpoint for all AI providers.
    
    Handles:
    - Provider routing (OpenAI, Anthropic, Gemini)
    - Usage metering
    - Cost calculation
    - Rate limiting
    - Budget enforcement
    """
    user_id = request.user_id or "anonymous"
    request_id = generate_request_id()
    
    # Check rate limits
    budget = store.get_budget(user_id)
    if not store.check_rate_limit(user_id, budget):
        raise HTTPException(429, "Rate limit exceeded")
    
    # Check budget
    within_budget, remaining = store.check_budget(user_id)
    if not within_budget:
        raise HTTPException(402, f"Daily budget exceeded. Remaining: ${remaining:.2f}")
    
    # Get adapter and make request
    adapter = adapters.get(request.provider)
    if not adapter:
        raise HTTPException(400, f"Unknown provider: {request.provider}")
    
    try:
        content, usage = await adapter.chat(request)
    except Exception as e:
        raise HTTPException(500, f"API error: {str(e)}")
    
    # Calculate cost
    cost = calculate_cost(request.model, usage)
    
    # Record usage (async)
    record = UsageRecord(
        user_id=user_id,
        service_id=request.service_id or "default",
        provider=request.provider.value,
        model=request.model,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cost_usd=cost,
        timestamp=datetime.now().isoformat(),
        request_id=request_id,
        project_id=request.project_id,
    )
    background_tasks.add_task(store.record_usage, record)
    
    return ChatResponse(
        content=content,
        model=request.model,
        provider=request.provider.value,
        usage=usage,
        cost_usd=cost,
        request_id=request_id,
        timestamp=datetime.now().isoformat(),
    )


@app.get("/v1/usage/{user_id}")
async def get_usage(user_id: str, days: int = 30):
    """Get usage statistics for a user"""
    since = datetime.now() - timedelta(days=days)
    return store.get_user_usage(user_id, since)


@app.get("/v1/usage")
async def get_all_usage(days: int = 30):
    """Get usage statistics for all users (admin)"""
    since = datetime.now() - timedelta(days=days)
    
    # Group by user
    users = set(u["user_id"] for u in store.usage)
    result = {
        "period_days": days,
        "total_cost_usd": sum(u["cost_usd"] for u in store.usage 
                              if datetime.fromisoformat(u["timestamp"]) >= since),
        "total_requests": len([u for u in store.usage 
                               if datetime.fromisoformat(u["timestamp"]) >= since]),
        "users": {uid: store.get_user_usage(uid, since) for uid in users},
    }
    return result


@app.get("/v1/budget/{user_id}")
async def get_budget(user_id: str):
    """Get budget for a user"""
    budget = store.get_budget(user_id)
    within_budget, remaining = store.check_budget(user_id)
    return {
        **asdict(budget),
        "remaining_daily_usd": remaining,
        "within_budget": within_budget,
    }


@app.put("/v1/budget/{user_id}")
async def set_budget(
    user_id: str,
    daily_budget_usd: float = None,
    monthly_budget_usd: float = None,
    requests_per_minute: int = None,
    tier: str = None,
):
    """Update budget for a user (admin)"""
    budget = store.get_budget(user_id)
    
    if daily_budget_usd is not None:
        budget.daily_budget_usd = daily_budget_usd
    if monthly_budget_usd is not None:
        budget.monthly_budget_usd = monthly_budget_usd
    if requests_per_minute is not None:
        budget.requests_per_minute = requests_per_minute
    if tier is not None:
        budget.tier = tier
    
    store.set_budget(budget)
    return asdict(budget)


@app.get("/v1/pricing")
async def get_pricing():
    """Get current pricing for all models"""
    return {
        "pricing_per_million_tokens": PRICING,
        "note": "Prices in USD. Input and output tokens priced separately.",
    }


# ============================================================
# Admin Dashboard (HTML)
# ============================================================

@app.get("/")
async def dashboard():
    """Simple admin dashboard"""
    from fastapi.responses import HTMLResponse
    
    usage = store.get_user_usage("all", datetime.now() - timedelta(days=30))
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Gateway - Full Potential AI</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Outfit', system-ui, sans-serif;
                background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%);
                color: #e0e0e0;
                min-height: 100vh;
                padding: 2rem;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            h1 {{
                font-size: 2.5rem;
                background: linear-gradient(135deg, #00d4ff, #7c3aed);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 2rem;
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }}
            .stat-card {{
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 12px;
                padding: 1.5rem;
            }}
            .stat-value {{
                font-size: 2rem;
                font-weight: bold;
                color: #00d4ff;
            }}
            .stat-label {{ color: #888; margin-top: 0.5rem; }}
            .providers {{
                display: flex;
                gap: 1rem;
                margin-top: 1rem;
            }}
            .provider {{
                padding: 0.5rem 1rem;
                border-radius: 20px;
                font-size: 0.9rem;
            }}
            .provider.active {{ background: #22c55e33; color: #22c55e; }}
            .provider.inactive {{ background: #ef444433; color: #ef4444; }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 2rem;
            }}
            th, td {{
                padding: 1rem;
                text-align: left;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }}
            th {{ color: #888; }}
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
    </head>
    <body>
        <div class="container">
            <h1>⚡ API Gateway</h1>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{len(store.usage)}</div>
                    <div class="stat-label">Total Requests</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${sum(u['cost_usd'] for u in store.usage):.2f}</div>
                    <div class="stat-label">Total Cost</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{sum(u['input_tokens'] + u['output_tokens'] for u in store.usage):,}</div>
                    <div class="stat-label">Total Tokens</div>
                </div>
            </div>
            
            <h2 style="margin: 2rem 0 1rem;">Provider Status</h2>
            <div class="providers">
                <span class="provider {'active' if API_KEYS['openai'] else 'inactive'}">
                    OpenAI {'✓' if API_KEYS['openai'] else '✗'}
                </span>
                <span class="provider {'active' if API_KEYS['anthropic'] else 'inactive'}">
                    Anthropic {'✓' if API_KEYS['anthropic'] else '✗'}
                </span>
                <span class="provider {'active' if API_KEYS['gemini'] else 'inactive'}">
                    Gemini {'✓' if API_KEYS['gemini'] else '✗'}
                </span>
            </div>
            
            <h2 style="margin: 2rem 0 1rem;">Recent Usage</h2>
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>User</th>
                        <th>Provider</th>
                        <th>Model</th>
                        <th>Tokens</th>
                        <th>Cost</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td>{u['timestamp'][:19]}</td>
                        <td>{u['user_id']}</td>
                        <td>{u['provider']}</td>
                        <td>{u['model'][:30]}</td>
                        <td>{u['input_tokens'] + u['output_tokens']:,}</td>
                        <td>${u['cost_usd']:.4f}</td>
                    </tr>
                    ''' for u in store.usage[-20:][::-1])}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html)


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    print("🚀 Starting API Gateway on port 8400...")
    uvicorn.run(app, host="0.0.0.0", port=8400)

