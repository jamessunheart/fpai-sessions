"""
GPU BRIDGE - Universal AI Gateway

This bridge connects ALL FPAI services to the GPU fleet.
Services call this instead of Claude/OpenAI APIs.

Benefits:
- Near-zero marginal cost (GPUs already paid for)
- Faster response times (local inference)
- No rate limits
- Full control

Endpoints:
- POST /v1/chat/completions - OpenAI-compatible chat
- POST /v1/completions - Text completion
- POST /generate - Simple generation
- GET /models - Available models
- GET /health - Health check
"""

import os
import sys
import json
import random
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import model configuration
try:
    import sys
    sys.path.insert(0, "/opt/fpai/ai-brain/v2")
    from builder.config import get_config, MODEL_REGISTRY, get_fallback_chain
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


app = FastAPI(
    title="FPAI GPU Bridge",
    description="Universal AI Gateway - Routes all AI requests to GPU fleet",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config — keys scrubbed 2026-05-18; service is ARCHIVED. Read from env if revived.
VASTAI_API_KEY = os.environ.get("VASTAI_API_KEY", "")
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "")
LOG_FILE = "/opt/fpai/ai-brain/v2/data/gpu_bridge.log"
STATS_FILE = "/opt/fpai/ai-brain/v2/data/gpu_bridge_stats.json"

# Cache for GPU endpoints
GPU_ENDPOINTS = []
LAST_DISCOVERY = 0
DISCOVERY_INTERVAL = 60  # Refresh every 60 seconds

# Endpoint metadata refresh
ENDPOINT_TAGS_TIMEOUT_SECONDS = 3
ENDPOINT_GENERATE_TIMEOUT_SECONDS = 120
ENDPOINT_REFRESH_WORKERS = 24

# Stats
STATS = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "tokens_generated": 0,
    "cost_saved": 0.0,  # vs using Claude/OpenAI
    "started_at": datetime.utcnow().isoformat(),
    "last_error": None,
    "last_success_at": None
}

# Locks (FastAPI sync handlers may execute concurrently)
DISCOVERY_LOCK = threading.Lock()
STATS_LOCK = threading.Lock()


def log(msg: str):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] {msg}"
    print(entry)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(entry + "\n")


def save_stats():
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    with open(STATS_FILE, "w") as f:
        json.dump(STATS, f, indent=2)

def _model_base(name: str) -> str:
    if not name:
        return ""
    return name.split(":", 1)[0].strip()

def _model_matches(requested: str, available: str) -> bool:
    """Return True if an endpoint's available model should satisfy the requested model."""
    if not requested or not available:
        return False
    req = requested.strip()
    avail = available.strip()
    if req == avail:
        return True
    # Match by base name when tags differ (e.g. deepseek-coder:6.7b vs deepseek-coder:latest)
    return _model_base(req) == _model_base(avail)

def _fetch_endpoint_tags(url: str) -> tuple[str, bool, list[str], Optional[str]]:
    """Return (url, healthy, models, error)."""
    try:
        r = requests.get(f"{url}/api/tags", timeout=ENDPOINT_TAGS_TIMEOUT_SECONDS)
        if r.status_code != 200:
            return url, False, [], f"tags_http_{r.status_code}"
        data = r.json()
        models = [m.get("name") for m in data.get("models", []) if isinstance(m, dict) and m.get("name")]
        return url, True, models, None
    except Exception as e:
        return url, False, [], str(e)

def _refresh_endpoint_inventory(endpoints: List[Dict]) -> None:
    """Populate endpoint health + models concurrently (in-place)."""
    url_to_ep = {ep.get("url"): ep for ep in endpoints if ep.get("url")}
    urls = list(url_to_ep.keys())
    if not urls:
        return

    max_workers = min(len(urls), ENDPOINT_REFRESH_WORKERS)
    results: list[tuple[str, bool, list[str], Optional[str]]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_fetch_endpoint_tags, url) for url in urls]
        for fut in as_completed(futures):
            results.append(fut.result())

    checked_at = time.time()
    for url, healthy, models, err in results:
        ep = url_to_ep.get(url)
        if not ep:
            continue
        ep["healthy"] = healthy
        ep["models"] = models
        ep["last_checked"] = checked_at
        ep["last_error"] = err


def discover_gpu_endpoints() -> List[Dict]:
    """Discover all available GPU endpoints"""
    global GPU_ENDPOINTS, LAST_DISCOVERY
    now = time.time()

    with DISCOVERY_LOCK:
        if GPU_ENDPOINTS and (now - LAST_DISCOVERY) < DISCOVERY_INTERVAL:
            return GPU_ENDPOINTS

        endpoints: list[Dict] = []

        # Vast.ai instances
        try:
            r = requests.get(
                f"https://console.vast.ai/api/v0/instances/?api_key={VASTAI_API_KEY}",
                timeout=10
            )
            for inst in r.json().get("instances", []):
                if inst.get("actual_status") == "running":
                    ip = inst.get("public_ipaddr")
                    ports = inst.get("ports", {})

                    # Find Ollama port
                    for k, v in ports.items():
                        if "11434" in str(k):
                            if isinstance(v, list) and v:
                                port = v[0].get("HostPort") if isinstance(v[0], dict) else v[0]
                            elif isinstance(v, dict):
                                port = v.get("HostPort")
                            else:
                                port = v

                            if port and ip:
                                endpoints.append({
                                    "url": f"http://{ip}:{port}",
                                    "provider": "vastai",
                                    "gpu": inst.get("gpu_name", "Unknown"),
                                    "cost": inst.get("dph_total", 0)
                                })
                                break
        except Exception as e:
            log(f"Vast.ai discovery error: {e}")

        # RunPod pods (optional)
        try:
            r = requests.post(
                "https://api.runpod.io/graphql",
                headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
                json={"query": "query { myself { pods { id name runtime { ports { privatePort publicPort } } } } }"},
                timeout=10
            )
            for pod in r.json().get("data", {}).get("myself", {}).get("pods", []):
                if pod.get("runtime"):
                    endpoints.append({
                        "url": f"https://{pod['id']}-11434.proxy.runpod.net",
                        "provider": "runpod",
                        "gpu": pod.get("name", "Unknown"),
                        "cost": 0.40  # Approximate
                    })
        except Exception as e:
            log(f"RunPod discovery error: {e}")

        # Merge with existing cache so we preserve health/model metadata
        old_by_url = {ep.get("url"): ep for ep in GPU_ENDPOINTS if isinstance(ep, dict) and ep.get("url")}
        merged: list[Dict] = []
        for ep in endpoints:
            url = ep.get("url")
            if url in old_by_url:
                existing = old_by_url[url]
                existing.update(ep)
                merged.append(existing)
            else:
                ep.setdefault("healthy", False)
                ep.setdefault("models", [])
                ep.setdefault("last_checked", 0)
                ep.setdefault("last_error", None)
                ep.setdefault("fail_count", 0)
                merged.append(ep)

        GPU_ENDPOINTS = merged
        LAST_DISCOVERY = now

        # Refresh model inventories (fast, concurrent)
        _refresh_endpoint_inventory(GPU_ENDPOINTS)

        log(f"Discovered {len(GPU_ENDPOINTS)} GPU endpoints")
        return GPU_ENDPOINTS


def get_healthy_endpoint() -> Optional[Dict]:
    """Get a healthy GPU endpoint"""
    endpoints = discover_gpu_endpoints()
    if not endpoints:
        return None
    healthy = [ep for ep in endpoints if ep.get("healthy") and ep.get("models")]
    if not healthy:
        # Try forcing a refresh on demand
        _refresh_endpoint_inventory(endpoints)
        healthy = [ep for ep in endpoints if ep.get("healthy") and ep.get("models")]
    if not healthy:
        return None
    random.shuffle(healthy)
    return healthy[0]


def call_ollama(endpoint: Dict, prompt: str, model: str = "llama3.1:8b", 
                system: str = None, max_tokens: int = 1000) -> Dict:
    """Call Ollama on a GPU endpoint"""
    
    full_prompt = prompt
    if system:
        full_prompt = f"{system}\n\n{prompt}"
    
    try:
        r = requests.post(
            f"{endpoint['url']}/api/generate",
            json={
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens
                }
            },
            timeout=120
        )
        
        if r.status_code == 200:
            data = r.json()
            return {
                "success": True,
                "response": data.get("response", ""),
                "model": model,
                "gpu": endpoint.get("gpu"),
                "tokens": len(data.get("response", "").split())
            }
        else:
            return {"success": False, "error": f"HTTP {r.status_code}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== API ENDPOINTS ====================

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str = "llama3.1:8b"
    messages: List[ChatMessage]
    max_tokens: int = 1000
    temperature: float = 0.7

class CompletionRequest(BaseModel):
    model: str = "llama3.1:8b"
    prompt: str
    max_tokens: int = 1000

class SimpleRequest(BaseModel):
    prompt: str
    model: str = "llama3.1:8b"
    system: str = None
    max_tokens: int = 1000



def get_endpoint_for_model(
    model: str,
    exclude_urls: Optional[set[str]] = None,
    allow_local_fallback: bool = True
) -> Optional[Dict]:
    """Get a healthy endpoint that has the requested model (prefers real GPUs over local CPU)."""
    if not model:
        return get_healthy_endpoint()

    exclude_urls = exclude_urls or set()

    endpoints = discover_gpu_endpoints()
    candidates: list[Dict] = []
    for ep in endpoints:
        url = ep.get("url")
        if not url or url in exclude_urls:
            continue
        if not ep.get("healthy"):
            continue
        models = ep.get("models") or []
        if any(_model_matches(model, m) for m in models):
            candidates.append(ep)

    if candidates:
        random.shuffle(candidates)
        return candidates[0]

    if allow_local_fallback:
        # Fallback: local CPU ollama only if the model exists locally
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            if r.status_code == 200:
                local_models = [
                    m.get("name")
                    for m in r.json().get("models", [])
                    if isinstance(m, dict) and m.get("name")
                ]
                if any(_model_matches(model, m) for m in local_models):
                    return {
                        "url": "http://localhost:11434",
                        "provider": "local",
                        "gpu": "local-cpu",
                        "healthy": True,
                        "models": local_models
                    }
        except Exception:
            pass

    return None


@app.get("/")
def root():
    endpoints = discover_gpu_endpoints()
    return {
        "service": "FPAI GPU Bridge",
        "description": "Universal AI Gateway - Routes to GPU fleet",
        "gpu_endpoints": len(endpoints),
        "endpoints": [
            "POST /v1/chat/completions - OpenAI-compatible",
            "POST /v1/completions - Text completion",
            "POST /generate - Simple generation",
            "GET /models - Available models",
            "GET /health - Health check",
            "GET /stats - Usage statistics"
        ]
    }


@app.get("/health")
def health():
    endpoints = discover_gpu_endpoints()
    healthy = get_healthy_endpoint()
    return {
        "status": "healthy" if healthy else "degraded",
        "total_endpoints": len(endpoints),
        "healthy_endpoint": healthy.get("gpu") if healthy else None,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/models")
def list_models():
    """List available models across all GPUs, integrated with config system"""
    endpoints = discover_gpu_endpoints()
    discovered_models = set()
    for ep in endpoints:
        for m in ep.get("models", []) or []:
            if m:
                discovered_models.add(m)
    
    # Get config-based model info
    if CONFIG_AVAILABLE:
        config = get_config()
        primary = config.PRIMARY_MODELS
        
        return {
            "models": list(discovered_models),
            "primary_models": primary,
            "default": primary[0] if primary else "llama3.1:8b",
            "recommended": [
                "deepseek-coder:7b",
                "qwen2.5-coder:7b",
                "llama3.1:8b"
            ],
            "config_loaded": True
        }
    
    return {
        "models": list(discovered_models),
        "default": "llama3.1:8b",
        "recommended": [
            "deepseek-coder:7b",
            "qwen2.5-coder:7b",
            "llama3.1:8b"
        ],
        "config_loaded": False
    }


@app.get("/stats")
def get_stats():
    return {
        **STATS,
        "gpu_endpoints": len(discover_gpu_endpoints()),
        "uptime_hours": (datetime.utcnow() - datetime.fromisoformat(STATS["started_at"])).total_seconds() / 3600
    }



@app.get("/utilization")
def get_utilization():
    """Get per-GPU utilization metrics"""
    import json
    import os
    util_file = "/opt/fpai/ai-brain/v2/data/gpu_utilization.json"
    if os.path.exists(util_file):
        with open(util_file, "r") as f:
            return json.load(f)
    else:
        return {"gpus": {}, "last_updated": None, "total_requests": 0, "total_tokens": 0}

@app.post("/generate")
def generate(req: SimpleRequest):
    """Simple generation endpoint"""
    with STATS_LOCK:
        STATS["total_requests"] += 1

    endpoint = get_endpoint_for_model(req.model) if req.model else get_healthy_endpoint()
    if not endpoint:
        with STATS_LOCK:
            STATS["failed_requests"] += 1
            STATS["last_error"] = f"no_endpoint_for_model:{req.model}"
            save_stats()
        raise HTTPException(503, f"No healthy GPU endpoints available for model: {req.model}")

    # Try a few times on different endpoints (helps with transient failures)
    attempts = 0
    attempted_urls: set[str] = set()
    last_error: Optional[str] = None

    while attempts < 3:
        attempts += 1
        attempted_urls.add(endpoint.get("url"))

        result = call_ollama(
            endpoint,
            req.prompt,
            req.model,
            req.system,
            req.max_tokens
        )

        if result.get("success") and result.get("response"):
            with STATS_LOCK:
                STATS["successful_requests"] += 1
                STATS["tokens_generated"] += result.get("tokens", 0)
                STATS["cost_saved"] += result.get("tokens", 0) * 0.00001
                STATS["last_error"] = None
                STATS["last_success_at"] = datetime.utcnow().isoformat()
                save_stats()
            return {
                "response": result["response"],
                "model": result.get("model", req.model),
                "gpu": result.get("gpu"),
                "tokens": result.get("tokens", 0)
            }

        last_error = result.get("error") or "Generation failed"
        log(f"❌ /generate failed (attempt {attempts}) model={req.model} endpoint={endpoint.get('url')} error={last_error}")

        # Mark endpoint unhealthy after repeated failures
        endpoint["fail_count"] = int(endpoint.get("fail_count", 0)) + 1
        if endpoint.get("provider") != "local" and endpoint["fail_count"] >= 3:
            endpoint["healthy"] = False

        # Pick another endpoint (exclude already tried)
        endpoint = get_endpoint_for_model(
            req.model,
            exclude_urls=attempted_urls,
            allow_local_fallback=(attempts >= 2)
        )
        if not endpoint:
            break

    with STATS_LOCK:
        STATS["failed_requests"] += 1
        STATS["last_error"] = last_error
        save_stats()
    raise HTTPException(502, last_error or "Generation failed")


@app.post("/v1/chat/completions")
def chat_completions(req: ChatRequest):
    """OpenAI-compatible chat completions endpoint"""
    STATS["total_requests"] += 1
    
    endpoint = get_endpoint_for_model(req.model) if req.model else get_healthy_endpoint()
    if not endpoint:
        STATS["failed_requests"] += 1
        raise HTTPException(503, "No healthy GPU endpoints available")
    
    # Convert messages to prompt
    prompt_parts = []
    system_msg = None
    
    for msg in req.messages:
        if msg.role == "system":
            system_msg = msg.content
        elif msg.role == "user":
            prompt_parts.append(f"User: {msg.content}")
        elif msg.role == "assistant":
            prompt_parts.append(f"Assistant: {msg.content}")
    
    prompt = "\n".join(prompt_parts) + "\nAssistant:"
    
    result = call_ollama(endpoint, prompt, req.model, system_msg, req.max_tokens)
    
    if result["success"]:
        STATS["successful_requests"] += 1
        STATS["tokens_generated"] += result.get("tokens", 0)
        STATS["cost_saved"] += result.get("tokens", 0) * 0.00001
        save_stats()
        
        # Return OpenAI-compatible format
        return {
            "id": f"chatcmpl-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "object": "chat.completion",
            "created": int(datetime.utcnow().timestamp()),
            "model": result["model"],
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result["response"]
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": sum(len(m.content.split()) for m in req.messages),
                "completion_tokens": result.get("tokens", 0),
                "total_tokens": sum(len(m.content.split()) for m in req.messages) + result.get("tokens", 0)
            },
            "_gpu": result["gpu"]
        }
    else:
        STATS["failed_requests"] += 1
        raise HTTPException(500, result.get("error", "Generation failed"))


@app.post("/v1/completions")
def completions(req: CompletionRequest):
    """OpenAI-compatible completions endpoint"""
    STATS["total_requests"] += 1
    
    endpoint = get_endpoint_for_model(req.model) if req.model else get_healthy_endpoint()
    if not endpoint:
        STATS["failed_requests"] += 1
        raise HTTPException(503, "No healthy GPU endpoints available")
    
    result = call_ollama(endpoint, req.prompt, req.model, None, req.max_tokens)
    
    if result["success"]:
        STATS["successful_requests"] += 1
        STATS["tokens_generated"] += result.get("tokens", 0)
        STATS["cost_saved"] += result.get("tokens", 0) * 0.00001
        save_stats()
        
        return {
            "id": f"cmpl-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "object": "text_completion",
            "created": int(datetime.utcnow().timestamp()),
            "model": result["model"],
            "choices": [{
                "text": result["response"],
                "index": 0,
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(req.prompt.split()),
                "completion_tokens": result.get("tokens", 0),
                "total_tokens": len(req.prompt.split()) + result.get("tokens", 0)
            }
        }
    else:
        STATS["failed_requests"] += 1
        raise HTTPException(500, result.get("error", "Generation failed"))


if __name__ == "__main__":
    log("🔗 GPU Bridge starting on port 8400")
    uvicorn.run(app, host="0.0.0.0", port=8400)
