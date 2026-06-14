#!/usr/bin/env python3
"""AI Intelligence Scanner — Daily automated scan of the AI landscape.

Monitors sources for new tools, models, and frameworks relevant to our stack.
Scores each item and writes a digest to the memory bus.

Sources:
  - GitHub trending (AI/LLM/agents tags)
  - HuggingFace trending models
  - Anthropic/OpenAI/Google blog RSS
  - OpenClaw releases
  - LangChain/CrewAI/AutoGen releases
  - ProductHunt AI category
  - Hacker News AI stories

Usage:
  intel-scanner.py scan       — Run full scan, score, write to bus
  intel-scanner.py latest     — Show latest digest
"""

import json
import os
import sys
import re
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

BUS_URL = "http://127.0.0.1:8195"
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DIGEST_DIR = Path("/opt/fpai/intel-scanner/digests")
DIGEST_DIR.mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (compatible; FPAI-Scanner/1.0)"
OUR_STACK = [
    "OpenClaw (AI agent framework)",
    "Anthropic Claude (primary LLM)",
    "Ollama (local LLM)",
    "Python/FastAPI (services)",
    "Playwright (browser automation)",
    "Telegram Bot API",
    "Resend/Brevo (email)",
    "SQLite (databases)",
    "Docker (containerization)",
    "Nginx (reverse proxy)",
    "Systemd (service management)",
]


def fetch_json(url, headers=None, timeout=15):
    try:
        resp = requests.get(url, headers={**(headers or {}), "User-Agent": UA}, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def fetch_text(url, timeout=15):
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return None


def scan_github_trending():
    """GitHub trending AI/LLM repos from the last 3 days."""
    items = []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
    for query in ["ai+agents", "llm+framework", "ai+automation"]:
        data = fetch_json(
            f"https://api.github.com/search/repositories?q=stars:>50+pushed:>{cutoff}+topic:{query}&sort=stars&order=desc&per_page=5",
            headers={"Accept": "application/vnd.github+json"}
        )
        if data:
            for repo in data.get("items", [])[:5]:
                items.append({
                    "source": "github",
                    "title": repo["full_name"],
                    "description": (repo.get("description") or "")[:200],
                    "url": repo["html_url"],
                    "stars": repo["stargazers_count"],
                    "language": repo.get("language", ""),
                    "updated": repo.get("pushed_at", ""),
                })
    return items


def scan_huggingface_trending():
    """HuggingFace trending models."""
    items = []
    data = fetch_json("https://huggingface.co/api/trending")
    if data:
        for model in (data if isinstance(data, list) else data.get("recentlyTrending", []))[:10]:
            mid = model.get("repoData", {}).get("id", "") if isinstance(model, dict) else ""
            if not mid and isinstance(model, dict):
                mid = model.get("id", "")
            items.append({
                "source": "huggingface",
                "title": mid,
                "description": model.get("repoData", {}).get("description", "")[:200] if isinstance(model, dict) else "",
                "url": f"https://huggingface.co/{mid}",
                "likes": model.get("repoData", {}).get("likes", 0) if isinstance(model, dict) else 0,
            })
    return items


def scan_hacker_news():
    """Top HN stories about AI/LLM."""
    items = []
    data = fetch_json("https://hn.algolia.com/api/v1/search?query=AI+LLM+agents&tags=story&hitsPerPage=10")
    if data:
        for hit in data.get("hits", [])[:10]:
            items.append({
                "source": "hackernews",
                "title": hit.get("title", ""),
                "url": hit.get("url", f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"),
                "points": hit.get("points", 0),
                "comments": hit.get("num_comments", 0),
            })
    return items


def scan_github_releases():
    """Check releases for key frameworks."""
    repos = [
        "anthropics/anthropic-sdk-python",
        "openai/openai-python",
        "langchain-ai/langchain",
        "microsoft/autogen",
        "joaomdmoura/crewAI",
        "ollama/ollama",
    ]
    items = []
    for repo in repos:
        data = fetch_json(f"https://api.github.com/repos/{repo}/releases?per_page=1",
                          headers={"Accept": "application/vnd.github+json"})
        if data and len(data) > 0:
            rel = data[0]
            pub = rel.get("published_at", "")
            if pub:
                pub_date = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - pub_date < timedelta(days=7):
                    items.append({
                        "source": "github_release",
                        "title": f"{repo} {rel.get('tag_name', '')}",
                        "description": (rel.get("body") or "")[:300],
                        "url": rel.get("html_url", ""),
                        "published": pub,
                    })
    return items


def scan_producthunt():
    """ProductHunt AI category (public API)."""
    items = []
    # PH doesn't have a simple public API without auth, use their topics page
    text = fetch_text("https://www.producthunt.com/topics/artificial-intelligence")
    if text:
        titles = re.findall(r'<h3[^>]*>([^<]+)</h3>', text)[:5]
        for t in titles:
            items.append({
                "source": "producthunt",
                "title": t.strip(),
                "url": "https://www.producthunt.com/topics/artificial-intelligence",
            })
    return items


def score_items_with_claude(items):
    """Use Claude to score relevance and generate recommendations."""
    if not ANTHROPIC_KEY or not items:
        # Fallback: simple keyword scoring
        scored = []
        high_relevance = ["agent", "openclaw", "anthropic", "claude", "ollama", "telegram",
                          "browser", "automation", "orchestrat", "multi-agent", "tool-use",
                          "function-call", "mcp", "cursor"]
        medium_relevance = ["llm", "gpt", "langchain", "crewai", "autogen", "rag",
                            "embedding", "fine-tun", "lora", "deploy"]
        for item in items:
            text = (item.get("title", "") + " " + item.get("description", "")).lower()
            if any(k in text for k in high_relevance):
                item["relevance"] = "high"
                item["recommendation"] = "investigate for integration"
            elif any(k in text for k in medium_relevance):
                item["relevance"] = "medium"
                item["recommendation"] = "watch"
            else:
                item["relevance"] = "low"
                item["recommendation"] = "ignore"
            scored.append(item)
        return scored

    prompt = f"""You are an AI infrastructure analyst for the Full Potential AI ecosystem.

OUR STACK:
{json.dumps(OUR_STACK, indent=2)}

Score each item below for relevance to our stack. For each, provide:
- relevance: high, medium, low, or none
- recommendation: "integrate_now", "investigate", "watch", or "ignore"  
- reason: one sentence why

Items to score:
{json.dumps(items, indent=2)}

Respond as JSON array with each item having added fields: relevance, recommendation, reason."""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        if resp.status_code == 200:
            text = resp.json()["content"][0]["text"]
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                scored = json.loads(json_match.group())
                return scored
    except Exception as e:
        print(f"  Claude scoring failed: {e}")

    return items


def write_to_bus(digest):
    """Write the digest to the memory bus."""
    try:
        requests.post(f"{BUS_URL}/bus/messages", json={
            "from": "intel_scanner",
            "to": "all",
            "type": "intelligence_digest",
            "priority": "medium",
            "content": digest,
            "thread_id": f"intel_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        }, timeout=10)
    except Exception:
        pass


def run_scan():
    """Run the full intelligence scan."""
    print(f"AI Intelligence Scan — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    all_items = []

    print("\n[1/5] GitHub trending AI repos...")
    gh = scan_github_trending()
    print(f"  Found {len(gh)} items")
    all_items.extend(gh)

    print("[2/5] HuggingFace trending models...")
    hf = scan_huggingface_trending()
    print(f"  Found {len(hf)} items")
    all_items.extend(hf)

    print("[3/5] Hacker News AI stories...")
    hn = scan_hacker_news()
    print(f"  Found {len(hn)} items")
    all_items.extend(hn)

    print("[4/5] Framework releases...")
    rel = scan_github_releases()
    print(f"  Found {len(rel)} new releases")
    all_items.extend(rel)

    print("[5/5] ProductHunt AI...")
    ph = scan_producthunt()
    print(f"  Found {len(ph)} items")
    all_items.extend(ph)

    # Deduplicate by title
    seen = set()
    unique = []
    for item in all_items:
        key = item.get("title", "").lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    all_items = unique

    print(f"\nTotal unique items: {len(all_items)}")
    print("Scoring relevance...")

    scored = score_items_with_claude(all_items)

    # Sort by relevance
    order = {"high": 0, "medium": 1, "low": 2, "none": 3}
    scored.sort(key=lambda x: order.get(x.get("relevance", "none"), 3))

    # Build digest
    high = [i for i in scored if i.get("relevance") == "high"]
    medium = [i for i in scored if i.get("relevance") == "medium"]

    digest = {
        "scan_date": datetime.now(timezone.utc).isoformat(),
        "total_items_scanned": len(scored),
        "high_relevance": len(high),
        "medium_relevance": len(medium),
        "items": scored,
        "summary": f"Scanned {len(scored)} items. {len(high)} high relevance, {len(medium)} medium.",
    }

    # Save to disk
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    digest_file = DIGEST_DIR / f"digest_{date_str}.json"
    digest_file.write_text(json.dumps(digest, indent=2, default=str))

    # Write to bus
    write_to_bus(digest)

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"DIGEST SUMMARY")
    print(f"{'=' * 60}")

    if high:
        print(f"\n🔴 HIGH RELEVANCE ({len(high)}):")
        for i in high:
            print(f"  [{i.get('source', '?'):15}] {i.get('title', '?')}")
            if i.get("reason"):
                print(f"    → {i['reason']}")
            if i.get("url"):
                print(f"    {i['url']}")

    if medium:
        print(f"\n🟡 MEDIUM RELEVANCE ({len(medium)}):")
        for i in medium[:10]:
            print(f"  [{i.get('source', '?'):15}] {i.get('title', '?')}")
            if i.get("reason"):
                print(f"    → {i['reason']}")

    print(f"\nDigest saved to {digest_file}")
    print(f"Written to memory bus")


def show_latest():
    """Show the latest digest."""
    digests = sorted(DIGEST_DIR.glob("digest_*.json"), reverse=True)
    if not digests:
        print("No digests yet. Run: intel-scanner.py scan")
        return
    data = json.loads(digests[0].read_text())
    print(f"Latest digest: {digests[0].name}")
    print(f"Scanned: {data.get('total_items_scanned', 0)} items")
    print(f"High relevance: {data.get('high_relevance', 0)}")
    print(f"Medium relevance: {data.get('medium_relevance', 0)}")
    for item in data.get("items", []):
        if item.get("relevance") in ("high", "medium"):
            print(f"  [{item.get('relevance', '?'):6}] [{item.get('source', '?'):15}] {item.get('title', '?')}")


if __name__ == "__main__":
    # Load .env
    env_file = Path("/opt/fpai/cora-loop/.env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    if cmd == "scan":
        run_scan()
    elif cmd == "latest":
        show_latest()
    else:
        print("Usage: intel-scanner.py [scan|latest]")
