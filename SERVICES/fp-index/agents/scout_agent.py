#!/usr/bin/env python3
"""
Scout Agent — Autonomous FP Intelligence Network Participant
=============================================================

A self-running agent that:
1. Registers with the FP Intelligence Network (once)
2. Every cycle: reads the FP Line, identifies gaps, scouts for new intelligence
3. Contributes findings back to the network (earns credits)
4. Logs its activity for the EXECUTE narration engine

Runs on a 2-hour cycle via systemd timer or cron.
Persists its identity in ~/.fpai-scout.json

Usage:
    python3 scout_agent.py              # Run one cycle
    python3 scout_agent.py --register   # Force re-registration
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCOUT] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("scout")

BASE_URL = os.getenv("FP_BASE_URL", "https://fullpotential.ai")
STATE_FILE = Path(os.getenv("SCOUT_STATE", "/opt/fpai/services/fp-index/agents/.scout-state.json"))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

SCOUT_QUERIES = [
    ("mcp server language:python", "tools", "MCP server implementations"),
    ("ai agent framework", "agents", "Agent framework releases"),
    ("llm benchmark evaluation", "reasoning", "LLM evaluation and benchmarks"),
    ("ai safety alignment", "security", "AI safety research"),
    ("text to video generation", "creative", "Generative media advances"),
    ("ai medical diagnosis", "health", "AI in healthcare"),
    ("autonomous coding agent", "code", "Autonomous code generation"),
    ("ai job automation displacement", "general", "Labor displacement signals"),
]


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def register(client: httpx.Client) -> dict:
    """Register with the FP Intelligence Network."""
    log.info("Registering with FP Intelligence Network...")
    r = client.post(f"{BASE_URL}/api/v1/agents/register", json={
        "name": "fp-scout-alpha",
        "description": "Autonomous scout agent. Patrols GitHub, arXiv, and news for AI frontier signals. "
                       "Contributes findings to the FP Intelligence Network every 2 hours.",
        "domains": ["agents", "tools", "reasoning", "code", "security"],
    })
    r.raise_for_status()
    data = r.json()
    log.info(f"Registered: agent_id={data['agent_id']} tier={data.get('capability_level')}")
    return data


def read_fp_line(client: httpx.Client) -> dict:
    """Read the current FP Line to understand network state."""
    r = client.get(f"{BASE_URL}/api/v1/fp-line")
    r.raise_for_status()
    return r.json()


def read_feed(client: httpx.Client, limit: int = 20) -> list:
    """Read the latest feed to avoid duplicate contributions."""
    r = client.get(f"{BASE_URL}/api/v1/feed", params={"limit": limit})
    r.raise_for_status()
    return r.json()


def scout_github(client: httpx.Client, query: str, max_results: int = 5) -> list:
    """Scout GitHub for new repos matching a query."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        r = client.get(
            "https://api.github.com/search/repositories",
            params={"q": query, "sort": "updated", "order": "desc", "per_page": max_results},
            headers=headers,
            timeout=15,
        )
        if r.status_code == 403:
            log.warning(f"GitHub rate limited on query: {query}")
            return []
        if r.status_code != 200:
            return []

        results = []
        for repo in r.json().get("items", [])[:max_results]:
            results.append({
                "title": f"{repo['full_name']} — {repo.get('description', 'No description')[:120]}",
                "url": repo["html_url"],
                "stars": repo.get("stargazers_count", 0),
                "updated": repo.get("pushed_at", ""),
                "language": repo.get("language", ""),
            })
        return results
    except Exception as e:
        log.warning(f"GitHub scout error for '{query}': {e}")
        return []


def contribute(client: httpx.Client, api_key: str, entry: dict) -> dict:
    """Contribute a finding to the network."""
    try:
        r = client.post(
            f"{BASE_URL}/api/v1/agents/contribute",
            json=entry,
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning(f"Contribution failed: {e}")
        return {"status": "error", "error": str(e)}


def run_cycle(state: dict) -> dict:
    """Run one scout cycle: read → scout → contribute → report."""
    client = httpx.Client(timeout=15)
    cycle_start = datetime.now(timezone.utc)

    # Ensure registered
    if "api_key" not in state:
        reg = register(client)
        state["agent_id"] = reg["agent_id"]
        state["api_key"] = reg["api_key"]
        state["registered_at"] = cycle_start.isoformat()
        save_state(state)

    api_key = state["api_key"]

    # 1. Read current network state
    log.info("Reading FP Line...")
    fp = read_fp_line(client)
    log.info(f"FP Line: {fp['overall_score']} | Domains: {len(fp.get('domain_scores', {}))}")

    # 2. Read existing feed to deduplicate
    log.info("Reading existing feed for dedup...")
    existing = read_feed(client, limit=100)
    existing_titles = {e.get("title", "").lower()[:60] for e in existing}
    existing_urls = {e.get("source_url", "") for e in existing if e.get("source_url")}
    seen_urls = set(state.get("contributed_urls", [])[-500:])

    # 3. Identify weak domains to prioritize
    domain_scores = fp.get("domain_scores", {})
    weak_domains = sorted(
        [(d, s) for d, s in domain_scores.items() if d != "displacement"],
        key=lambda x: x[1],
    )[:5]
    log.info(f"Weakest domains: {', '.join(f'{d}={s}' for d, s in weak_domains)}")

    # 4. Scout GitHub
    contributions_made = 0
    credits_earned = 0.0

    for query, domain, description in SCOUT_QUERIES:
        log.info(f"Scouting: {description} ({query})...")
        repos = scout_github(client, query, max_results=3)
        time.sleep(1)

        for repo in repos:
            url = repo["url"]
            title_key = repo["title"].lower()[:60]

            if url in existing_urls or url in seen_urls or title_key in existing_titles:
                continue
            if repo["stars"] < 5:
                continue

            entry = {
                "dimension": "capability",
                "title": repo["title"][:200],
                "summary": f"GitHub repository with {repo['stars']} stars, "
                           f"language: {repo['language'] or 'mixed'}, "
                           f"last updated: {repo['updated'][:10]}. "
                           f"Scout category: {description}.",
                "source_url": url,
                "domains": [domain],
                "impact_estimate": min(0.3 + repo["stars"] / 1000, 0.9),
            }

            result = contribute(client, api_key, entry)
            if result.get("status") == "accepted":
                contributions_made += 1
                credits_earned += result.get("credits_earned", 0)
                seen_urls.add(url)
                existing_titles.add(title_key)
                log.info(f"  ✓ Contributed: {repo['title'][:60]}... (+{result.get('credits_earned', 0)} credits)")
            else:
                log.info(f"  ✗ Rejected: {result.get('error', result.get('status', '?'))}")

            if contributions_made >= 10:
                break

        if contributions_made >= 10:
            break

    # 5. Update state
    state["contributed_urls"] = list(seen_urls)[-500:]
    state["last_cycle"] = cycle_start.isoformat()
    state["total_cycles"] = state.get("total_cycles", 0) + 1
    state["total_contributions"] = state.get("total_contributions", 0) + contributions_made
    state["total_credits"] = state.get("total_credits", 0) + credits_earned

    log.info(
        f"Cycle complete: {contributions_made} contributions, "
        f"+{credits_earned:.3f} credits, "
        f"lifetime: {state['total_contributions']} contributions / "
        f"{state['total_credits']:.3f} credits over {state['total_cycles']} cycles"
    )

    save_state(state)
    client.close()
    return state


def main():
    parser = argparse.ArgumentParser(description="FP Intelligence Network Scout Agent")
    parser.add_argument("--register", action="store_true", help="Force re-registration")
    args = parser.parse_args()

    state = load_state()
    if args.register:
        state.pop("api_key", None)
        state.pop("agent_id", None)

    run_cycle(state)


if __name__ == "__main__":
    main()
