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

import asyncio
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
    """Estimate frontier impact 0-1 from engagement signals and content quality.

    Three components:
    1. Engagement (0-0.35): stars, points, likes — log-scaled for diminishing returns
    2. Content signals (0-0.35): frontier keywords weighted by specificity
    3. Source credibility (0.15-0.30): base varies by source reliability
    """
    import math

    stars = item.get("stars", 0) or item.get("likes", 0) or 0
    points = item.get("points", 0) or 0
    text = (item.get("title", "") + " " + item.get("description", "")).lower()

    # 1. Engagement: log-scaled (1K stars ≈ 0.2, 10K ≈ 0.3, 100K ≈ 0.35)
    engagement = 0.0
    if stars > 0:
        engagement += min(math.log10(max(stars, 1)) / 14, 0.35)
    if points > 0:
        engagement += min(math.log10(max(points, 1)) / 10, 0.2)
    engagement = min(engagement, 0.35)

    # 2. Content signals: high-specificity keywords score more
    high_signal = [
        "state-of-the-art", "sota", "benchmark record", "surpass", "outperform",
        "gpt-5", "gpt-6", "claude-4", "claude-5", "gemini-2", "gemini-3",
        "llama-4", "llama-5", "o3", "o4", "o5",
        "deepseek-v4", "deepseek-r2", "qwen-3", "qwen3",
        "agi", "superintelligence", "paradigm shift",
    ]
    mid_signal = [
        "breakthrough", "new model", "autonomous", "first-ever", "novel approach",
        "agent-native", "self-improving", "real-time", "zero-shot",
        "open-source release", "mcp server", "tool-use",
    ]
    low_signal = [
        "framework", "library", "sdk", "integration", "api",
        "fine-tun", "evaluation", "dataset", "router",
    ]

    content_score = 0.0
    for kw in high_signal:
        if kw in text:
            content_score += 0.12
    for kw in mid_signal:
        if kw in text:
            content_score += 0.06
    for kw in low_signal:
        if kw in text:
            content_score += 0.03
    content_score = min(content_score, 0.35)

    # 3. Source credibility base
    source_bases = {
        "model_drop": 0.35, "lab_announcement": 0.30, "github_events": 0.28,
        "hf_fast_detect": 0.30,
        "model_release": 0.30, "github_release": 0.25, "changelog": 0.25,
        "arxiv": 0.22, "hf_daily_papers": 0.22, "benchmark": 0.25,
        "ai_blog": 0.22, "tech_news": 0.20,
        "agent_framework": 0.20, "github": 0.18,
        "huggingface": 0.18, "hackernews": 0.18,
        "reddit_ai": 0.15, "agentic_community": 0.15,
        "tool_discovery": 0.18, "openclaw": 0.18,
        "ai_incident": 0.20, "ai_policy": 0.20,
        "layoffs": 0.18,
    }
    base = source_bases.get(source, 0.18)

    return min(round(base + engagement + content_score, 3), 1.0)


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
                    tags=[t for t in [repo.get("language") or "", "github-trending"] if t],
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
        "vllm-project/vllm", "deepseek-ai/DeepSeek-V3",
        "mlc-ai/mlc-llm", "ggerganov/llama.cpp",
        "sgl-project/sglang", "mistralai/mistral-inference",
        "unslothai/unsloth", "pytorch/pytorch",
        "apple/ml-stable-diffusion", "stability-ai/generative-models",
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
    categories = [
        "cs.AI",   # Artificial Intelligence
        "cs.CL",   # Computation and Language (NLP, LLMs)
        "cs.LG",   # Machine Learning
        "cs.MA",   # Multi-Agent Systems
        "cs.CV",   # Computer Vision
        "cs.RO",   # Robotics (embodied AI)
        "stat.ML", # Statistical ML
        "cs.IR",   # Information Retrieval (RAG, search)
    ]
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
                    impact_score=_estimate_impact(
                        {"title": title, "description": summary}, "arxiv"
                    ),
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
                    impact_score=_estimate_impact(
                        {"title": title, "description": summary}, "ai_blog"
                    ),
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
                    impact_score=_estimate_impact(
                        {"title": title, "description": summary}, "reddit_ai"
                    ),
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
                    impact_score=_estimate_impact(
                        {"title": title, "description": summary}, "tech_news"
                    ),
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

            entries.append(IndexEntry(
                id=_entry_id("hf_papers", title),
                dimension=Dimension.INTELLIGENCE,
                title=title,
                summary=summary,
                source="hf_papers",
                source_url=f"https://huggingface.co/papers/{pid}" if pid else "",
                source_type=SourceType.RESEARCH_PAPER,
                domains=_classify_domains(f"{title} {summary}"),
                impact_score=_estimate_impact(
                    {"title": title, "description": summary, "likes": upvotes},
                    "hf_daily_papers"
                ),
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
                    impact_score=_estimate_impact(
                        {"title": title, "description": summary}, "changelog"
                    ),
                    entities=[provider.split("_")[0]],
                    tags=["changelog", "primary-source", provider],
                    published_at=pub_str,
                ))
        except Exception as e:
            logger.warning(f"Changelog scan failed for {provider}: {e}")
    return entries


# ─── Benchmark Leaderboards ──────────────────────────────────────────────────

async def scan_benchmarks(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Scan benchmark leaderboards for actual model performance data."""
    entries = []

    # Open LLM Leaderboard v2: fetch top models via HF datasets API
    try:
        resp = await client.get(
            "https://huggingface.co/api/datasets/open-llm-leaderboard/contents",
            timeout=15
        )
        top_models_text = ""
        if resp.status_code == 200:
            data = resp.json()
            last_mod = data.get("lastModified", "")
            top_models_text = f"Last updated: {last_mod[:10] if last_mod else 'unknown'}. "

        # Also check trending models on HF that mention "leaderboard"
        resp2 = await client.get(
            "https://huggingface.co/api/models?sort=trending&limit=10&filter=text-generation",
            timeout=15
        )
        trending_models = []
        if resp2.status_code == 200:
            for m in resp2.json()[:10]:
                name = m.get("id", "")
                likes = m.get("likes", 0)
                downloads = m.get("downloads", 0)
                trending_models.append(f"{name} ({likes} likes, {downloads:,} downloads)")

        if trending_models:
            top5 = trending_models[:5]
            summary = (
                f"{top_models_text}Top trending text-generation models: "
                f"{'; '.join(top5)}. "
                f"These models represent the current frontier of open-source LLM capability."
            )
        else:
            summary = f"{top_models_text}Open LLM Leaderboard tracks standardized benchmarks across open-source models."

        entries.append(IndexEntry(
            id=_entry_id("leaderboard", f"open_llm_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"),
            dimension=Dimension.CAPABILITY,
            title="Open LLM Leaderboard — Trending Models",
            summary=summary,
            source="benchmark",
            source_url="https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard",
            source_type=SourceType.BENCHMARK,
            domains=[Domain.REASONING, Domain.CODE, Domain.GENERAL],
            impact_score=_estimate_impact(
                {"stars": sum(m.get("likes", 0) for m in (resp2.json()[:5] if resp2.status_code == 200 else [])),
                 "title": "open llm leaderboard sota benchmark"},
                "benchmark"
            ),
            tags=["benchmark", "leaderboard", "quantified", "trending-models"],
        ))
    except Exception as e:
        logger.warning(f"Open LLM Leaderboard scan failed: {e}")

    # Chatbot Arena: fetch latest results from the lmsys API
    try:
        resp = await client.get(
            "https://huggingface.co/api/spaces/lmsys/chatbot-arena-leaderboard",
            timeout=15
        )
        arena_summary = ""
        if resp.status_code == 200:
            data = resp.json()
            last_mod = data.get("lastModified", "")
            arena_summary = f"Last updated: {last_mod[:10] if last_mod else 'unknown'}. "

        # Try to get recent discussions for arena changes
        disc_resp = await client.get(
            "https://huggingface.co/api/spaces/lmsys/chatbot-arena-leaderboard/discussions?limit=5",
            timeout=10
        )
        recent_changes = []
        if disc_resp.status_code == 200:
            for disc in disc_resp.json().get("discussions", [])[:5]:
                title = disc.get("title", "")
                if title:
                    recent_changes.append(title)

        if recent_changes:
            arena_summary += f"Recent activity: {'; '.join(recent_changes[:3])}. "

        arena_summary += "Community-driven blind comparison ranking LLMs by human preference votes."

        entries.append(IndexEntry(
            id=_entry_id("leaderboard", f"lmsys_arena_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"),
            dimension=Dimension.CAPABILITY,
            title="Chatbot Arena — Human Preference Rankings",
            summary=arena_summary,
            source="benchmark",
            source_url="https://huggingface.co/spaces/lmsys/chatbot-arena-leaderboard",
            source_type=SourceType.BENCHMARK,
            domains=[Domain.REASONING, Domain.GENERAL],
            impact_score=_estimate_impact(
                {"points": 500, "title": "chatbot arena benchmark human preference sota"},
                "benchmark"
            ),
            tags=["benchmark", "arena", "human-eval", "elo-ranking"],
        ))
    except Exception as e:
        logger.warning(f"Chatbot Arena scan failed: {e}")
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
                    impact_score=_estimate_impact(
                        {"title": title, "description": body}, "agentic_community"
                    ),
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
    # Ordered by value: highest-signal queries first so rate limits don't cost us
    discovery_queries = [
        # Highest value — core infrastructure we'd actually use
        "mcp+server", "llm+router", "agent+orchestration",
        "rag+framework", "ai+agent+tool", "agent+memory",
        "ai+coding+assistant", "llm+gateway", "ai+workflow+engine",
        # OpenClaw / Claude ecosystem
        "openclaw+skills", "claude+agent", "claude+skills",
        # Self-improving / meta-agent systems
        "self-improving+agent", "meta-agent",
        # Broader infrastructure
        "ai+infrastructure", "model+gateway", "ai+developer+tools",
        "vector+database+ai", "ai+automation+platform",
        # Lower priority — nice to have
        "ai+trading+agent", "ai+skills+library",
        "awesome+ai+agents", "ai+workflow+agent",
    ]
    rate_limited = False
    for query in discovery_queries:
        if rate_limited:
            break
        try:
            url = (
                f"https://api.github.com/search/repositories"
                f"?q=created:>{cutoff_date}+stars:>100+topic:{query}"
                f"&sort=stars&order=desc&per_page=3"
            )
            resp = await client.get(url, headers=GH_HEADERS)
            if resp.status_code == 403:
                logger.warning(f"Tool discovery: GitHub rate limited at query '{query}', stopping ({len(entries)} entries captured)")
                rate_limited = True
                break
            if resp.status_code != 200:
                continue
            await asyncio.sleep(0.5)
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
                    impact_score=_estimate_impact(
                        {"title": name, "description": desc, "stars": stars},
                        "tool_discovery"
                    ),
                    entities=[repo.get("owner", {}).get("login", "")],
                    tags=[t for t in ["discovery", "new-tool", "breakout", repo.get("language") or ""] if t],
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
        if rate_limited:
            break
        try:
            cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
            url = (
                f"https://api.github.com/search/repositories"
                f"?q=stars:>500+pushed:>{cutoff_7d}+topic:{query}"
                f"&sort=stars&order=desc&per_page=3"
            )
            resp = await client.get(url, headers=GH_HEADERS)
            if resp.status_code == 403:
                logger.warning(f"Tool discovery breakout: GitHub rate limited at '{query}'")
                rate_limited = True
                break
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


# ─── PRE-PUBLICATION: PyPI AI Package Monitor ────────────────────────────────

PYPI_PACKAGES = [
    "anthropic", "openai", "google-generativeai", "transformers",
    "langchain-core", "langchain", "llama-index", "crewai", "autogen",
    "dspy-ai", "vllm", "guidance", "instructor", "outlines",
    "openai-whisper", "ultralytics", "diffusers", "accelerate",
    "pydantic-ai", "litellm", "smolagents", "mcp",
    "tiktoken", "tokenizers", "safetensors", "huggingface-hub",
]

_pypi_last_versions: dict[str, str] = {}

async def scan_pypi_ai_packages(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Pre-publication signal: detect AI SDK updates before blog posts.

    New PyPI versions typically appear 1-3 days before announcement posts.
    This is invisible to humans reading news — gold for a scanner.
    """
    entries = []
    for pkg in PYPI_PACKAGES:
        try:
            resp = await client.get(f"https://pypi.org/pypi/{pkg}/json", timeout=8)
            if resp.status_code != 200:
                continue
            data = resp.json()
            info = data.get("info", {})
            version = info.get("version", "")
            name = info.get("name", pkg)
            summary_text = info.get("summary", "")

            prev = _pypi_last_versions.get(pkg)
            if prev is None:
                _pypi_last_versions[pkg] = version
                continue
            if version == prev:
                continue

            _pypi_last_versions[pkg] = version

            releases = data.get("releases", {})
            release_files = releases.get(version, [])
            upload_time = ""
            if release_files:
                upload_time = release_files[0].get("upload_time_iso_8601", "")

            text = f"{name} {version} {summary_text}"
            entries.append(IndexEntry(
                id=_entry_id("pypi", f"{name}-{version}"),
                dimension=Dimension.CAPABILITY,
                title=f"[PyPI] {name} {version} — new release",
                summary=(
                    f"Python package '{name}' updated to {version}. "
                    f"{summary_text[:200]}. "
                    f"Pre-publication signal: SDK updates often precede announcements by 1-3 days."
                ),
                source="pypi_monitor",
                source_url=f"https://pypi.org/project/{pkg}/{version}/",
                source_type=SourceType.TOOL_LAUNCH,
                domains=_classify_domains(text),
                impact_score=_estimate_impact(
                    {"title": f"{name} {version} new release sdk update", "description": summary_text},
                    "model_release"
                ),
                entities=[name],
                tags=["pre-publication", "pypi", "sdk-update", "early-signal"],
                raw_data={"package": pkg, "version": version, "previous": prev},
                published_at=upload_time or None,
            ))
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.warning(f"PyPI scan failed for {pkg}: {e}")
    if entries:
        logger.info(f"  PyPI: {len(entries)} new package versions detected (pre-publication signal)")
    return entries


# ─── PRE-PUBLICATION: HuggingFace Org Model Watcher ─────────────────────────

HF_WATCHED_ORGS = [
    "meta-llama", "mistralai", "google", "microsoft",
    "Qwen", "deepseek-ai", "stabilityai", "openai",
    "anthropic", "cohere", "databricks", "nvidia",
    "apple", "allenai", "bigcode", "HuggingFaceH4",
    "NousResearch", "teknium", "cognitivecomputations",
]

_hf_known_models: dict[str, set[str]] = {}

async def scan_hf_new_models(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Pre-publication signal: detect new model uploads from key AI labs.

    Model weights on HuggingFace often appear hours before blog posts.
    Watching specific orgs catches drops that trending-only scanning misses.
    """
    entries = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)

    for org in HF_WATCHED_ORGS:
        try:
            resp = await client.get(
                f"https://huggingface.co/api/models?author={org}&sort=lastModified&direction=-1&limit=5",
                timeout=10
            )
            if resp.status_code != 200:
                continue

            models = resp.json()
            known = _hf_known_models.get(org, set())
            if not known:
                _hf_known_models[org] = {m.get("id", "") for m in models}
                continue

            for model in models:
                model_id = model.get("id", "")
                if not model_id or model_id in known:
                    continue

                created = model.get("createdAt", "")
                if created:
                    try:
                        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        if created_dt < cutoff:
                            continue
                    except (ValueError, TypeError):
                        pass

                known.add(model_id)
                likes = model.get("likes", 0)
                downloads = model.get("downloads", 0)
                pipeline_tag = model.get("pipeline_tag", "")
                tags = model.get("tags", [])

                tag_text = " ".join(tags[:10]) if tags else ""
                text = f"{model_id} {pipeline_tag} {tag_text}"

                entries.append(IndexEntry(
                    id=_entry_id("hf_model", model_id),
                    dimension=Dimension.CAPABILITY,
                    title=f"[HF New Model] {model_id}",
                    summary=(
                        f"New model uploaded by {org}: {model_id}. "
                        f"Pipeline: {pipeline_tag or 'unspecified'}. "
                        f"{likes} likes, {downloads:,} downloads. "
                        f"Pre-publication signal: model weights often precede announcements."
                    ),
                    source="hf_model_watch",
                    source_url=f"https://huggingface.co/{model_id}",
                    source_type=SourceType.TOOL_LAUNCH,
                    domains=_classify_domains(text),
                    impact_score=_estimate_impact(
                        {"title": f"new model {model_id} {pipeline_tag}", "description": tag_text, "likes": likes},
                        "model_release"
                    ),
                    entities=[org],
                    tags=["pre-publication", "hf-model-drop", "early-signal", pipeline_tag or "unknown"],
                    raw_data={"model_id": model_id, "org": org, "likes": likes, "downloads": downloads, "pipeline_tag": pipeline_tag},
                    published_at=created or None,
                ))

            _hf_known_models[org] = known
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning(f"HF model watch failed for {org}: {e}")
    if entries:
        logger.info(f"  HF Model Watch: {len(entries)} new models from watched orgs (pre-publication signal)")
    return entries


# ─── CROSS-SOURCE SYNTHESIS: Convergence Detection ──────────────────────────

async def detect_cross_source_patterns(entries: list[IndexEntry]) -> list[IndexEntry]:
    """Detect patterns that emerge only when seeing multiple sources together.

    A human reads one article at a time. The system sees all entries simultaneously
    and can detect convergence, capability chains, and contradictions that no
    single-source reader can.
    """
    if len(entries) < 10:
        return []

    synthesis_entries = []

    # --- Pattern 1: Domain convergence ---
    # 3+ different sources reporting on the same domain = convergence signal
    domain_source_map: dict[str, dict[str, list]] = {}
    for entry in entries:
        for domain in entry.domains:
            d = domain.value if hasattr(domain, 'value') else str(domain)
            if d == "general":
                continue
            domain_source_map.setdefault(d, {})
            src = entry.source
            domain_source_map[d].setdefault(src, []).append(entry)

    for domain, sources in domain_source_map.items():
        unique_sources = list(sources.keys())
        if len(unique_sources) < 3:
            continue

        total_entries = sum(len(v) for v in sources.values())
        avg_impact = sum(
            e.impact_score for src_entries in sources.values() for e in src_entries
        ) / total_entries if total_entries else 0

        top_titles = []
        for src_entries in sources.values():
            best = max(src_entries, key=lambda e: e.impact_score)
            top_titles.append(f"{best.source}: {best.title[:60]}")

        strength = min(1.0, len(unique_sources) / 6 + avg_impact * 0.3)

        synthesis_entries.append(IndexEntry(
            id=_entry_id("synthesis", f"convergence_{domain}_{datetime.now(timezone.utc).strftime('%H')}"),
            dimension=Dimension.INTELLIGENCE,
            title=f"[Convergence] {domain.replace('_',' ').title()}: {len(unique_sources)} independent sources",
            summary=(
                f"Cross-source convergence detected in {domain}: "
                f"{len(unique_sources)} independent sources ({', '.join(unique_sources[:5])}) "
                f"reporting {total_entries} signals. Avg impact: {avg_impact:.2f}. "
                f"Top signals: {'; '.join(top_titles[:3])}. "
                f"Multiple sources pointing the same direction is a stronger signal than any individual entry."
            ),
            source="cross_source_synthesis",
            source_url="",
            source_type=SourceType.FIELD_REPORT,
            source_category=SourceCategory.COMMUNITY_SIGNAL,
            domains=[Domain(domain)] if domain in [d.value for d in Domain] else [Domain.GENERAL],
            impact_score=round(strength, 3),
            tags=["synthesis", "convergence", f"domain-{domain}", "cross-source"],
            raw_data={"domain": domain, "source_count": len(unique_sources), "entry_count": total_entries, "sources": unique_sources},
        ))

    # --- Pattern 2: Entity convergence ---
    # Same entity (company/project) appearing across multiple sources = major event
    entity_sources: dict[str, dict[str, list]] = {}
    for entry in entries:
        for entity in (entry.entities or []):
            if not entity or len(entity) < 3:
                continue
            ent = entity.lower().strip()
            entity_sources.setdefault(ent, {})
            entity_sources[ent].setdefault(entry.source, []).append(entry)

    for entity, sources in entity_sources.items():
        unique_sources = list(sources.keys())
        if len(unique_sources) < 3:
            continue

        total = sum(len(v) for v in sources.values())
        top_titles = []
        for src_entries in sources.values():
            best = max(src_entries, key=lambda e: e.impact_score)
            top_titles.append(best.title[:60])

        synthesis_entries.append(IndexEntry(
            id=_entry_id("synthesis", f"entity_{entity}_{datetime.now(timezone.utc).strftime('%H')}"),
            dimension=Dimension.INTELLIGENCE,
            title=f"[Cross-Source] {entity.title()}: activity across {len(unique_sources)} sources",
            summary=(
                f"Entity '{entity}' detected across {len(unique_sources)} independent sources "
                f"({', '.join(unique_sources[:4])}), {total} total mentions this cycle. "
                f"Signals: {'; '.join(top_titles[:3])}. "
                f"Multi-source entity activity often indicates a major release or shift."
            ),
            source="cross_source_synthesis",
            source_url="",
            source_type=SourceType.FIELD_REPORT,
            domains=[Domain.GENERAL],
            impact_score=min(0.6 + len(unique_sources) * 0.05, 0.95),
            tags=["synthesis", "entity-convergence", f"entity-{entity}", "cross-source"],
            raw_data={"entity": entity, "source_count": len(unique_sources), "entry_count": total, "sources": unique_sources},
        ))

    if synthesis_entries:
        logger.info(f"  Cross-Source Synthesis: {len(synthesis_entries)} patterns detected")
    return synthesis_entries


# ─── Full Scan Orchestrator ──────────────────────────────────────────────────

async def _scan_layoffs(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Wrapper to import and run the layoffs scanner."""
    from ..data_sources.layoffs import scan_layoffs
    return await scan_layoffs(client)


# ═══════════════════════════════════════════════════════════════════════════════
# TIER 0: FAST-DETECT — 5-minute polling for model drops & announcements
# These scanners are lightweight (minimal API calls) and designed to catch
# major announcements within minutes, not hours.
# ═══════════════════════════════════════════════════════════════════════════════

# Track what we've already seen to avoid re-alerting
_seen_model_drops: set[str] = set()
_seen_lab_posts: set[str] = set()
_seen_org_events: set[str] = set()
_seen_hf_hot: set[str] = set()


async def scan_model_drops(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Poll official API changelogs/status pages every 5 min for new model releases.

    These update minutes after a release — much faster than blog RSS feeds.
    We check: OpenAI models API, Anthropic docs page, Google AI Studio models.
    """
    entries = []

    # 1. OpenAI — poll the models API for new model IDs
    try:
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {openai_key}"},
            )
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
                for m in models:
                    mid = m.get("id", "")
                    created = m.get("created", 0)
                    created_dt = datetime.fromtimestamp(created, tz=timezone.utc)
                    if created_dt > recent_cutoff and mid not in _seen_model_drops:
                        _seen_model_drops.add(mid)
                        entries.append(IndexEntry(
                            id=_entry_id("openai_model_drop", mid),
                            dimension=Dimension.CAPABILITY,
                            title=f"[MODEL DROP] OpenAI: {mid}",
                            summary=f"New model detected via OpenAI API: {mid} (created {created_dt.strftime('%Y-%m-%d %H:%M')} UTC). Check capabilities and pricing.",
                            source="model_drop",
                            source_url=f"https://platform.openai.com/docs/models/{mid}",
                            source_type=SourceType.MODEL_RELEASE,
                            source_category=SourceCategory.MODEL_RELEASE,
                            domains=_classify_domains(mid),
                            alignment=Alignment.NEUTRAL,
                            readiness=ReadinessLevel.PRODUCTION,
                            impact_score=0.85,
                            tags=["model-drop", "openai", "fast-detect"],
                            entities=["openai"],
                            published_at=created_dt.isoformat(),
                        ))
    except Exception as e:
        logger.debug(f"[FAST-DETECT] OpenAI models check: {e}")

    # 2. Anthropic — poll the docs/changelog page
    try:
        resp = await client.get("https://docs.anthropic.com/en/docs/about-claude/models")
        if resp.status_code == 200:
            text = resp.text
            model_patterns = re.findall(r'claude-[\w.-]+', text)
            for mid in set(model_patterns):
                if mid not in _seen_model_drops and "claude-" in mid:
                    key = f"anthropic:{mid}"
                    if key not in _seen_model_drops:
                        _seen_model_drops.add(key)
    except Exception as e:
        logger.debug(f"[FAST-DETECT] Anthropic models check: {e}")

    # 3. Google — poll Gemini models list
    try:
        google_key = os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        if google_key:
            resp = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={google_key}",
            )
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                for m in models:
                    mid = m.get("name", "").replace("models/", "")
                    if mid and mid not in _seen_model_drops and "gemini" in mid.lower():
                        _seen_model_drops.add(mid)
    except Exception as e:
        logger.debug(f"[FAST-DETECT] Google models check: {e}")

    if entries:
        logger.info(f"[FAST-DETECT] Model drops detected: {len(entries)}")
    return entries


async def scan_lab_announcements(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Poll AI lab announcement pages directly — faster than RSS.

    Checks the actual HTML of announcement/changelog pages for new content
    since last check. Most labs update these pages before blog RSS propagates.
    """
    entries = []

    pages = {
        "openai_changelog": {
            "url": "https://platform.openai.com/docs/changelog",
            "pattern": r'<h[23][^>]*>([^<]+)</h[23]>',
            "source": "openai",
        },
        "anthropic_changelog": {
            "url": "https://docs.anthropic.com/en/docs/about-claude/models",
            "pattern": r'<h[23][^>]*>([^<]+)</h[23]>',
            "source": "anthropic",
        },
    }

    for page_id, config in pages.items():
        try:
            resp = await client.get(config["url"], follow_redirects=True)
            if resp.status_code != 200:
                continue

            headings = re.findall(config["pattern"], resp.text)
            for heading in headings[:5]:
                heading = heading.strip()
                if len(heading) < 10 or len(heading) > 200:
                    continue
                key = f"{page_id}:{heading[:60]}"
                if key in _seen_lab_posts:
                    continue
                _seen_lab_posts.add(key)

                if any(kw in heading.lower() for kw in [
                    "new", "launch", "release", "introduc", "announc",
                    "update", "available", "model", "gpt", "claude", "gemini",
                ]):
                    entries.append(IndexEntry(
                        id=_entry_id("lab_announce", heading),
                        dimension=Dimension.CAPABILITY,
                        title=f"[{config['source'].upper()}] {heading}",
                        summary=f"New announcement detected on {config['source']} changelog: {heading}",
                        source="lab_announcement",
                        source_url=config["url"],
                        source_type=SourceType.BLOG,
                        source_category=SourceCategory.MODEL_RELEASE,
                        domains=_classify_domains(heading),
                        alignment=Alignment.NEUTRAL,
                        readiness=ReadinessLevel.PRODUCTION,
                        impact_score=0.75,
                        tags=["lab-announcement", config["source"], "fast-detect"],
                        entities=[config["source"]],
                    ))
        except Exception as e:
            logger.debug(f"[FAST-DETECT] Lab announcement check for {page_id}: {e}")

    return entries


# Key AI organizations to watch for new repo/release events
_KEY_AI_ORGS = [
    "openai", "anthropics", "google-deepmind", "meta-llama", "mistralai",
    "huggingface", "deepseek-ai", "THUDM", "01-ai", "Qwen",
    "nvidia", "microsoft", "apple", "stability-ai", "black-forest-labs",
    "allenai", "EleutherAI", "NousResearch", "teknium",
]


async def scan_key_org_events(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Poll GitHub Events API for key AI orgs — detect new repos and releases in minutes.

    The Events API updates within minutes of any action. We watch for:
    - CreateEvent (new repos)
    - ReleaseEvent (new releases)
    - PushEvent to main/master with significant changes
    """
    entries = []

    for org in _KEY_AI_ORGS:
        try:
            resp = await client.get(
                f"https://api.github.com/orgs/{org}/events?per_page=10",
                headers=GH_HEADERS,
            )
            if resp.status_code != 200:
                continue

            events = resp.json()
            if not isinstance(events, list):
                continue

            for event in events[:10]:
                event_type = event.get("type", "")
                event_id = event.get("id", "")

                if event_id in _seen_org_events:
                    continue

                created = event.get("created_at", "")
                if created:
                    try:
                        event_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        if datetime.now(timezone.utc) - event_dt > timedelta(hours=6):
                            continue
                    except (ValueError, TypeError):
                        continue

                payload = event.get("payload", {})
                repo_name = event.get("repo", {}).get("name", "")

                if event_type == "CreateEvent" and payload.get("ref_type") == "repository":
                    _seen_org_events.add(event_id)
                    desc = payload.get("description", "") or ""
                    entries.append(IndexEntry(
                        id=_entry_id("gh_event", f"{org}:{repo_name}"),
                        dimension=Dimension.CAPABILITY,
                        title=f"[NEW REPO] {repo_name}",
                        summary=f"{org} created new repository: {repo_name}. {desc[:200]}",
                        source="github_events",
                        source_url=f"https://github.com/{repo_name}",
                        source_type=SourceType.TOOL_LAUNCH,
                        source_category=SourceCategory.TOOL_LAUNCH,
                        domains=_classify_domains(f"{repo_name} {desc}"),
                        alignment=_classify_alignment(f"{repo_name} {desc}"),
                        impact_score=0.80,
                        tags=["new-repo", org, "fast-detect"],
                        entities=[org],
                        published_at=created,
                    ))

                elif event_type == "ReleaseEvent":
                    release = payload.get("release", {})
                    tag = release.get("tag_name", "")
                    rel_title = release.get("name", "") or tag
                    if not tag:
                        continue
                    _seen_org_events.add(event_id)
                    body = (release.get("body") or "")[:300]
                    entries.append(IndexEntry(
                        id=_entry_id("gh_event", f"{repo_name}:{tag}"),
                        dimension=Dimension.CAPABILITY,
                        title=f"[RELEASE] {repo_name} {tag}",
                        summary=f"{rel_title}: {body}",
                        source="github_events",
                        source_url=release.get("html_url", f"https://github.com/{repo_name}"),
                        source_type=SourceType.TOOL_LAUNCH,
                        source_category=SourceCategory.TOOL_LAUNCH,
                        domains=_classify_domains(f"{repo_name} {body}"),
                        alignment=Alignment.LIGHT,
                        impact_score=0.75,
                        tags=["release", org, "fast-detect"],
                        entities=[org],
                        published_at=created,
                    ))

        except Exception as e:
            logger.debug(f"[FAST-DETECT] GitHub events for {org}: {e}")

    if entries:
        logger.info(f"[FAST-DETECT] GitHub events: {len(entries)} new from key AI orgs")
    return entries


async def scan_hf_hot_models(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Poll HuggingFace for brand-new models from key organizations.

    Checks the HF API for recently created models from top labs.
    Much faster than waiting for them to trend.
    """
    entries = []

    hf_orgs = [
        "meta-llama", "mistralai", "google", "Qwen", "deepseek-ai",
        "microsoft", "nvidia", "apple", "01-ai", "THUDM",
        "NousResearch", "stabilityai", "black-forest-labs",
    ]

    for org in hf_orgs:
        try:
            resp = await client.get(
                f"https://huggingface.co/api/models?author={org}&sort=createdAt&direction=-1&limit=3",
            )
            if resp.status_code != 200:
                continue

            models = resp.json()
            for m in models:
                mid = m.get("modelId", "") or m.get("id", "")
                created = m.get("createdAt", "")
                if not mid or not created:
                    continue

                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) - created_dt > timedelta(hours=48):
                        continue
                except (ValueError, TypeError):
                    continue

                if mid in _seen_hf_hot:
                    continue
                _seen_hf_hot.add(mid)

                downloads = m.get("downloads", 0)
                likes = m.get("likes", 0)
                pipeline = m.get("pipeline_tag", "")
                tags = m.get("tags", [])

                desc = f"New model from {org}: {mid}. Pipeline: {pipeline}. Downloads: {downloads:,}. Likes: {likes}."
                if tags:
                    desc += f" Tags: {', '.join(tags[:5])}"

                entries.append(IndexEntry(
                    id=_entry_id("hf_hot", mid),
                    dimension=Dimension.CAPABILITY,
                    title=f"[NEW MODEL] {mid}",
                    summary=desc[:300],
                    source="hf_fast_detect",
                    source_url=f"https://huggingface.co/{mid}",
                    source_type=SourceType.MODEL_RELEASE,
                    source_category=SourceCategory.MODEL_RELEASE,
                    domains=_classify_domains(f"{mid} {desc}"),
                    alignment=Alignment.LIGHT,
                    readiness=ReadinessLevel.EXPERIMENTAL,
                    impact_score=0.80,
                    tags=["new-model", org, "fast-detect"],
                    entities=[org],
                    published_at=created,
                ))
        except Exception as e:
            logger.debug(f"[FAST-DETECT] HF hot models for {org}: {e}")

    if entries:
        logger.info(f"[FAST-DETECT] HuggingFace: {len(entries)} new models from key labs")
    return entries


SCAN_TIERS = {
    "tier0": {
        "interval_minutes": 5,
        "label": "Fast-Detect (5m)",
        "scanners": [
            ("Model Drop Detector", scan_model_drops),
            ("AI Lab Announcements", scan_lab_announcements),
            ("Key Org GitHub Events", scan_key_org_events),
            ("HF Hot Models", scan_hf_hot_models),
        ],
    },
    "tier1": {
        "interval_minutes": 30,
        "label": "Critical (30m)",
        "scanners": [
            ("Model Changelogs", scan_model_changelogs),
            ("Agent Frameworks", scan_agent_frameworks),
            ("Benchmarks", scan_benchmarks),
            ("PyPI AI Packages", scan_pypi_ai_packages),
            ("HF Model Watch", scan_hf_new_models),
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


async def run_tier0_scan() -> list[IndexEntry]:
    """Tier 0: Fast-detect — model drops, lab announcements, key org events (5 min)."""
    return await _run_tier("tier0")


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
