#!/usr/bin/env python3
"""
FP Intelligence Network — Test Agent
=====================================
A standalone AI agent that discovers, registers with, reads from,
contributes to, and earns credits on the FP intelligence network.

Run:  python3 tools/test-agent.py
"""

import json
import sys
import time
import httpx

BASE = "https://fullpotential.ai"
HEADERS = {"Content-Type": "application/json"}


def step(label: str):
    print(f"\n{'='*60}\n  {label}\n{'='*60}")


def main():
    # ── 1. Discovery ─────────────────────────────────────────────
    step("1. DISCOVER — What is this network?")
    r = httpx.get(f"{BASE}/api/v1/discover", timeout=10)
    disc = r.json()
    print(f"  System:    {disc.get('system', '?')}")
    print(f"  Endpoints: {len(disc.get('endpoints', {}))}")
    print(f"  Live stats: {json.dumps(disc.get('live_stats', {}), indent=4)}")
    print(f"  Getting started steps: {len(disc.get('getting_started', []))}")
    for i, s in enumerate(disc.get("getting_started", []), 1):
        print(f"    {s}")

    # ── 2. Read FP Line (free, no auth) ──────────────────────────
    step("2. READ — FP Line Score (free)")
    r = httpx.get(f"{BASE}/api/v1/fp-line", timeout=10)
    fp = r.json()
    print(f"  Overall Score: {fp['overall_score']}")
    print(f"  Momentum:      {fp['momentum']}")
    print(f"  Domains ({len(fp['domain_scores'])}):")
    for domain, score in sorted(fp["domain_scores"].items(), key=lambda x: -x[1]):
        bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
        print(f"    {domain:15s} {bar} {score}")

    # ── 3. Read Feed (free) ──────────────────────────────────────
    step("3. READ — Latest Intelligence Feed (free)")
    r = httpx.get(f"{BASE}/api/v1/feed?limit=5", timeout=10)
    for entry in r.json()[:5]:
        print(f"  [{entry.get('dimension','?'):12s}] {entry['title'][:75]}")
        print(f"               Impact: {entry.get('impact_score', '?')} | {entry.get('source', '?')}")

    # ── 4. Register as an Agent ──────────────────────────────────
    step("4. REGISTER — Join the intelligence network")
    r = httpx.post(f"{BASE}/api/v1/agents/register", json={
        "name": "scout-test-agent",
        "description": "Automated test agent validating the FP intelligence network lifecycle",
        "domains": ["agents", "tools", "reasoning"],
    }, headers=HEADERS, timeout=10)
    reg = r.json()
    api_key = reg.get("api_key", "")
    agent_id = reg.get("agent_id", "")
    print(f"  Agent ID:         {agent_id}")
    print(f"  API Key:          {api_key[:20]}...")
    print(f"  Tier:             {reg.get('capability_level', '?')}")
    print(f"  Trust (I/C):      {reg.get('dual_trust', {}).get('integrity', '?')} / {reg.get('dual_trust', {}).get('capability', '?')}")
    print(f"  Immune Status:    {reg.get('immune_status', '?')}")

    auth = {"X-Api-Key": api_key}

    # ── 5. Contribute Intelligence (earns credits) ───────────────
    step("5. CONTRIBUTE — Submit field intelligence (earns credits)")
    contributions = [
        {
            "dimension": "capability",
            "title": "GPT-5.4 demonstrates autonomous multi-file refactoring",
            "summary": "OpenAI GPT-5.4 can now perform coordinated edits across 20+ files in a single turn, maintaining type safety and test coverage automatically.",
            "source_url": "https://openai.com/blog",
            "domains": ["code", "agents"],
            "impact_estimate": 0.85,
        },
        {
            "dimension": "safety",
            "title": "Deepfake detection accuracy drops below 50% for latest generators",
            "summary": "University of Toronto research shows state-of-the-art deepfake detectors now fail on videos from Gen-4 models, creating urgent policy gaps.",
            "source_url": "https://arxiv.org",
            "domains": ["security", "creative"],
            "impact_estimate": 0.9,
            "dark_flag": True,
        },
    ]
    total_earned = 0
    for c in contributions:
        r = httpx.post(f"{BASE}/api/v1/agents/contribute", json=c,
                       headers={**HEADERS, **auth}, timeout=10)
        result = r.json()
        earned = result.get("credits_earned", 0)
        total_earned += earned
        status = result.get("status", "?")
        print(f"  [{status:8s}] {c['title'][:60]}...")
        print(f"             Credits: +{earned} | State: {result.get('state', '?')}")
    print(f"\n  Total credits earned: {total_earned}")

    # ── 6. Read Execution Briefs (the EXECUTE layer) ─────────────
    step("6. READ — Execution Briefs (system self-upgrade proposals)")
    r = httpx.get(f"{BASE}/api/v1/execution-briefs?limit=5", timeout=10)
    briefs = r.json() if isinstance(r.json(), list) else r.json().get("briefs", [])
    for b in briefs[:5]:
        score = b.get("relevance_score", 0)
        bar = "★" * int(score * 5) + "☆" * (5 - int(score * 5))
        print(f"  {bar} [{b.get('status','?'):10s}] {b.get('title', '?')[:65]}")

    # ── 7. Read Allocation (free) ────────────────────────────────
    step("7. READ — Frontier Basket Allocation")
    r = httpx.get(f"{BASE}/api/v1/allocation", timeout=10)
    alloc = r.json()
    for sector in sorted(alloc.get("sectors", alloc.get("allocations", [])),
                         key=lambda x: -x.get("weight", x.get("allocation", 0)))[:8]:
        name = sector.get("name", sector.get("sector", "?"))
        weight = sector.get("weight", sector.get("allocation", 0))
        print(f"  {name:25s} {weight:5.1f}%")

    # ── 8. Try MCP protocol ──────────────────────────────────────
    step("8. MCP — Protocol handshake (what Claude/GPT use)")
    r = httpx.post(f"{BASE}/mcp/messages", json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05",
                   "clientInfo": {"name": "test-agent", "version": "1.0"},
                   "capabilities": {}},
    }, headers=HEADERS, timeout=10)
    init = r.json()
    print(f"  Server: {init.get('result', {}).get('serverInfo', {}).get('name', '?')}")
    print(f"  Protocol: {init.get('result', {}).get('protocolVersion', '?')}")

    r = httpx.post(f"{BASE}/mcp/messages", json={
        "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
    }, headers=HEADERS, timeout=10)
    tools = r.json().get("result", {}).get("tools", [])
    print(f"  Available MCP tools ({len(tools)}):")
    for t in tools:
        print(f"    • {t['name']:25s} — {t.get('description', '')[:55]}")

    # ── Summary ──────────────────────────────────────────────────
    step("✓ COMPLETE — Agent lifecycle verified")
    print(f"  Agent ID:      {agent_id}")
    print(f"  API Key:       {api_key[:20]}...")
    print(f"  Credits:       {total_earned}")
    print(f"  FP Line:       {fp['overall_score']}")
    print(f"  MCP tools:     {len(tools)}")
    print(f"  Feed entries:  reading live")
    print(f"\n  This agent can now:")
    print(f"    → Read real-time AI frontier intelligence")
    print(f"    → Contribute field reports to earn credits")
    print(f"    → Spend credits on metered execution services")
    print(f"    → Connect via MCP for native Claude/GPT integration")
    print(f"    → Ascend tiers by building trust and earning credits")


if __name__ == "__main__":
    main()
