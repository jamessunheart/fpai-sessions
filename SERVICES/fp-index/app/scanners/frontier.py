"""
AI Frontier Scanners
====================

Expanded scanner system for the Full Potential Index.
Monitors the AI frontier across multiple sources and dimensions.

Sources:
  - GitHub trending + releases (AI/agents/LLM)
  - HuggingFace trending models + new spaces
  - Hacker News top AI stories
  - arXiv recent AI papers
  - Major AI provider blogs (OpenAI, Anthropic, Google, Meta)
  - ProductHunt AI category
  - AI security/incident feeds
"""

import hashlib
import logging
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
import feedparser

from ..models.schema import (
    IndexEntry, Dimension, SourceType, SourceCategory, Domain, Alignment,
    ReadinessLevel
)

logger = logging.getLogger("fp_index.scanners")

UA = "Mozilla/5.0 (compatible; FPIndex/1.0; +https://fullpotential.ai)"
SCAN_TIMEOUT = 20.0

_GH_TOKEN = os.getenv("GITHUB_TOKEN", "")
GH_HEADERS = {"Accept": "application/vnd.github+json"}
if _GH_TOKEN:
    GH_HEADERS["Authorization"] = f"Bearer {_GH_TOKEN}"
    logger.info("GitHub API: authenticated (5,000 req/hr)")
else:
    logger.info("GitHub API: unauthenticated (60 req/hr) — set GITHUB_TOKEN for higher limits")


def _entry_id(source: str, title: str) -> str:
    raw = f"{source}:{title}:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _classify_domains(text: str) -> list[Domain]:
    text_lower = text.lower()
    domains = []
    patterns = {
        Domain.REASONING: ["reason", "chain-of-thought", "cot", "logic", "math", "theorem"],
        Domain.CODE: ["code", "programming", "developer", "ide", "compiler", "debug", "copilot"],
        Domain.VISION: ["vision", "image", "video", "visual", "multimodal", "ocr", "diffusion"],
        Domain.AUDIO: ["audio", "speech", "voice", "tts", "stt", "music", "sound", "whisper", "transcri", "diarization"],
        Domain.AGENTS: ["agent", "autonomous", "tool-use", "function-call", "mcp", "orchestrat", "multi-agent", "agentic", "agent-native"],
        Domain.TOOLS: ["api", "sdk", "framework", "library", "plugin", "integration", "tool", "router", "gateway", "infrastructure", "platform", "middleware"],
        Domain.SCIENCE: ["research", "paper", "arxiv", "benchmark", "dataset", "scientific"],
        Domain.CREATIVE: ["creative", "art", "design", "writing", "story", "generative"],
        Domain.SECURITY: ["security", "safety", "alignment", "jailbreak", "vulnerability", "exploit", "deepfake"],
        Domain.FINANCE: ["trading", "finance", "crypto", "defi", "market", "predict", "hedge fund", "portfolio", "usdc", "stablecoin"],
        Domain.HEALTH: ["health", "medical", "drug", "clinical", "diagnosis", "biotech"],
        Domain.EDUCATION: ["education", "learning", "tutor", "course", "student"],
    }
    for domain, keywords in patterns.items():
        if any(k in text_lower for k in keywords):
            domains.append(domain)
    return domains or [Domain.GENERAL]


def _classify_alignment(text: str) -> Alignment:
    text_lower = text.lower()
    dark_signals = [
        "deepfake", "scam", "phishing", "exploit", "malware", "surveillance",
        "manipulation", "weaponiz", "misinformation", "disinformation",
        "fraud", "impersonat", "attack", "breach", "data leak"
    ]
    light_signals = [
        "safety", "alignment", "open-source", "accessibility", "privacy",
        "protect", "healthcare", "education", "sustainability", "humanitarian",
        "wellbeing", "wellness", "democratiz", "transparent"
    ]
    dark_count = sum(1 for s in dark_signals if s in text_lower)
    light_count = sum(1 for s in light_signals if s in text_lower)
    if dark_count > light_count and dark_count >= 2:
        return Alignment.DARK
    if light_count > dark_count and light_count >= 2:
        return Alignment.LIGHT
    return Alignment.NEUTRAL


def _estimate_impact(item: dict, source: str) -> float:
    """Estimate frontier impact 0-1 based on available signals."""
    score = 0.3
    stars = item.get("stars", 0) or item.get("likes", 0) or 0
    points = item.get("points", 0) or 0
    if stars > 10000:
        score += 0.3
    elif stars > 1000:
        score += 0.2
    elif stars > 100:
        score += 0.1
    if points > 500:
        score += 0.2
    elif points > 100:
        score += 0.1

    text = (item.get("title", "") + " " + item.get("description", "")).lower()
    frontier_signals = [
        "breakthrough", "state-of-the-art", "sota", "first", "new model",
        "gpt-5", "claude", "gemini", "llama", "o3", "o4",
        "autonomous", "agi", "superintelligence", "benchmark record",
        "agent-native", "smart routing", "llm router", "ai infrastructure",
        "zero api key", "micropayment", "x402", "openclaw",
    ]
    if any(s in text for s in frontier_signals):
        score += 0.15

    if source in ("model_release", "github_release"):
        score += 0.1

    return min(score, 1.0)


# ─── GitHub ───────────────────────────────────────────────────────────────────

async def scan_github_trending(client: httpx.AsyncClient) -> list[IndexEntry]:
    entries = []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
    queries = ["ai+agents", "llm+framework", "ai+automation", "ai+tools", "machine+learning"]

    for query in queries:
        try:
            url = (
                f"https://api.github.com/search/repositories"
                f"?q=stars:>50+pushed:>{cutoff}+topic:{query}&sort=stars&order=desc&per_page=5"
            )
            resp = await client.get(url, headers=GH_HEADERS)
            if resp.status_code != 200:
                continue
            data = resp.json()
            for repo in data.get("items", [])[:5]:
                title = repo["full_name"]
                desc = (repo.get("description") or "")[:300]
                text = f"{title} {desc}"
                entries.append(IndexEntry(
                    id=_entry_id("github", title),
                    dimension=Dimension.CAPABILITY,
                    title=title,
                    summary=desc,
                    source="github",
                    source_url=repo["html_url"],
                    source_type=SourceType.TOOL_LAUNCH,
                    domains=_classify_domains(text),
                    alignment=_classify_alignment(text),
                    impact_score=_estimate_impact(repo, "github"),
                    entities=[repo.get("owner", {}).get("login", "")],
                    tags=[repo.get("language", ""), "github-trending"],
                    raw_data={"stars": repo["stargazers_count"], "language": repo.get("language")},
                ))
        except Exception as e:
            logger.warning(f"GitHub trending scan failed for {query}: {e}")
    return entries


async def scan_github_releases(client: httpx.AsyncClient) -> list[IndexEntry]:
    repos = [
        "anthropics/anthropic-sdk-python", "openai/openai-python",
        "langchain-ai/langchain", "microsoft/autogen",
        "joaomdmoura/crewAI", "ollama/ollama",
        "huggingface/transformers", "meta-llama/llama",
        "google/generative-ai-python", "run-llama/llama_index",
    ]
    entries = []
    for repo in repos:
        try:
            resp = await client.get(
                f"https://api.github.com/repos/{repo}/releases?per_page=1",
                headers=GH_HEADERS
            )
            if resp.status_code != 200 or not resp.json():
                continue
            rel = resp.json()[0]
            pub = rel.get("published_at", "")
            if not pub:
                continue
            pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - pub_dt > timedelta(days=7):
                continue
            title = f"{repo} {rel.get('tag_name', '')}"
            desc = (rel.get("body") or "")[:400]
            entries.append(IndexEntry(
                id=_entry_id("github_release", title),
                dimension=Dimension.CAPABILITY,
                title=title,
                summary=desc,
                source="github_release",
                source_url=rel.get("html_url", ""),
                source_type=SourceType.TOOL_LAUNCH,
                domains=_classify_domains(f"{title} {desc}"),
                impact_score=_estimate_impact({"title": title, "description": desc}, "github_release"),
                entities=[repo.split("/")[0]],
                tags=["release", "framework"],
                published_at=pub,
            ))
        except Exception as e:
            logger.warning(f"GitHub release scan failed for {repo}: {e}")
    return entries


# ─── HuggingFace ──────────────────────────────────────────────────────────────

async def scan_huggingface(client: httpx.AsyncClient) -> list[IndexEntry]:
    entries = []
    try:
        resp = await client.get("https://huggingface.co/api/trending")
        if resp.status_code != 200:
            return entries
        data = resp.json()
        models = data if isinstance(data, list) else data.get("recentlyTrending", [])
        for model in models[:15]:
            repo_data = model.get("repoData", {}) if isinstance(model, dict) else {}
            mid = repo_data.get("id", "") or (model.get("id", "") if isinstance(model, dict) else "")
            if not mid:
                continue
            desc = (repo_data.get("description") or "")[:300]
            likes = repo_data.get("likes", 0)
            entries.append(IndexEntry(
                id=_entry_id("huggingface", mid),
                dimension=Dimension.CAPABILITY,
                title=mid,
                summary=desc,
                source="huggingface",
                source_url=f"https://huggingface.co/{mid}",
                source_type=SourceType.MODEL_RELEASE,
                domains=_classify_domains(f"{mid} {desc}"),
                impact_score=_estimate_impact({"title": mid, "description": desc, "likes": likes}, "huggingface"),
                entities=[mid.split("/")[0] if "/" in mid else mid],
                tags=["model", "huggingface-trending"],
                raw_data={"likes": likes},
            ))
    except Exception as e:
        logger.warning(f"HuggingFace scan failed: {e}")
    return entries


# ─── Hacker News ──────────────────────────────────────────────────────────────

async def scan_hackernews(client: httpx.AsyncClient) -> list[IndexEntry]:
    entries = []
    queries = ["AI LLM agents", "artificial intelligence", "machine learning model"]
    for query in queries:
        try:
            resp = await client.get(
                f"https://hn.algolia.com/api/v1/search?query={query}&tags=story&hitsPerPage=10"
            )
            if resp.status_code != 200:
                continue
            for hit in resp.json().get("hits", [])[:10]:
                title = hit.get("title", "")
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                entries.append(IndexEntry(
                    id=_entry_id("hackernews", title),
                    dimension=Dimension.ACTIVITY,
                    title=title,
                    summary=f"HN discussion: {hit.get('num_comments', 0)} comments, {hit.get('points', 0)} points",
                    source="hackernews",
                    source_url=url,
                    source_type=SourceType.NEWS,
                    domains=_classify_domains(title),
                    alignment=_classify_alignment(title),
                    impact_score=_estimate_impact(hit, "hackernews"),
                    tags=["discussion", "community"],
                    raw_data={"points": hit.get("points", 0), "comments": hit.get("num_comments", 0)},
                ))
        except Exception as e:
            logger.warning(f"HN scan failed for {query}: {e}")
    return entries


# ─── arXiv ────────────────────────────────────────────────────────────────────

async def scan_arxiv(client: httpx.AsyncClient) -> list[IndexEntry]:
    entries = []
    categories = ["cs.AI", "cs.CL", "cs.LG", "cs.MA"]
    for cat in categories:
        try:
            url = f"http://export.arxiv.org/api/query?search_query=cat:{cat}&sortBy=submittedDate&sortOrder=descending&max_results=5"
            resp = await client.get(url)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:5]:
                title = entry.get("title", "").replace("\n", " ").strip()
                summary = entry.get("summary", "").replace("\n", " ")[:300]
                link = entry.get("link", "")
                entries.append(IndexEntry(
                    id=_entry_id("arxiv", title),
                    dimension=Dimension.INTELLIGENCE,
                    title=title,
                    summary=summary,
                    source="arxiv",
                    source_url=link,
                    source_type=SourceType.RESEARCH_PAPER,
                    domains=_classify_domains(f"{title} {summary}"),
                    impact_score=0.4,
                    entities=[a.get("name", "") for a in entry.get("authors", [])[:3]],
                    tags=["research", "paper", cat],
                    published_at=entry.get("published"),
                ))
        except Exception as e:
            logger.warning(f"arXiv scan failed for {cat}: {e}")
    return entries


# ─── AI Provider Blogs (RSS) ─────────────────────────────────────────────────

async def scan_ai_blogs(client: httpx.AsyncClient) -> list[IndexEntry]:
    feeds = {
        "openai": "https://openai.com/blog/rss.xml",
        "anthropic": "https://www.anthropic.com/rss.xml",
        "google_ai": "https://blog.google/technology/ai/rss/",
        "meta_ai": "https://ai.meta.com/blog/rss/",
    }
    entries = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    for provider, feed_url in feeds.items():
        try:
            resp = await client.get(feed_url)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.text)
            for item in feed.entries[:5]:
                published = item.get("published_parsed") or item.get("updated_parsed")
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                    pub_str = pub_dt.isoformat()
                else:
                    pub_str = None

                title = item.get("title", "").strip()
                summary = (item.get("summary") or item.get("description") or "")[:300]
                summary = re.sub(r'<[^>]+>', '', summary).strip()
                link = item.get("link", "")

                entries.append(IndexEntry(
                    id=_entry_id(provider, title),
                    dimension=Dimension.CAPABILITY,
                    title=f"[{provider.upper()}] {title}",
                    summary=summary,
                    source=provider,
                    source_url=link,
                    source_type=SourceType.BLOG,
                    domains=_classify_domains(f"{title} {summary}"),
                    alignment=_classify_alignment(f"{title} {summary}"),
                    impact_score=0.6,
                    entities=[provider],
                    tags=["official", "blog", provider],
                    published_at=pub_str,
                ))
        except Exception as e:
            logger.warning(f"Blog scan failed for {provider}: {e}")
    return entries


# ─── Reddit AI ───────────────────────────────────────────────────────────────

async def scan_reddit_ai(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Scan Reddit AI subreddits via RSS (JSON API is blocked from servers)."""
    subreddits = ["MachineLearning", "artificial", "LocalLLaMA"]
    entries = []
    for sub in subreddits:
        try:
            resp = await client.get(f"https://www.reddit.com/r/{sub}/hot/.rss")
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.text)
            for item in feed.entries[:10]:
                title = item.get("title", "").strip()
                if not title:
                    continue
                link = item.get("link", "")
                summary = (item.get("summary") or "")[:300]
                summary = re.sub(r'<[^>]+>', '', summary).strip()

                entries.append(IndexEntry(
                    id=_entry_id(f"reddit_{sub}", title),
                    dimension=Dimension.ACTIVITY,
                    title=f"[r/{sub}] {title}",
                    summary=summary or f"Discussion on r/{sub}",
                    source="reddit",
                    source_url=link,
                    source_type=SourceType.NEWS,
                    domains=_classify_domains(f"{title} {summary}"),
                    alignment=_classify_alignment(f"{title} {summary}"),
                    impact_score=0.35,
                    tags=["reddit", f"r/{sub}", "community"],
                ))
        except Exception as e:
            logger.warning(f"Reddit scan failed for r/{sub}: {e}")
    return entries


# ─── Tech News RSS ───────────────────────────────────────────────────────────

async def scan_tech_news(client: httpx.AsyncClient) -> list[IndexEntry]:
    feeds = {
        "techcrunch_ai": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "verge_ai": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "ars_ai": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "mit_ai": "https://www.technologyreview.com/feed/",
    }
    entries = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)

    for source_name, feed_url in feeds.items():
        try:
            resp = await client.get(feed_url)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.text)
            for item in feed.entries[:5]:
                title = item.get("title", "").strip()
                if not title:
                    continue

                ai_keywords = [
                    "ai", "artificial intelligence", "machine learning", "llm",
                    "gpt", "claude", "gemini", "neural", "deep learning",
                    "openai", "anthropic", "model", "chatbot", "copilot",
                    "autonomous", "robot", "agent",
                ]
                title_lower = title.lower()
                if not any(k in title_lower for k in ai_keywords):
                    continue

                published = item.get("published_parsed") or item.get("updated_parsed")
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                    pub_str = pub_dt.isoformat()
                else:
                    pub_str = None

                summary = (item.get("summary") or item.get("description") or "")[:300]
                summary = re.sub(r'<[^>]+>', '', summary).strip()
                link = item.get("link", "")

                entries.append(IndexEntry(
                    id=_entry_id(source_name, title),
                    dimension=Dimension.ACTIVITY,
                    title=title,
                    summary=summary,
                    source=source_name,
                    source_url=link,
                    source_type=SourceType.NEWS,
                    domains=_classify_domains(f"{title} {summary}"),
                    alignment=_classify_alignment(f"{title} {summary}"),
                    impact_score=0.5,
                    entities=[source_name.replace("_ai", "")],
                    tags=["news", source_name],
                    published_at=pub_str,
                ))
        except Exception as e:
            logger.warning(f"Tech news scan failed for {source_name}: {e}")
    return entries


# ─── Papers With Code (trending) ─────────────────────────────────────────────

async def scan_hf_daily_papers(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Scan HuggingFace daily papers (trending research with community upvotes)."""
    entries = []
    try:
        resp = await client.get("https://huggingface.co/api/daily_papers")
        if resp.status_code != 200:
            return entries
        papers = resp.json() if isinstance(resp.json(), list) else resp.json().get("papers", [])
        for paper in papers[:15]:
            p = paper.get("paper", paper) if isinstance(paper, dict) else {}
            title = (p.get("title") or "").strip()
            if not title:
                continue
            summary = (p.get("summary") or p.get("abstract") or "")[:300]
            pid = p.get("id") or ""
            upvotes = paper.get("numUpvotes", 0) if isinstance(paper, dict) else 0

            impact = 0.4
            if upvotes > 50:
                impact = 0.7
            elif upvotes > 20:
                impact = 0.55
            elif upvotes > 5:
                impact = 0.45

            entries.append(IndexEntry(
                id=_entry_id("hf_papers", title),
                dimension=Dimension.INTELLIGENCE,
                title=title,
                summary=summary,
                source="hf_papers",
                source_url=f"https://huggingface.co/papers/{pid}" if pid else "",
                source_type=SourceType.RESEARCH_PAPER,
                domains=_classify_domains(f"{title} {summary}"),
                impact_score=impact,
                tags=["research", "paper", "huggingface-daily"],
                raw_data={"upvotes": upvotes},
                published_at=paper.get("publishedAt"),
            ))
    except Exception as e:
        logger.warning(f"HuggingFace daily papers scan failed: {e}")
    return entries


# ─── Official Model Changelogs (Primary Sources) ────────────────────────────

async def scan_model_changelogs(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Scan official changelog/release note pages — primary capability signals."""
    changelog_rss = {
        "anthropic_news": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml",
        "anthropic_eng": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_engineering.xml",
        "anthropic_research": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml",
        "openai": "https://openai.com/news/rss.xml",
        "google_deepmind": "https://blog.google/technology/ai/rss/",
    }
    entries = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)

    for provider, feed_url in changelog_rss.items():
        try:
            resp = await client.get(feed_url)
            if resp.status_code != 200:
                logger.info(f"Changelog feed {provider}: HTTP {resp.status_code}")
                continue
            feed = feedparser.parse(resp.text)
            for item in feed.entries[:8]:
                title = item.get("title", "").strip()
                if not title:
                    continue
                published = item.get("published_parsed") or item.get("updated_parsed")
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                    pub_str = pub_dt.isoformat()
                else:
                    pub_str = None

                summary = (item.get("summary") or item.get("description") or "")[:300]
                summary = re.sub(r'<[^>]+>', '', summary).strip()
                link = item.get("link", "")
                label = provider.replace("_", " ").title()

                entries.append(IndexEntry(
                    id=_entry_id(f"changelog_{provider}", title),
                    dimension=Dimension.CAPABILITY,
                    title=f"[{label}] {title}",
                    summary=summary,
                    source="changelog",
                    source_url=link,
                    source_type=SourceType.TOOL_LAUNCH,
                    domains=_classify_domains(f"{title} {summary}"),
                    impact_score=0.7,
                    entities=[provider.split("_")[0]],
                    tags=["changelog", "primary-source", provider],
                    published_at=pub_str,
                ))
        except Exception as e:
            logger.warning(f"Changelog scan failed for {provider}: {e}")
    return entries


# ─── Benchmark Leaderboards ──────────────────────────────────────────────────

async def scan_benchmarks(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Scan Open LLM Leaderboard — quantified capability shifts."""
    entries = []
    try:
        resp = await client.get(
            "https://huggingface.co/api/spaces/open-llm-leaderboard/open_llm_leaderboard"
        )
        if resp.status_code == 200:
            data = resp.json()
            siblings = data.get("siblings", [])
            last_modified = data.get("lastModified", "")
            entries.append(IndexEntry(
                id=_entry_id("leaderboard", f"open_llm_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"),
                dimension=Dimension.CAPABILITY,
                title="Open LLM Leaderboard Update",
                summary=f"Tracking {len(siblings)} files. Last modified: {last_modified[:10] if last_modified else 'unknown'}. The Open LLM Leaderboard ranks open-source models across standardized benchmarks.",
                source="benchmark",
                source_url="https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard",
                source_type=SourceType.BENCHMARK,
                domains=[Domain.REASONING, Domain.CODE, Domain.GENERAL],
                impact_score=0.6,
                tags=["benchmark", "leaderboard", "quantified"],
            ))
    except Exception as e:
        logger.warning(f"Open LLM Leaderboard scan failed: {e}")

    try:
        resp = await client.get("https://huggingface.co/api/spaces/lmsys/chatbot-arena-leaderboard")
        if resp.status_code == 200:
            data = resp.json()
            last_modified = data.get("lastModified", "")
            entries.append(IndexEntry(
                id=_entry_id("leaderboard", f"lmsys_arena_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"),
                dimension=Dimension.CAPABILITY,
                title="LMSYS Chatbot Arena Leaderboard Update",
                summary=f"Last modified: {last_modified[:10] if last_modified else 'unknown'}. Community-driven blind comparison of LLMs through human preference voting.",
                source="benchmark",
                source_url="https://huggingface.co/spaces/lmsys/chatbot-arena-leaderboard",
                source_type=SourceType.BENCHMARK,
                domains=[Domain.REASONING, Domain.GENERAL],
                impact_score=0.65,
                tags=["benchmark", "arena", "human-eval"],
            ))
    except Exception as e:
        logger.warning(f"LMSYS Arena scan failed: {e}")
    return entries


# ─── Agent Framework Releases (Infrastructure Signal) ────────────────────────

async def scan_agent_frameworks(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Track releases from key agent frameworks — infrastructure capability signals."""
    frameworks = [
        # Core SDKs
        "langchain-ai/langchain", "langchain-ai/langgraph",
        "microsoft/autogen", "microsoft/semantic-kernel",
        "joaomdmoura/crewAI", "run-llama/llama_index",
        "BerriAI/litellm", "pydantic/pydantic-ai",
        "anthropics/anthropic-sdk-python", "openai/openai-python",
        "google/generative-ai-python",
        "huggingface/smolagents", "modelcontextprotocol/servers",
        # Agent infrastructure
        "BlockRunAI/ClawRouter", "vercel/ai", "livekit/agents",
        "e2b-dev/E2B", "all-hands-ai/OpenHands",
        "agentscope-ai/agentscope",
        # AI-native capabilities (transcription, trading, memory, safety)
        "Vaibhavs10/insanely-fast-whisper", "SYSTRAN/faster-whisper",
        "TauricResearch/tradingagents",
        "facebookresearch/Hyperagents",
        "letta-ai/claude-subconscious",
        "deepset-ai/haystack",
    ]
    entries = []
    for repo in frameworks:
        try:
            resp = await client.get(
                f"https://api.github.com/repos/{repo}/releases?per_page=2",
                headers=GH_HEADERS
            )
            if resp.status_code != 200 or not resp.json():
                continue
            for rel in resp.json()[:2]:
                pub = rel.get("published_at", "")
                if not pub:
                    continue
                pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - pub_dt > timedelta(days=14):
                    continue
                tag = rel.get("tag_name", "")
                title = f"{repo} {tag}"
                body = (rel.get("body") or "")[:400]

                is_major = any(x in tag for x in ["0.0", "1.0", "2.0", "3.0"]) or "breaking" in body.lower()
                impact = 0.7 if is_major else 0.5

                entries.append(IndexEntry(
                    id=_entry_id("agent_framework", title),
                    dimension=Dimension.CAPABILITY,
                    title=title,
                    summary=body,
                    source="agent_framework",
                    source_url=rel.get("html_url", ""),
                    source_type=SourceType.TOOL_LAUNCH,
                    domains=[Domain.AGENTS, Domain.TOOLS],
                    impact_score=impact,
                    entities=[repo.split("/")[0]],
                    tags=["agent-framework", "release", "infrastructure"],
                    published_at=pub,
                ))
        except Exception as e:
            logger.warning(f"Agent framework scan failed for {repo}: {e}")
    return entries


# ─── AI Incident Database (Threat Intelligence) ─────────────────────────────

async def scan_ai_incidents(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Scan AI incident and safety signal sources — dark AI threat intelligence.
    
    Uses multiple approaches: Hacker News safety stories, Reddit AI ethics,
    and curated AI safety feeds. The AI Incident Database lacks a public REST API,
    so we aggregate from discussion sources where incidents surface first.
    """
    entries = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    safety_keywords = [
        "incident", "bias", "hallucination", "deepfake", "misuse", "safety",
        "harm", "leak", "vulnerability", "jailbreak", "adversarial", "exploit",
        "alignment failure", "ai risk", "catastrophic", "deceptive",
    ]

    try:
        resp = await client.get(
            "https://hn.algolia.com/api/v1/search_by_date?query=AI+incident+safety+bias+risk&tags=story&numericFilters=created_at_i>"
            + str(int((datetime.now(timezone.utc) - timedelta(days=3)).timestamp()))
            + "&hitsPerPage=10"
        )
        if resp.status_code == 200:
            hits = resp.json().get("hits", [])
            for hit in hits:
                title = hit.get("title", "")
                if not title:
                    continue
                title_lower = title.lower()
                if not any(kw in title_lower for kw in safety_keywords):
                    continue
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                points = hit.get("points", 0)
                impact = 0.5 + min(points / 500, 0.3)
                entries.append(IndexEntry(
                    id=_entry_id("ai_incident_hn", title),
                    dimension=Dimension.ACTIVITY,
                    title=f"[Safety Signal] {title}",
                    summary=f"Hacker News discussion ({points} points) — flagged as AI safety/incident signal.",
                    source="ai_incidents",
                    source_url=url,
                    source_type=SourceType.INCIDENT_REPORT,
                    domains=_classify_domains(f"{title}"),
                    alignment=Alignment.DARK,
                    dark_flag=True,
                    impact_score=impact,
                    tags=["incident", "dark-ai", "safety", "hacker-news"],
                    published_at=hit.get("created_at"),
                ))
    except Exception as e:
        logger.warning(f"AI incident HN scan failed: {e}")

    safety_rss = {
        "ai_safety_reddit": "https://www.reddit.com/r/aisafety/hot/.rss",
    }
    for source_name, feed_url in safety_rss.items():
        try:
            resp = await client.get(feed_url, headers={"User-Agent": UA})
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.text)
            for item in feed.entries[:10]:
                title = item.get("title", "").strip()
                if not title:
                    continue
                published = item.get("published_parsed") or item.get("updated_parsed")
                pub_str = None
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                    pub_str = pub_dt.isoformat()
                summary = re.sub(r'<[^>]+>', '', (item.get("summary") or "")[:300]).strip()
                link = item.get("link", "")
                entries.append(IndexEntry(
                    id=_entry_id(source_name, title),
                    dimension=Dimension.ACTIVITY,
                    title=f"[Safety Signal] {title}",
                    summary=summary,
                    source="ai_incidents",
                    source_url=link,
                    source_type=SourceType.INCIDENT_REPORT,
                    domains=_classify_domains(f"{title} {summary}"),
                    alignment=Alignment.DARK if any(kw in title.lower() for kw in safety_keywords) else Alignment.NEUTRAL,
                    dark_flag=any(kw in title.lower() for kw in safety_keywords),
                    impact_score=0.5,
                    tags=["safety", "dark-ai", "reddit"],
                    published_at=pub_str,
                ))
        except Exception as e:
            logger.warning(f"AI safety RSS scan failed for {source_name}: {e}")
    return entries


# ─── AI Policy & Regulation (Constraint Layer) ──────────────────────────────

async def scan_ai_policy(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Scan AI policy and regulation signals — the constraint layer that shapes deployment.
    
    Uses HN Algolia for policy discussions and curated RSS feeds from policy think tanks.
    """
    entries = []

    policy_keywords = [
        "ai regulation", "ai act", "ai policy", "ai governance", "ai safety regulation",
        "executive order ai", "eu ai", "ai legislation", "ai ban", "ai law",
        "deepfake law", "ai liability", "frontier model", "ai audit",
    ]
    try:
        resp = await client.get(
            "https://hn.algolia.com/api/v1/search_by_date?query=AI+regulation+policy+governance&tags=story&numericFilters=created_at_i>"
            + str(int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp()))
            + "&hitsPerPage=10"
        )
        if resp.status_code == 200:
            hits = resp.json().get("hits", [])
            for hit in hits:
                title = hit.get("title", "")
                if not title:
                    continue
                title_lower = title.lower()
                if not any(kw in title_lower for kw in policy_keywords):
                    continue
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                points = hit.get("points", 0)
                entries.append(IndexEntry(
                    id=_entry_id("policy_hn", title),
                    dimension=Dimension.ACTIVITY,
                    title=f"[Policy] {title}",
                    summary=f"Policy signal from Hacker News ({points} points).",
                    source="ai_policy",
                    source_url=url,
                    source_type=SourceType.NEWS,
                    domains=[Domain.SECURITY, Domain.GENERAL],
                    impact_score=0.5 + min(points / 500, 0.2),
                    tags=["policy", "regulation", "hacker-news"],
                    published_at=hit.get("created_at"),
                ))
    except Exception as e:
        logger.warning(f"AI policy HN scan failed: {e}")

    policy_rss = {
        "eff_ai": "https://www.eff.org/rss/updates.xml",
        "stanford_hai": "https://hai.stanford.edu/news/rss.xml",
    }
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    for source_name, feed_url in policy_rss.items():
        try:
            resp = await client.get(feed_url)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.text)
            for item in feed.entries[:8]:
                title = item.get("title", "").strip()
                if not title:
                    continue
                title_lower = title.lower()
                if not any(kw in title_lower for kw in ["ai", "machine learning", "artificial", "model", "algorithm", "llm", "regulation", "policy"]):
                    continue
                published = item.get("published_parsed") or item.get("updated_parsed")
                pub_str = None
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                    pub_str = pub_dt.isoformat()
                summary = re.sub(r'<[^>]+>', '', (item.get("summary") or "")[:300]).strip()
                link = item.get("link", "")
                entries.append(IndexEntry(
                    id=_entry_id(source_name, title),
                    dimension=Dimension.ACTIVITY,
                    title=f"[Policy] {title}",
                    summary=summary,
                    source="ai_policy",
                    source_url=link,
                    source_type=SourceType.NEWS,
                    domains=[Domain.SECURITY, Domain.GENERAL],
                    impact_score=0.5,
                    entities=[source_name.replace("_", " ")],
                    tags=["policy", "regulation", source_name],
                    published_at=pub_str,
                ))
        except Exception as e:
            logger.warning(f"AI policy RSS scan failed for {source_name}: {e}")
    return entries


# ─── Agentic AI Community Scanner ────────────────────────────────────────────

async def scan_agentic_ai(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Scan agentic AI communities — OpenClaw, agent builders, AI automation groups.
    
    Tracks: new innovations, community discoveries, framework adoption,
    use cases, and breakout projects in the agentic AI space.
    """
    entries = []

    agentic_repos = [
        # Core agent frameworks
        "OCloudAI/OctoTools", "openclaw/openclaw",
        "SigmaHQ/sigma", "browser-use/browser-use",
        "modelcontextprotocol/servers", "modelcontextprotocol/typescript-sdk",
        "langgenius/dify", "n8n-io/n8n", "activepieces/activepieces",
        "FlowiseAI/Flowise", "Mintplex-Labs/anything-llm",
        "ComposioHQ/composio", "geekan/MetaGPT",
        "Significant-Gravitas/AutoGPT", "OpenBMB/ChatDev",
        "yoheinakajima/babyagi",
        # Agent infrastructure + routers
        "BlockRunAI/ClawRouter",
        "all-hands-ai/OpenHands", "e2b-dev/E2B",
        "livekit/agents", "fixie-ai/ultravox",
        "vercel/ai", "deepset-ai/haystack",
        "mem0ai/mem0", "cpacker/MemGPT",
        # OpenClaw ecosystem (skills, wrappers, plugins)
        "VoltAgent/awesome-openclaw-skills",
        "BehiSecc/awesome-claude-skills",
        "Memphis-Chains/memphis",
        "letta-ai/claude-subconscious",
        "Donchitos/Claude-Code-Game-Studios",
        "cporter202/API-mega-list",
        # Self-improving / meta-agent systems
        "facebookresearch/Hyperagents",
        "agentscope-ai/agentscope",
        # AI trading / finance agents
        "TauricResearch/tradingagents",
        # AI capability tools
        "p-e-w/heretic",
        "Vaibhavs10/insanely-fast-whisper",
    ]
    for repo in agentic_repos:
        try:
            resp = await client.get(
                f"https://api.github.com/repos/{repo}/releases?per_page=2",
                headers=GH_HEADERS
            )
            if resp.status_code != 200 or not resp.json():
                continue
            for rel in resp.json()[:2]:
                pub = rel.get("published_at", "")
                if not pub:
                    continue
                pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - pub_dt > timedelta(days=14):
                    continue
                tag = rel.get("tag_name", "")
                title = f"{repo} {tag}"
                body = (rel.get("body") or "")[:400]
                entries.append(IndexEntry(
                    id=_entry_id("agentic_release", title),
                    dimension=Dimension.CAPABILITY,
                    title=f"[Agentic AI] {title}",
                    summary=body,
                    source="agentic_ai",
                    source_url=rel.get("html_url", ""),
                    source_type=SourceType.TOOL_LAUNCH,
                    domains=[Domain.AGENTS, Domain.TOOLS],
                    impact_score=0.6,
                    entities=[repo.split("/")[0]],
                    tags=["agentic", "agent-framework", "community"],
                    published_at=pub,
                ))
        except Exception as e:
            logger.warning(f"Agentic AI scan failed for {repo}: {e}")

    agentic_subreddits = [
        "OpenAI", "ChatGPTPro", "AutoGPT", "AIAgents",
        "ClaudeAI", "singularity", "LLMDevs",
    ]
    for sub in agentic_subreddits:
        try:
            resp = await client.get(
                f"https://www.reddit.com/r/{sub}/hot/.rss",
                headers={"User-Agent": UA}
            )
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.text)
            agentic_keywords = [
                "agent", "agentic", "autonomous", "openclaw", "open claw",
                "mcp", "tool use", "function calling", "browser use",
                "automation", "workflow", "n8n", "dify", "crew",
                "open source", "github", "repo", "framework", "router",
                "skills", "plugin", "self-improving", "meta-agent",
                "trading agent", "whisper", "transcription", "memory",
                "claude code", "cursor", "codex", "cline",
            ]
            for item in feed.entries[:10]:
                title = item.get("title", "").strip()
                if not title:
                    continue
                title_lower = title.lower()
                if not any(kw in title_lower for kw in agentic_keywords):
                    continue
                published = item.get("published_parsed") or item.get("updated_parsed")
                pub_str = None
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) - pub_dt > timedelta(days=7):
                        continue
                    pub_str = pub_dt.isoformat()
                summary = re.sub(r'<[^>]+>', '', (item.get("summary") or "")[:300]).strip()
                link = item.get("link", "")
                entries.append(IndexEntry(
                    id=_entry_id(f"agentic_reddit_{sub}", title),
                    dimension=Dimension.CAPABILITY,
                    title=f"[Agentic Community] {title}",
                    summary=summary,
                    source="agentic_ai",
                    source_url=link,
                    source_type=SourceType.FIELD_REPORT,
                    source_category=SourceCategory.AGENT_FIELD_REPORT,
                    domains=[Domain.AGENTS, Domain.TOOLS],
                    impact_score=0.45,
                    tags=["agentic", "community", f"r/{sub}"],
                    published_at=pub_str,
                ))
        except Exception as e:
            logger.warning(f"Agentic AI Reddit scan failed for r/{sub}: {e}")

    agentic_hn_queries = [
        "AI+agent+autonomous", "agentic+AI", "OpenClaw",
        "MCP+model+context+protocol", "browser+use+AI+agent",
        "LLM+router+smart+routing", "AI+agent+payments+crypto",
        "AI+agent+infrastructure+framework", "agent+tool+use+API",
        "self-improving+AI+agent", "AI+trading+agent+multi-agent",
        "claude+code+skills+plugin", "open+source+AI+tool+free",
        "AI+agent+memory+persistent", "whisper+transcription+fast",
        "AI+censorship+uncensored+model",
    ]
    for query in agentic_hn_queries:
        try:
            resp = await client.get(
                f"https://hn.algolia.com/api/v1/search_by_date?query={query}&tags=story"
                f"&numericFilters=created_at_i>"
                + str(int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp()))
                + "&hitsPerPage=5"
            )
            if resp.status_code != 200:
                continue
            for hit in resp.json().get("hits", []):
                title = hit.get("title", "")
                if not title:
                    continue
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                points = hit.get("points", 0)
                entries.append(IndexEntry(
                    id=_entry_id("agentic_hn", title),
                    dimension=Dimension.CAPABILITY,
                    title=f"[Agentic AI] {title}",
                    summary=f"Agentic AI discussion on HN ({points} points).",
                    source="agentic_ai",
                    source_url=url,
                    source_type=SourceType.FIELD_REPORT,
                    domains=[Domain.AGENTS, Domain.TOOLS],
                    impact_score=0.45 + min(points / 500, 0.3),
                    tags=["agentic", "community", "hacker-news"],
                    published_at=hit.get("created_at"),
                ))
        except Exception as e:
            logger.warning(f"Agentic AI HN scan failed for {query}: {e}")

    return entries


# ─── AI Tool Discovery (Find *new* tools like ClawRouter) ────────────────────

async def scan_tool_discovery(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Proactively discover NEW AI tools, routers, agent infrastructure, and
    developer platforms that are gaining traction — the things we don't
    already know about.

    Strategy:
      1. GitHub search for recently-created repos with explosive growth
      2. npm/PyPI new package signals via GitHub trending
      3. Product Hunt AI category
      4. HN "Show HN" + "Launch HN" for AI tools
    """
    entries = []
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

    # --- 1. GitHub: new repos gaining stars fast (created recently, high stars) ---
    discovery_queries = [
        # Infrastructure & routing
        "llm+router", "ai+agent+tool", "ai+infrastructure",
        "model+gateway", "ai+payments", "agent+orchestration",
        "ai+developer+tools", "llm+gateway", "ai+automation+platform",
        "vector+database+ai", "rag+framework", "ai+coding+assistant",
        "mcp+server", "ai+workflow+engine", "agent+memory",
        # OpenClaw / Claude ecosystem (FB viral category)
        "openclaw+skills", "claude+skills", "claude+code+plugin",
        "openclaw+wrapper", "claude+agent",
        # Self-improving / meta-agent systems
        "self-improving+agent", "meta-agent", "hyperagent",
        "agent+self-modification", "agent+evolution",
        # AI trading / finance
        "ai+trading+agent", "multi-agent+trading", "ai+hedge+fund",
        # AI capability tools (transcription, uncensoring, etc.)
        "whisper+fast+transcription", "ai+censorship+removal",
        "ai+skills+library", "awesome+ai+agents",
        # Agent specialist collections
        "ai+agent+specialist", "ai+workflow+agent",
        "agent+game+studio", "ai+api+list",
    ]
    for query in discovery_queries:
        try:
            url = (
                f"https://api.github.com/search/repositories"
                f"?q=created:>{cutoff_date}+stars:>100+topic:{query}"
                f"&sort=stars&order=desc&per_page=3"
            )
            resp = await client.get(url, headers=GH_HEADERS)
            if resp.status_code != 200:
                continue
            for repo in resp.json().get("items", [])[:3]:
                name = repo["full_name"]
                desc = (repo.get("description") or "")[:300]
                stars = repo.get("stargazers_count", 0)
                created = repo.get("created_at", "")[:10]
                text = f"{name} {desc}"

                age_days = max(1, (datetime.now(timezone.utc) - datetime.fromisoformat(
                    repo.get("created_at", "2026-01-01T00:00:00Z").replace("Z", "+00:00")
                )).days)
                velocity = stars / age_days

                if velocity < 5:
                    continue

                impact = min(0.4 + (velocity / 100) + (stars / 10000), 1.0)

                entries.append(IndexEntry(
                    id=_entry_id("tool_discovery", name),
                    dimension=Dimension.CAPABILITY,
                    title=f"[New Tool] {name}",
                    summary=f"{desc} — {stars:,} stars in {age_days}d ({velocity:.0f} stars/day). Created {created}.",
                    source="tool_discovery",
                    source_url=repo["html_url"],
                    source_type=SourceType.TOOL_LAUNCH,
                    domains=_classify_domains(text),
                    alignment=_classify_alignment(text),
                    impact_score=impact,
                    entities=[repo.get("owner", {}).get("login", "")],
                    tags=["discovery", "new-tool", "breakout", repo.get("language", "")],
                    raw_data={
                        "stars": stars, "velocity": round(velocity, 1),
                        "age_days": age_days, "language": repo.get("language"),
                        "topics": repo.get("topics", []),
                    },
                    published_at=repo.get("created_at"),
                ))
        except Exception as e:
            logger.warning(f"Tool discovery GitHub failed for {query}: {e}")

    # --- 2. Show HN / Launch HN for AI tools ---
    try:
        resp = await client.get(
            "https://hn.algolia.com/api/v1/search_by_date"
            "?query=Show+HN+AI+tool+agent+LLM&tags=show_hn"
            f"&numericFilters=created_at_i>{int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp())}"
            "&hitsPerPage=15"
        )
        if resp.status_code == 200:
            for hit in resp.json().get("hits", []):
                title = hit.get("title", "")
                if not title:
                    continue
                title_lower = title.lower()
                ai_signals = [
                    "ai", "llm", "gpt", "claude", "agent", "model", "ml",
                    "neural", "transformer", "embedding", "vector", "rag",
                    "router", "gateway", "inference", "fine-tun", "copilot",
                    "openclaw", "whisper", "transcri", "trading", "hedge",
                    "self-improv", "memory", "skill", "mcp", "autom",
                    "uncensor", "open source", "multi-agent",
                ]
                if not any(s in title_lower for s in ai_signals):
                    continue
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                points = hit.get("points", 0)
                comments = hit.get("num_comments", 0)
                traction = points + (comments * 2)

                if traction < 20:
                    continue

                impact = min(0.45 + (traction / 500), 0.9)
                entries.append(IndexEntry(
                    id=_entry_id("tool_discovery_hn", title),
                    dimension=Dimension.CAPABILITY,
                    title=f"[New Tool] {title}",
                    summary=f"Show HN launch — {points} points, {comments} comments. Community-validated AI tool.",
                    source="tool_discovery",
                    source_url=url,
                    source_type=SourceType.TOOL_LAUNCH,
                    domains=_classify_domains(title),
                    alignment=_classify_alignment(title),
                    impact_score=impact,
                    tags=["discovery", "show-hn", "new-tool", "community-validated"],
                    raw_data={"points": points, "comments": comments},
                    published_at=hit.get("created_at"),
                ))
    except Exception as e:
        logger.warning(f"Tool discovery HN Show failed: {e}")

    # --- 3. Product Hunt AI tools ---
    try:
        resp = await client.get(
            "https://hn.algolia.com/api/v1/search_by_date"
            "?query=Product+Hunt+AI+launch&tags=story"
            f"&numericFilters=created_at_i>{int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp())}"
            "&hitsPerPage=10"
        )
        if resp.status_code == 200:
            for hit in resp.json().get("hits", []):
                title = hit.get("title", "")
                if not title:
                    continue
                title_lower = title.lower()
                if "product hunt" not in title_lower and not any(
                    s in title_lower for s in ["ai", "llm", "agent", "ml"]
                ):
                    continue
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                points = hit.get("points", 0)
                if points < 10:
                    continue
                entries.append(IndexEntry(
                    id=_entry_id("tool_discovery_ph", title),
                    dimension=Dimension.ACTIVITY,
                    title=f"[New Tool] {title}",
                    summary=f"Product Hunt / AI launch signal ({points} points on HN).",
                    source="tool_discovery",
                    source_url=url,
                    source_type=SourceType.TOOL_LAUNCH,
                    domains=_classify_domains(title),
                    impact_score=min(0.4 + points / 300, 0.8),
                    tags=["discovery", "product-hunt", "new-tool"],
                    published_at=hit.get("created_at"),
                ))
    except Exception as e:
        logger.warning(f"Tool discovery PH scan failed: {e}")

    # --- 4. GitHub trending: catch breakout repos we don't track yet ---
    breakout_queries = [
        "ai+agent", "llm+tool", "ai+platform",
        "open+source+ai", "ai+dev+tool",
    ]
    for query in breakout_queries:
        try:
            cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
            url = (
                f"https://api.github.com/search/repositories"
                f"?q=stars:>500+pushed:>{cutoff_7d}+topic:{query}"
                f"&sort=stars&order=desc&per_page=3"
            )
            resp = await client.get(url, headers=GH_HEADERS)
            if resp.status_code != 200:
                continue
            for repo in resp.json().get("items", [])[:3]:
                name = repo["full_name"]
                stars = repo.get("stargazers_count", 0)
                desc = (repo.get("description") or "")[:300]
                entries.append(IndexEntry(
                    id=_entry_id("breakout_repo", name),
                    dimension=Dimension.CAPABILITY,
                    title=f"[Trending] {name}",
                    summary=f"{desc} — {stars:,} stars, actively updated.",
                    source="tool_discovery",
                    source_url=repo["html_url"],
                    source_type=SourceType.TOOL_LAUNCH,
                    domains=_classify_domains(f"{name} {desc}"),
                    impact_score=min(0.4 + stars / 10000, 0.9),
                    entities=[repo.get("owner", {}).get("login", "")],
                    tags=["discovery", "trending", "breakout"],
                    raw_data={"stars": stars, "language": repo.get("language")},
                ))
        except Exception as e:
            logger.warning(f"Breakout repo scan failed for {query}: {e}")

    logger.info(f"  Tool Discovery: {len(entries)} new tools/platforms found")
    return entries


# ─── OpenClaw & Agent Ecosystem Scanner ───────────────────────────────────────

async def scan_openclaw_ecosystem(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Track the OpenClaw/Claude ecosystem — skills registries, wrappers,
    plugins, hosted platforms, and community-built tools.

    This catches the class of viral tools spreading through Facebook AI groups:
    skills libraries, agent wrappers, self-evolving agents, specialist collections.
    """
    entries = []

    ecosystem_repos = [
        "VoltAgent/awesome-openclaw-skills",
        "BehiSecc/awesome-claude-skills",
        "Memphis-Chains/memphis",
        "letta-ai/claude-subconscious",
        "Donchitos/Claude-Code-Game-Studios",
        "cporter202/API-mega-list",
        "p-e-w/heretic",
        "brooks376/MetaClaw-Open-Source-Self-Evolving-AI-Agent-Framework-with-Online-RL",
        "Dev-Dennis-040/openclaw-agency-skills",
    ]

    for repo in ecosystem_repos:
        try:
            resp = await client.get(
                f"https://api.github.com/repos/{repo}",
                headers=GH_HEADERS
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            stars = data.get("stargazers_count", 0)
            desc = (data.get("description") or "")[:300]
            name = data["full_name"]
            pushed = data.get("pushed_at", "")

            if pushed:
                push_dt = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - push_dt > timedelta(days=60):
                    continue

            topics = data.get("topics", [])
            text = f"{name} {desc} {' '.join(topics)}"

            entries.append(IndexEntry(
                id=_entry_id("openclaw_eco", name),
                dimension=Dimension.CAPABILITY,
                title=f"[OpenClaw Ecosystem] {name}",
                summary=f"{desc} — {stars:,} stars. Topics: {', '.join(topics[:5]) if topics else 'n/a'}",
                source="openclaw_ecosystem",
                source_url=data.get("html_url", ""),
                source_type=SourceType.TOOL_LAUNCH,
                domains=_classify_domains(text),
                alignment=_classify_alignment(text),
                impact_score=min(0.45 + stars / 5000, 0.85),
                entities=[repo.split("/")[0]],
                tags=["openclaw-ecosystem", "skills", "community-built"],
                raw_data={"stars": stars, "topics": topics, "language": data.get("language")},
                published_at=pushed,
            ))
        except Exception as e:
            logger.warning(f"OpenClaw ecosystem scan failed for {repo}: {e}")

    # Search for new OpenClaw/Claude ecosystem repos we don't track yet
    ecosystem_searches = [
        "openclaw+skills", "awesome+openclaw", "claude+skills+library",
        "openclaw+plugin", "claude+code+agent", "metaclaw",
    ]
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    for query in ecosystem_searches:
        try:
            url = (
                f"https://api.github.com/search/repositories"
                f"?q=created:>{cutoff}+stars:>10+{query}"
                f"&sort=stars&order=desc&per_page=3"
            )
            resp = await client.get(url, headers=GH_HEADERS)
            if resp.status_code != 200:
                continue
            for repo in resp.json().get("items", [])[:3]:
                name = repo["full_name"]
                desc = (repo.get("description") or "")[:300]
                stars = repo.get("stargazers_count", 0)
                text = f"{name} {desc}"

                entries.append(IndexEntry(
                    id=_entry_id("openclaw_new", name),
                    dimension=Dimension.CAPABILITY,
                    title=f"[New in Ecosystem] {name}",
                    summary=f"{desc} — {stars:,} stars.",
                    source="openclaw_ecosystem",
                    source_url=repo["html_url"],
                    source_type=SourceType.TOOL_LAUNCH,
                    domains=_classify_domains(text),
                    impact_score=min(0.4 + stars / 2000, 0.8),
                    entities=[repo.get("owner", {}).get("login", "")],
                    tags=["openclaw-ecosystem", "new-discovery", "community-built"],
                    raw_data={"stars": stars, "language": repo.get("language")},
                    published_at=repo.get("created_at"),
                ))
        except Exception as e:
            logger.warning(f"OpenClaw ecosystem search failed for {query}: {e}")

    logger.info(f"  OpenClaw Ecosystem: {len(entries)} tools/skills found")
    return entries


# ─── Full Scan Orchestrator ──────────────────────────────────────────────────

async def _scan_layoffs(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Wrapper to import and run the layoffs scanner."""
    from ..data_sources.layoffs import scan_layoffs
    return await scan_layoffs(client)


SCAN_TIERS = {
    "tier1": {
        "interval_minutes": 30,
        "label": "Critical (30m)",
        "scanners": [
            ("Model Changelogs", scan_model_changelogs),
            ("Agent Frameworks", scan_agent_frameworks),
            ("Benchmarks", scan_benchmarks),
        ],
    },
    "tier2": {
        "interval_minutes": 60,
        "label": "Community (60m)",
        "scanners": [
            ("GitHub Trending", scan_github_trending),
            ("GitHub Releases", scan_github_releases),
            ("HuggingFace", scan_huggingface),
            ("Hacker News", scan_hackernews),
            ("Reddit AI", scan_reddit_ai),
            ("Agentic AI", scan_agentic_ai),
            ("Tool Discovery", scan_tool_discovery),
            ("OpenClaw Ecosystem", scan_openclaw_ecosystem),
            ("Layoffs", _scan_layoffs),
        ],
    },
    "tier3": {
        "interval_minutes": 360,
        "label": "Deep (6h)",
        "scanners": [
            ("HF Daily Papers", scan_hf_daily_papers),
            ("arXiv", scan_arxiv),
            ("AI Blogs", scan_ai_blogs),
            ("Tech News", scan_tech_news),
            ("AI Incidents", scan_ai_incidents),
            ("AI Policy", scan_ai_policy),
        ],
    },
}


async def _run_tier(tier_id: str) -> list[IndexEntry]:
    """Run a specific scan tier and return deduplicated entries."""
    tier = SCAN_TIERS[tier_id]
    all_entries: list[IndexEntry] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": UA},
        timeout=httpx.Timeout(SCAN_TIMEOUT),
        follow_redirects=True,
    ) as client:
        for name, scanner in tier["scanners"]:
            try:
                logger.info(f"[{tier['label']}] Scanning {name}...")
                results = await scanner(client)
                logger.info(f"  {name}: {len(results)} entries")
                all_entries.extend(results)
            except Exception as e:
                logger.error(f"  {name} FAILED: {e}")

    return _deduplicate(all_entries)


async def run_tier1_scan() -> list[IndexEntry]:
    """Tier 1: Critical sources — changelogs, frameworks, benchmarks (30 min)."""
    return await _run_tier("tier1")


async def run_tier2_scan() -> list[IndexEntry]:
    """Tier 2: Community reaction layer — HN, Reddit, GitHub (60 min)."""
    return await _run_tier("tier2")


async def run_full_scan() -> list[IndexEntry]:
    """Run all 18 sources across all tiers. Used for tier3 cycle and initial boot."""
    all_entries: list[IndexEntry] = []
    for tier_id in SCAN_TIERS:
        entries = await _run_tier(tier_id)
        all_entries.extend(entries)
    return _deduplicate(all_entries)


def _deduplicate(entries: list[IndexEntry]) -> list[IndexEntry]:
    seen_ids: set[str] = set()
    unique: list[IndexEntry] = []
    for entry in entries:
        if entry.id not in seen_ids:
            seen_ids.add(entry.id)
            unique.append(entry)
    return unique
