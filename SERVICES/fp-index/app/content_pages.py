"""
Content Pages — Branded article pages, content hub, RSS feeds.

Turns published_content into traffic-driving, SEO-friendly pages
with CTAs that map to the funnel:

  Insight Article  →  "Subscribe to Daily Intelligence"  →  /subscribe
  Audio Briefing   →  "Listen + Subscribe"               →  /subscribe
  Cost Analysis    →  "See Our AI Services"               →  /pricing
  Social Content   →  Links back to article pages

Every page: OG tags, canonical URL, structured data, email capture.
"""

import hashlib
import html as html_mod
import re
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select, func, update as sql_update

from .models.database import PublishedContentRow, ExecutionBriefRow, IndexEntryRow, PageViewRow, async_session

router = APIRouter()

BASE_URL = "https://fullpotential.ai"

# ─── Shared CSS (matches the intelligence page design system) ────────────────

SHARED_CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Newsreader:ital,wght@0,400;0,600;1,400&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#06060b;--card:#0c0c14;--border:#1a1a2e;--text:#c8c8d8;--dim:#666680;
      --accent:#00d4ff;--gold:#ffb800;--red:#ff4466;--green:#22cc88;--purple:#7b2fff}
body{font-family:'Newsreader',Georgia,serif;background:var(--bg);color:var(--text);line-height:1.7}
.wrap{max-width:780px;margin:0 auto;padding:40px 20px}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}

.site-header{text-align:center;padding:24px 0 32px;border-bottom:1px solid var(--border);margin-bottom:40px}
.site-header a{color:var(--dim);font-family:'IBM Plex Mono',monospace;font-size:0.7rem;
               text-transform:uppercase;letter-spacing:3px}
.site-header a:hover{color:var(--accent);text-decoration:none}

.breadcrumb{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:var(--dim);margin-bottom:24px}
.breadcrumb a{color:var(--dim)}
.breadcrumb a:hover{color:var(--accent)}

.article-title{font-size:2rem;font-weight:600;color:#e8e8f8;line-height:1.3;margin-bottom:12px}
.article-meta{font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:var(--dim);
              margin-bottom:32px;display:flex;gap:16px;flex-wrap:wrap;align-items:center}
.article-meta .tag{padding:2px 8px;border-radius:3px;border:1px solid var(--border);font-size:0.65rem;text-transform:uppercase;letter-spacing:1px}
.article-meta .tag-insight{border-color:var(--accent);color:var(--accent)}
.article-meta .tag-audio{border-color:var(--gold);color:var(--gold)}
.article-meta .tag-cost{border-color:var(--green);color:var(--green)}
.article-meta .tag-spec{border-color:var(--purple);color:var(--purple)}
.article-meta .tag-social{border-color:var(--red);color:var(--red)}
.article-meta .tag-prompt{border-color:#888;color:#888}

.article-body{font-size:1.05rem;color:var(--text);line-height:1.85;white-space:pre-line}
.article-body h1,.article-body h2,.article-body h3{color:#e8e8f8;margin:24px 0 12px;font-family:'Newsreader',Georgia,serif}
.article-body h2{font-size:1.3rem;border-bottom:1px solid var(--border);padding-bottom:8px}
.article-body h3{font-size:1.1rem}
.article-body p{margin-bottom:14px}
.article-body ul,.article-body ol{margin:12px 0 12px 24px}
.article-body li{margin-bottom:6px}
.article-body blockquote{border-left:3px solid var(--gold);padding:12px 20px;margin:16px 0;
                         background:rgba(255,184,0,0.03);color:var(--dim);font-style:italic}
.article-body code{font-family:'IBM Plex Mono',monospace;font-size:0.9em;background:rgba(255,255,255,0.05);
                   padding:2px 6px;border-radius:3px}
.article-body pre{background:var(--card);border:1px solid var(--border);border-radius:8px;
                  padding:16px;overflow-x:auto;margin:16px 0}
.article-body pre code{background:none;padding:0}

.audio-player{margin:24px 0;padding:24px;background:var(--card);border:1px solid var(--border);border-radius:12px;text-align:center}
.audio-player audio{width:100%;max-width:500px;margin-top:12px}
.audio-player .label{font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:var(--dim);margin-bottom:8px}

.cta-box{margin:48px 0 32px;padding:32px;background:linear-gradient(135deg,rgba(0,212,255,0.04),rgba(123,47,255,0.04));
         border:1px solid var(--border);border-radius:12px;text-align:center}
.cta-title{font-size:1.2rem;font-weight:600;color:#e0e0f0;margin-bottom:6px}
.cta-sub{font-size:0.88rem;color:var(--dim);margin-bottom:20px;max-width:480px;margin-left:auto;margin-right:auto}
.cta-form{display:flex;gap:8px;max-width:440px;margin:0 auto}
.cta-input{flex:1;font-family:'IBM Plex Mono',monospace;font-size:0.85rem;padding:12px 16px;
           background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);outline:none}
.cta-input:focus{border-color:var(--accent)}
.cta-input::placeholder{color:#444}
.cta-btn{font-family:'IBM Plex Mono',monospace;font-size:0.8rem;padding:12px 24px;
         background:linear-gradient(135deg,var(--accent),var(--purple));color:#fff;border:none;
         border-radius:6px;cursor:pointer;font-weight:600;white-space:nowrap;transition:opacity 0.2s}
.cta-btn:hover{opacity:0.9}
.cta-msg{font-family:'IBM Plex Mono',monospace;font-size:0.8rem;margin-top:10px;min-height:1.2em}

.cta-link{display:inline-block;margin-top:16px;font-family:'IBM Plex Mono',monospace;font-size:0.8rem;
          padding:10px 24px;border:1px solid var(--accent);border-radius:6px;color:var(--accent);transition:all 0.2s}
.cta-link:hover{background:var(--accent);color:var(--bg);text-decoration:none}

.footer{margin-top:48px;padding-top:24px;border-top:1px solid var(--border);text-align:center;
        font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:#333}
.footer a{color:var(--dim)}

.hub-grid{display:grid;gap:20px}
.hub-card{padding:24px;background:var(--card);border:1px solid var(--border);border-radius:10px;
          transition:border-color 0.2s}
.hub-card:hover{border-color:var(--accent)}
.hub-card a{text-decoration:none}
.hub-card-title{font-size:1.1rem;font-weight:600;color:#e0e0f0;margin-bottom:8px;line-height:1.4}
.hub-card-excerpt{font-size:0.88rem;color:var(--dim);line-height:1.6;margin-bottom:12px}
.hub-card-meta{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:#444;display:flex;gap:12px;flex-wrap:wrap}

.hub-filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:24px}
.hub-filter{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;padding:5px 12px;
            background:none;border:1px solid var(--border);color:var(--dim);border-radius:4px;
            cursor:pointer;transition:all 0.2s}
.hub-filter.active,.hub-filter:hover{border-color:var(--accent);color:var(--accent);background:rgba(0,212,255,0.05)}

.hub-stats{display:flex;gap:12px;justify-content:center;margin:0 0 32px;flex-wrap:wrap}
.hub-stat{font-family:'IBM Plex Mono',monospace;font-size:0.75rem;padding:6px 14px;
          background:var(--card);border:1px solid var(--border);border-radius:6px;color:var(--dim)}
.hub-stat b{color:var(--text)}
"""


SUBSCRIBE_JS = """
async function doSubscribe(e){
  e.preventDefault();
  const email=document.getElementById('cta-email').value;
  const msg=document.getElementById('cta-msg');
  if(!email){msg.textContent='Enter your email';msg.className='cta-msg';msg.style.color='var(--red)';return}
  try{
    const r=await fetch('/api/v1/subscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email})});
    const d=await r.json();
    if(r.ok){msg.textContent='You\\'re in. First briefing arrives tomorrow.';msg.style.color='var(--green)'}
    else{msg.textContent=d.detail||'Something went wrong';msg.style.color='var(--red)'}
  }catch(err){msg.textContent='Network error';msg.style.color='var(--red)'}
}
"""


CONTENT_TYPE_META = {
    "insight_article": {"tag_class": "tag-insight", "tag_label": "BUILD LOG", "cta_title": "Follow the build", "cta_sub": "We're building a self-improving AI system in public. Get the build logs.", "cta_type": "subscribe"},
    "audio_briefing": {"tag_class": "tag-audio", "tag_label": "AUDIO", "cta_title": "Listen to the build logs", "cta_sub": "Audio versions of what we actually shipped, narrated by AI.", "cta_type": "subscribe"},
    "cost_analysis": {"tag_class": "tag-cost", "tag_label": "COST ANALYSIS", "cta_title": "Real infrastructure numbers", "cta_sub": "See how we optimize costs across AI providers — with real data.", "cta_type": "link", "cta_href": "/pricing", "cta_text": "View pricing"},
    "implementation_spec": {"tag_class": "tag-spec", "tag_label": "SPEC", "cta_title": "Want to build this?", "cta_sub": "We document everything we build. Full specs, open decisions.", "cta_type": "link", "cta_href": "/intelligence", "cta_text": "See the specs"},
    "social_content": {"tag_class": "tag-social", "tag_label": "SOCIAL", "cta_title": "Follow the build", "cta_sub": "Real updates from a real AI system being built in public.", "cta_type": "subscribe"},
    "prompt_improvement": {"tag_class": "tag-prompt", "tag_label": "PROMPT", "cta_title": "See how we improve prompts", "cta_sub": "Our system rewrites its own prompts and measures the results.", "cta_type": "link", "cta_href": "/intelligence", "cta_text": "View intelligence feed"},
}


def _clean_title(title: str) -> str:
    """Remove [TAG] prefixes from titles for display."""
    return re.sub(r'^\[(?:INSIGHT|AUDIO|COST|SPEC|SOCIAL|PROMPT)\]\s*', '', title)


def _excerpt(body: str, length: int = 200) -> str:
    """First `length` chars of body, cleaned of markdown."""
    text = re.sub(r'[#*_`~]', '', body)
    text = re.sub(r'\n+', ' ', text).strip()
    return text[:length] + ('...' if len(text) > length else '')


def _body_to_html(body: str) -> str:
    """Convert markdown-ish body to HTML."""
    escaped = html_mod.escape(body)
    escaped = re.sub(r'^### (.+)$', r'<h3>\1</h3>', escaped, flags=re.M)
    escaped = re.sub(r'^## (.+)$', r'<h2>\1</h2>', escaped, flags=re.M)
    escaped = re.sub(r'^# (.+)$', r'<h1>\1</h1>', escaped, flags=re.M)
    escaped = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped)
    escaped = re.sub(r'\*(.+?)\*', r'<em>\1</em>', escaped)
    escaped = re.sub(r'`([^`]+)`', r'<code>\1</code>', escaped)
    paragraphs = escaped.split('\n\n')
    result = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p.startswith('<h'):
            result.append(p)
        else:
            result.append(f'<p>{p}</p>')
    return '\n'.join(result)


def _format_date(dt) -> str:
    if isinstance(dt, str):
        return dt[:10]
    if isinstance(dt, datetime):
        return dt.strftime('%B %d, %Y')
    return str(dt)[:10]


def _build_cta(content_type: str) -> str:
    meta = CONTENT_TYPE_META.get(content_type, CONTENT_TYPE_META["insight_article"])
    if meta["cta_type"] == "subscribe":
        return f"""
<div class="cta-box">
  <div class="cta-title">{meta['cta_title']}</div>
  <div class="cta-sub">{meta['cta_sub']}</div>
  <form class="cta-form" onsubmit="doSubscribe(event);return false">
    <input class="cta-input" type="email" id="cta-email" placeholder="your@email.com" required>
    <button class="cta-btn" type="submit">Subscribe</button>
  </form>
  <div id="cta-msg" class="cta-msg"></div>
</div>"""
    else:
        return f"""
<div class="cta-box">
  <div class="cta-title">{meta['cta_title']}</div>
  <div class="cta-sub">{meta['cta_sub']}</div>
  <a class="cta-link" href="{meta['cta_href']}">{meta['cta_text']}</a>
</div>"""


# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTANT: Static routes MUST be declared BEFORE the {content_id} catch-all.
# FastAPI matches routes in declaration order.
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# RSS Feed (must be before /insights/{content_id})
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/insights/feed.xml")
async def insights_rss():
    async with async_session() as session:
        rows = (await session.execute(
            select(PublishedContentRow)
            .where(PublishedContentRow.content_type.in_(["insight_article", "audio_briefing"]))
            .order_by(PublishedContentRow.published_at.desc())
            .limit(50)
        )).scalars().all()

    items = ""
    for r in rows:
        clean = _clean_title(r.title)
        link = f"{BASE_URL}/insights/{r.id}"
        desc = _excerpt(r.body, 300)
        pub = r.published_at.strftime('%a, %d %b %Y %H:%M:%S +0000') if isinstance(r.published_at, datetime) else str(r.published_at)
        items += f"""
    <item>
      <title>{xml_escape(clean)}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <description>{xml_escape(desc)}</description>
      <pubDate>{pub}</pubDate>
      <category>{r.content_type}</category>
    </item>"""

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Full Potential AI — Insights</title>
    <link>{BASE_URL}/insights</link>
    <description>Original intelligence from the AI frontier. Scanned, evaluated, and published autonomously.</description>
    <language>en-us</language>
    <atom:link href="{BASE_URL}/insights/feed.xml" rel="self" type="application/rss+xml"/>
    <image>
      <url>{BASE_URL}/api/v1/og-image</url>
      <title>Full Potential AI</title>
      <link>{BASE_URL}</link>
    </image>
    {items}
  </channel>
</rss>"""
    return Response(content=rss, media_type="application/rss+xml")


# ═══════════════════════════════════════════════════════════════════════════════
# Pageview Tracking — lightweight, privacy-respecting
# ═══════════════════════════════════════════════════════════════════════════════

async def _record_pageview(request: Request, path: str, content_id: str = None):
    """Record a pageview. Hash IP for privacy — we only need unique counts, not identity."""
    ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:12]
    referrer = request.headers.get("referer", "")[:500]
    ua = request.headers.get("user-agent", "")[:200]

    if any(bot in ua.lower() for bot in ["bot", "crawl", "spider", "slurp", "feed"]):
        return

    async with async_session() as session:
        session.add(PageViewRow(
            path=path[:500],
            content_id=content_id,
            ip_hash=ip_hash,
            referrer=referrer,
            user_agent=ua,
        ))
        if content_id:
            await session.execute(
                sql_update(PublishedContentRow)
                .where(PublishedContentRow.id == content_id)
                .values(view_count=PublishedContentRow.view_count + 1)
            )
        await session.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# Sitemap — so search engines can find the content
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/sitemap.xml")
async def sitemap():
    async with async_session() as session:
        rows = (await session.execute(
            select(PublishedContentRow.id, PublishedContentRow.published_at, PublishedContentRow.content_type)
            .where(PublishedContentRow.content_type.in_(["insight_article", "audio_briefing"]))
            .where(PublishedContentRow.gate_decision == "passed")
            .order_by(PublishedContentRow.published_at.desc())
        )).all()

    urls = f"""  <url>
    <loc>{BASE_URL}/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>{BASE_URL}/insights</loc>
    <changefreq>hourly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>{BASE_URL}/intelligence</loc>
    <changefreq>hourly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>{BASE_URL}/transparency</loc>
    <changefreq>daily</changefreq>
    <priority>0.7</priority>
  </url>"""

    for r in rows:
        lastmod = r[1].strftime("%Y-%m-%d") if isinstance(r[1], datetime) else str(r[1])[:10]
        urls += f"""
  <url>
    <loc>{BASE_URL}/insights/{r[0]}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>"""
    return Response(content=xml, media_type="application/xml")


# ═══════════════════════════════════════════════════════════════════════════════
# Visibility Stats API — the system reads its own reach
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/api/v1/visibility")
async def visibility_stats():
    """The system's own view of its reach — pageviews, top content, referrers."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    week_ago = now - timedelta(days=7)

    async with async_session() as session:
        total_views = (await session.execute(
            select(func.count()).select_from(PageViewRow)
        )).scalar() or 0

        today_views = (await session.execute(
            select(func.count()).select_from(PageViewRow)
            .where(PageViewRow.timestamp >= today_start)
        )).scalar() or 0

        week_views = (await session.execute(
            select(func.count()).select_from(PageViewRow)
            .where(PageViewRow.timestamp >= week_ago)
        )).scalar() or 0

        unique_today = (await session.execute(
            select(func.count(func.distinct(PageViewRow.ip_hash)))
            .where(PageViewRow.timestamp >= today_start)
        )).scalar() or 0

        top_content = (await session.execute(
            select(PublishedContentRow.id, PublishedContentRow.title,
                   PublishedContentRow.view_count, PublishedContentRow.content_type)
            .where(PublishedContentRow.view_count > 0)
            .order_by(PublishedContentRow.view_count.desc())
            .limit(10)
        )).all()

        top_referrers = (await session.execute(
            select(PageViewRow.referrer, func.count())
            .where(PageViewRow.referrer != "")
            .where(PageViewRow.timestamp >= week_ago)
            .group_by(PageViewRow.referrer)
            .order_by(func.count().desc())
            .limit(10)
        )).all()

        top_pages = (await session.execute(
            select(PageViewRow.path, func.count())
            .where(PageViewRow.timestamp >= week_ago)
            .group_by(PageViewRow.path)
            .order_by(func.count().desc())
            .limit(10)
        )).all()

    return {
        "total_pageviews": total_views,
        "today_pageviews": today_views,
        "today_unique_visitors": unique_today,
        "week_pageviews": week_views,
        "top_content": [
            {"id": r[0], "title": r[1][:80], "views": r[2], "type": r[3]}
            for r in top_content
        ],
        "top_referrers": [
            {"referrer": r[0][:100], "count": r[1]}
            for r in top_referrers
        ],
        "top_pages": [
            {"path": r[0], "count": r[1]}
            for r in top_pages
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Content hub — /insights (must be before /insights/{content_id})
# ═══════════════════════════════════════════════════════════════════════════════

PUBLIC_CONTENT_TYPES = ["insight_article", "audio_briefing", "social_content"]


@router.get("/insights", response_class=HTMLResponse)
async def insights_hub(request: Request, type: str = None):
    try:
        await _record_pageview(request, "/insights")
    except Exception:
        pass

    async with async_session() as session:
        query = select(PublishedContentRow).order_by(PublishedContentRow.published_at.desc())
        if type and type in PUBLIC_CONTENT_TYPES:
            query = query.where(PublishedContentRow.content_type == type)
        else:
            query = query.where(PublishedContentRow.content_type.in_(PUBLIC_CONTENT_TYPES))
        rows = (await session.execute(query.limit(100))).scalars().all()

        counts = dict((await session.execute(
            select(PublishedContentRow.content_type, func.count())
            .where(PublishedContentRow.content_type.in_(PUBLIC_CONTENT_TYPES))
            .group_by(PublishedContentRow.content_type)
        )).all())

    total = sum(counts.values())

    cards_html = ""
    for r in rows:
        clean = _clean_title(r.title)
        excerpt = _excerpt(r.body, 180)
        meta = CONTENT_TYPE_META.get(r.content_type, CONTENT_TYPE_META["insight_article"])
        cards_html += f"""
<div class="hub-card" data-type="{r.content_type}">
  <a href="/insights/{r.id}">
    <div class="hub-card-title">{html_mod.escape(clean)}</div>
    <div class="hub-card-excerpt">{html_mod.escape(excerpt)}</div>
    <div class="hub-card-meta">
      <span class="tag {meta['tag_class']}">{meta['tag_label']}</span>
      <span>{_format_date(r.published_at)}</span>
      <span>{r.domain or 'general'}</span>
    </div>
  </a>
</div>"""

    filter_buttons = '<button class="hub-filter active" onclick="filterCards(null,this)">All</button>'
    for ct_key, ct_meta in CONTENT_TYPE_META.items():
        if ct_key in counts:
            filter_buttons += f'<button class="hub-filter" onclick="filterCards(\'{ct_key}\',this)">{ct_meta["tag_label"]} ({counts[ct_key]})</button>'

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Build Logs — Full Potential AI</title>
<meta name="description" content="We're building a self-improving AI system in public. Real build logs — what we shipped, what broke, what we learned.">
<meta property="og:type" content="website">
<meta property="og:title" content="Build Logs — Full Potential AI">
<meta property="og:description" content="A self-improving AI system built in public. Real build logs with real numbers.">
<meta property="og:url" content="{BASE_URL}/insights">
<meta property="og:site_name" content="Full Potential AI">
<meta property="og:image" content="{BASE_URL}/api/v1/og-image">
<link rel="canonical" href="{BASE_URL}/insights">
<link rel="alternate" type="application/rss+xml" title="Full Potential AI Insights" href="{BASE_URL}/insights/feed.xml">
<style>{SHARED_CSS}</style>
</head>
<body>
<div class="wrap">

<div class="site-header">
  <a href="/">FULL POTENTIAL AI</a>
</div>

<h1 class="article-title" style="text-align:center;margin-bottom:8px">Build Logs</h1>
<p style="text-align:center;color:var(--dim);font-size:0.92rem;margin-bottom:32px;max-width:520px;margin-left:auto;margin-right:auto">
  We're building a self-improving AI system in public. These are the real build logs — what we shipped, what broke, what we learned. Every article passes a five-filter conscience gate before publishing.
</p>

<div class="hub-stats">
  <div class="hub-stat"><b>{total}</b>&nbsp;published</div>
  <div class="hub-stat"><b>{counts.get('insight_article', 0)}</b>&nbsp;articles</div>
  <div class="hub-stat"><b>{counts.get('audio_briefing', 0)}</b>&nbsp;audio</div>
  <div class="hub-stat"><b>{counts.get('cost_analysis', 0)}</b>&nbsp;analyses</div>
</div>

<div class="hub-filters">
  {filter_buttons}
</div>

<div class="hub-grid" id="cards">
  {cards_html}
</div>

<div class="cta-box" style="margin-top:48px">
  <div class="cta-title">Get daily AI intelligence</div>
  <div class="cta-sub">One email per day. The signals that matter from the AI frontier.</div>
  <form class="cta-form" onsubmit="doSubscribe(event);return false">
    <input class="cta-input" type="email" id="cta-email" placeholder="your@email.com" required>
    <button class="cta-btn" type="submit">Subscribe</button>
  </form>
  <div id="cta-msg" class="cta-msg"></div>
</div>

<div class="footer">
  <a href="/intelligence">Intelligence Feed</a> &middot;
  <a href="/insights/feed.xml">RSS</a> &middot;
  <a href="/">Full Potential AI</a>
  <br><br>&copy; {datetime.now().year} Full Potential AI
</div>

</div>
<script>
{SUBSCRIBE_JS}
function filterCards(type, btn) {{
  document.querySelectorAll('.hub-filter').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.hub-card').forEach(c => {{
    c.style.display = (!type || c.dataset.type === type) ? '' : 'none';
  }});
}}
</script>
</body>
</html>"""
    return HTMLResponse(content=page)


# ═══════════════════════════════════════════════════════════════════════════════
# Individual article page (catch-all — must be LAST)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/insights/{content_id}", response_class=HTMLResponse)
async def insight_page(request: Request, content_id: str):
    try:
        await _record_pageview(request, f"/insights/{content_id}", content_id)
    except Exception:
        pass

    async with async_session() as session:
        row = (await session.execute(
            select(PublishedContentRow).where(PublishedContentRow.id == content_id)
        )).scalars().first()

    if not row:
        raise HTTPException(status_code=404, detail="Content not found")

    clean_title = _clean_title(row.title)
    description = _excerpt(row.body, 160)
    content_html = _body_to_html(row.body)
    pub_date = _format_date(row.published_at)
    ct = row.content_type
    meta = CONTENT_TYPE_META.get(ct, CONTENT_TYPE_META["insight_article"])
    canonical = f"{BASE_URL}/insights/{row.id}"

    audio_block = ""
    if ct == "audio_briefing":
        mp3_match = re.search(r'(briefing-[\d-]+\.mp3)', row.body)
        if mp3_match:
            audio_url = f"{BASE_URL}/api/v1/audio/file/{mp3_match.group(1)}"
            audio_block = f"""
<div class="audio-player">
  <div class="label">Listen to this briefing</div>
  <audio controls preload="none"><source src="{audio_url}" type="audio/mpeg"></audio>
</div>"""

    cta = _build_cta(ct)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_mod.escape(clean_title)} — Full Potential AI</title>
<meta name="description" content="{html_mod.escape(description)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{html_mod.escape(clean_title)}">
<meta property="og:description" content="{html_mod.escape(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="Full Potential AI">
<meta property="og:image" content="{BASE_URL}/api/v1/og-image">
<meta property="article:published_time" content="{row.published_at}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html_mod.escape(clean_title)}">
<meta name="twitter:description" content="{html_mod.escape(description)}">
<meta name="twitter:image" content="{BASE_URL}/api/v1/og-image">
<link rel="canonical" href="{canonical}">
<link rel="alternate" type="application/rss+xml" title="Full Potential AI Insights" href="{BASE_URL}/insights/feed.xml">
<style>{SHARED_CSS}</style>
</head>
<body>
<div class="wrap">

<div class="site-header">
  <a href="/">FULL POTENTIAL AI</a>
</div>

<div class="breadcrumb">
  <a href="/">Home</a> &rarr; <a href="/insights">Insights</a> &rarr; {html_mod.escape(clean_title[:50])}
</div>

<article>
  <h1 class="article-title">{html_mod.escape(clean_title)}</h1>
  <div class="article-meta">
    <span class="tag {meta['tag_class']}">{meta['tag_label']}</span>
    <span>{pub_date}</span>
    <span>{row.domain or 'general'}</span>
    <span>{row.view_count or 0} views</span>
    <span>by Full Potential Intelligence</span>
  </div>

  {audio_block}

  <div class="article-body">
    {content_html}
  </div>
</article>

{cta}

<div class="footer">
  <a href="/intelligence">Intelligence Feed</a> &middot;
  <a href="/insights">All Insights</a> &middot;
  <a href="/insights/feed.xml">RSS</a> &middot;
  <a href="/">Full Potential AI</a>
  <br><br>&copy; {datetime.now().year} Full Potential AI
</div>

</div>
<script>{SUBSCRIBE_JS}</script>
</body>
</html>"""
    return HTMLResponse(content=page)


# ═══════════════════════════════════════════════════════════════════════════════
# Podcast RSS (for audio briefings)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/audio/feed.xml")
async def audio_podcast_rss():
    async with async_session() as session:
        rows = (await session.execute(
            select(PublishedContentRow)
            .where(PublishedContentRow.content_type == "audio_briefing")
            .order_by(PublishedContentRow.published_at.desc())
            .limit(50)
        )).scalars().all()

    items = ""
    for r in rows:
        clean = _clean_title(r.title)
        link = f"{BASE_URL}/insights/{r.id}"
        mp3_match = re.search(r'(briefing-[\d-]+\.mp3)', r.body or '')
        mp3_url = f"{BASE_URL}/api/v1/audio/file/{mp3_match.group(1)}" if mp3_match else ""
        length = (r.gate_details or {}).get("bytes", 0) if isinstance(r.gate_details, dict) else 0
        pub = r.published_at.strftime('%a, %d %b %Y %H:%M:%S +0000') if isinstance(r.published_at, datetime) else str(r.published_at)
        desc = _excerpt(r.body, 300)
        if mp3_url:
            items += f"""
    <item>
      <title>{xml_escape(clean)}</title>
      <link>{link}</link>
      <guid isPermaLink="false">{r.id}</guid>
      <description>{xml_escape(desc)}</description>
      <enclosure url="{mp3_url}" length="{length}" type="audio/mpeg"/>
      <pubDate>{pub}</pubDate>
    </item>"""

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Full Potential AI — Daily Intelligence Briefing</title>
    <link>{BASE_URL}/insights</link>
    <description>AI-generated audio briefings from the frontier. What happened in AI today, synthesized and spoken.</description>
    <language>en-us</language>
    <itunes:author>Full Potential AI</itunes:author>
    <itunes:summary>Daily AI intelligence briefings from the Full Potential Index — scanning 18+ sources across the AI frontier.</itunes:summary>
    <itunes:category text="Technology"/>
    <itunes:explicit>false</itunes:explicit>
    <atom:link href="{BASE_URL}/audio/feed.xml" rel="self" type="application/rss+xml"/>
    {items}
  </channel>
</rss>"""
    return Response(content=rss, media_type="application/rss+xml")


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSPARENCY — Public conscience decisions log
# ═══════════════════════════════════════════════════════════════════════════════

TRANSPARENCY_CSS = """
.tp-hero{text-align:center;margin-bottom:48px}
.tp-hero h1{font-size:2.2rem;color:#e8e8f8;margin-bottom:12px}
.tp-hero p{color:var(--dim);font-size:1rem;max-width:560px;margin:0 auto;line-height:1.7}

.tp-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:16px;margin-bottom:48px}
.tp-stat{padding:24px;background:var(--card);border:1px solid var(--border);border-radius:10px;text-align:center}
.tp-stat-num{font-family:'IBM Plex Mono',monospace;font-size:2rem;font-weight:600}
.tp-stat-num.green{color:var(--green)}
.tp-stat-num.red{color:var(--red)}
.tp-stat-num.accent{color:var(--accent)}
.tp-stat-num.gold{color:var(--gold)}
.tp-stat-label{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:var(--dim);
               margin-top:6px;text-transform:uppercase;letter-spacing:1px}

.tp-section{margin-bottom:48px}
.tp-section h2{font-size:1.3rem;color:#e0e0f0;margin-bottom:6px;
               padding-bottom:10px;border-bottom:1px solid var(--border)}
.tp-section-sub{font-size:0.85rem;color:var(--dim);margin-bottom:20px}

.tp-row{padding:16px 20px;background:var(--card);border:1px solid var(--border);border-radius:8px;margin-bottom:10px}
.tp-row-title{font-size:0.95rem;color:#d0d0e0;margin-bottom:6px;line-height:1.4}
.tp-row-meta{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:var(--dim);
             display:flex;gap:12px;flex-wrap:wrap;align-items:center}
.tp-badge{padding:2px 8px;border-radius:3px;font-size:0.65rem;text-transform:uppercase;
          letter-spacing:0.5px;font-weight:600}
.tp-badge.passed{background:rgba(34,204,136,0.1);color:var(--green);border:1px solid rgba(34,204,136,0.3)}
.tp-badge.blocked{background:rgba(255,68,102,0.1);color:var(--red);border:1px solid rgba(255,68,102,0.3)}
.tp-badge.pending{background:rgba(255,184,0,0.1);color:var(--gold);border:1px solid rgba(255,184,0,0.3)}
.tp-badge.adopted{background:rgba(0,212,255,0.1);color:var(--accent);border:1px solid rgba(0,212,255,0.3)}

.tp-filters{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.tp-filter{font-family:'IBM Plex Mono',monospace;font-size:0.65rem;padding:2px 6px;
           border-radius:3px;border:1px solid var(--border)}
.tp-filter.pass{color:var(--green);border-color:rgba(34,204,136,0.2)}
.tp-filter.fail{color:var(--red);border-color:rgba(255,68,102,0.2)}

.tp-bar{height:8px;border-radius:4px;background:var(--card);border:1px solid var(--border);
        margin:20px 0 8px;overflow:hidden;display:flex}
.tp-bar-fill-green{background:var(--green);height:100%}
.tp-bar-fill-red{background:var(--red);height:100%}
.tp-bar-fill-gold{background:var(--gold);height:100%}
.tp-bar-labels{display:flex;justify-content:space-between;font-family:'IBM Plex Mono',monospace;
               font-size:0.65rem;color:var(--dim)}

.tp-live-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--green);
             margin-right:6px;animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}

.tp-timestamp{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:var(--dim);text-align:center;margin-top:32px}
"""


@router.get("/transparency", response_class=HTMLResponse)
async def transparency_page(request: Request):
    """Public conscience decisions log — every gate decision, visible to anyone."""
    try:
        await _record_pageview(request, "/transparency")
    except Exception:
        pass

    async with async_session() as session:
        total_content = (await session.execute(
            select(func.count()).select_from(PublishedContentRow)
        )).scalar() or 0

        content_with_gate = (await session.execute(
            select(PublishedContentRow.gate_decision, func.count())
            .group_by(PublishedContentRow.gate_decision)
        )).all()
        gate_counts = dict(content_with_gate)
        published_passed = gate_counts.get("passed", 0)

        total_proposals = (await session.execute(
            select(func.count()).select_from(ExecutionBriefRow)
        )).scalar() or 0

        status_counts_raw = (await session.execute(
            select(ExecutionBriefRow.status, func.count())
            .group_by(ExecutionBriefRow.status)
        )).all()
        status_counts = dict(status_counts_raw)

        blocked = status_counts.get("gate_blocked", 0)
        adopted = status_counts.get("adopted", 0) + status_counts.get("implemented", 0)
        pending_review = status_counts.get("needs_human_review", 0)

        total_entries = (await session.execute(
            select(func.count()).select_from(IndexEntryRow)
        )).scalar() or 0

        source_count = (await session.execute(
            select(func.count(func.distinct(IndexEntryRow.source)))
        )).scalar() or 0

        recent_published = (await session.execute(
            select(PublishedContentRow)
            .order_by(PublishedContentRow.published_at.desc())
            .limit(20)
        )).scalars().all()

        recent_blocked = (await session.execute(
            select(ExecutionBriefRow)
            .where(ExecutionBriefRow.status == "gate_blocked")
            .order_by(ExecutionBriefRow.created_at.desc())
            .limit(20)
        )).scalars().all()

        recent_pending = (await session.execute(
            select(ExecutionBriefRow)
            .where(ExecutionBriefRow.status == "needs_human_review")
            .order_by(ExecutionBriefRow.created_at.desc())
            .limit(10)
        )).scalars().all()

    total_decisions = total_content + blocked
    pass_rate = (published_passed / total_decisions * 100) if total_decisions > 0 else 0
    block_rate = (blocked / total_decisions * 100) if total_decisions > 0 else 0
    pending_rate = 100 - pass_rate - block_rate if total_decisions > 0 else 0

    published_rows = ""
    for r in recent_published:
        clean = _clean_title(r.title)
        date = _format_date(r.published_at)
        ct = r.content_type
        gate_details = r.gate_details or {}
        filters_html = ""
        if isinstance(gate_details, dict) and "filters" in gate_details:
            for f in gate_details["filters"]:
                cls = "pass" if f.get("result") == "pass" else "fail"
                filters_html += f'<span class="tp-filter {cls}">{html_mod.escape(f.get("name",""))}: {html_mod.escape(f.get("reason","")[:60])}</span>'

        meta_tag = CONTENT_TYPE_META.get(ct, CONTENT_TYPE_META["insight_article"])
        published_rows += f"""<div class="tp-row">
  <div class="tp-row-title"><a href="/insights/{r.id}">{html_mod.escape(clean[:100])}</a></div>
  <div class="tp-row-meta">
    <span class="tp-badge passed">PASSED</span>
    <span>{html_mod.escape(meta_tag['tag_label'])}</span>
    <span>{date}</span>
  </div>
  {f'<div class="tp-filters">{filters_html}</div>' if filters_html else ''}
</div>"""

    blocked_rows = ""
    for b in recent_blocked:
        date = _format_date(b.created_at)
        narrative = (b.narrative or "")[:120]
        blocked_rows += f"""<div class="tp-row">
  <div class="tp-row-title" style="color:var(--dim)">{html_mod.escape((b.entry_title or '')[:100])}</div>
  <div class="tp-row-meta">
    <span class="tp-badge blocked">BLOCKED</span>
    <span>{date}</span>
  </div>
  <div style="font-size:0.82rem;color:var(--dim);margin-top:6px;font-style:italic">{html_mod.escape(narrative)}</div>
</div>"""

    pending_rows = ""
    for p in recent_pending:
        date = _format_date(p.created_at)
        pending_rows += f"""<div class="tp-row">
  <div class="tp-row-title" style="color:var(--gold)">{html_mod.escape((p.entry_title or '')[:100])}</div>
  <div class="tp-row-meta">
    <span class="tp-badge pending">AWAITING HUMAN</span>
    <span>Score: {p.relevance_score:.0%}</span>
    <span>{date}</span>
  </div>
</div>"""

    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Transparency — Full Potential AI</title>
<meta name="description" content="Every decision our AI's conscience layer made — what it approved, what it blocked, and why. Full transparency from a self-improving system.">
<meta property="og:type" content="website">
<meta property="og:title" content="AI Conscience Transparency Log — Full Potential AI">
<meta property="og:description" content="Every decision our AI's conscience layer made — published for anyone to inspect.">
<meta property="og:url" content="{BASE_URL}/transparency">
<link rel="canonical" href="{BASE_URL}/transparency">
<style>{SHARED_CSS}
{TRANSPARENCY_CSS}</style>
</head>
<body>
<div class="wrap" style="max-width:860px">

<div class="site-header">
  <a href="/">FULL POTENTIAL AI</a>
</div>

<div class="tp-hero">
  <h1>Transparency Log</h1>
  <p>
    Every piece of content this system produces passes through a five-filter conscience gate.
    This page shows every decision — what passed, what was blocked, and why.
    Nothing is hidden.
  </p>
</div>

<div class="tp-stats">
  <div class="tp-stat">
    <div class="tp-stat-num accent">{total_entries:,}</div>
    <div class="tp-stat-label">Signals Scanned</div>
  </div>
  <div class="tp-stat">
    <div class="tp-stat-num gold">{source_count}</div>
    <div class="tp-stat-label">Sources Monitored</div>
  </div>
  <div class="tp-stat">
    <div class="tp-stat-num green">{total_content}</div>
    <div class="tp-stat-label">Published</div>
  </div>
  <div class="tp-stat">
    <div class="tp-stat-num red">{blocked}</div>
    <div class="tp-stat-label">Blocked by Conscience</div>
  </div>
  <div class="tp-stat">
    <div class="tp-stat-num gold">{pending_review}</div>
    <div class="tp-stat-label">Awaiting Human Review</div>
  </div>
</div>

<div style="max-width:600px;margin:0 auto 48px">
  <div style="font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:var(--dim);margin-bottom:8px">
    Conscience Gate Pass Rate
  </div>
  <div class="tp-bar">
    <div class="tp-bar-fill-green" style="width:{pass_rate:.1f}%"></div>
    <div class="tp-bar-fill-red" style="width:{block_rate:.1f}%"></div>
    <div class="tp-bar-fill-gold" style="width:{pending_rate:.1f}%"></div>
  </div>
  <div class="tp-bar-labels">
    <span style="color:var(--green)">Passed {pass_rate:.0f}%</span>
    <span style="color:var(--red)">Blocked {block_rate:.0f}%</span>
    <span style="color:var(--gold)">Review {pending_rate:.0f}%</span>
  </div>
</div>

<div class="tp-section">
  <h2>Five-Filter Conscience Gate</h2>
  <div class="tp-section-sub">
    Every output passes five filters before publication: <b>SERVE</b> (does it help the reader?),
    <b>TRUTH</b> (is it honest and verifiable?), <b>RESPECT</b> (does it respect autonomy?),
    <b>VALUE_FIRST</b> (does it give before asking?), <b>COHERENT</b> (is it consistent with our mission?).
    Fail any one filter and the content is blocked.
  </div>
</div>

{f'''<div class="tp-section">
  <h2><span class="tp-live-dot"></span>Recently Published (passed all 5 filters)</h2>
  {published_rows}
</div>''' if published_rows else ''}

{f'''<div class="tp-section">
  <h2>Blocked by Conscience Gate</h2>
  <div class="tp-section-sub">These proposals were evaluated and rejected. The system decided they weren't good enough.</div>
  {blocked_rows}
</div>''' if blocked_rows else ''}

{f'''<div class="tp-section">
  <h2>Awaiting Human Review</h2>
  <div class="tp-section-sub">The system flagged these for human judgment — it wasn't confident enough to decide alone.</div>
  {pending_rows}
</div>''' if pending_rows else ''}

<div class="tp-section">
  <h2>How It Works</h2>
  <div style="font-size:0.95rem;color:var(--dim);line-height:1.8">
    <p style="margin-bottom:14px">This system scans {source_count} sources across the AI frontier every 30-60 minutes.
    When it finds something significant, it evaluates whether it can apply that intelligence to improve itself.</p>
    <p style="margin-bottom:14px">If it decides to act — publish an article, send an email, generate audio — the output
    must pass through a five-filter conscience gate. Each filter checks a different principle.
    If any filter fails, the output is blocked and logged here.</p>
    <p>We publish this page because we believe AI systems should be transparent about what they do and
    why. If an AI is going to act autonomously, you should be able to see every decision it makes.</p>
  </div>
</div>

<div class="cta-box">
  <div class="cta-title">Follow the build</div>
  <div class="cta-sub">We're building a self-improving AI system in public. Get the build logs.</div>
  <form class="cta-form" onsubmit="doSubscribe(event);return false">
    <input class="cta-input" type="email" placeholder="you@email.com" required id="tp-email">
    <button class="cta-btn" type="submit">Subscribe</button>
  </form>
  <div class="cta-msg" id="tp-msg"></div>
</div>

<div class="tp-timestamp">Last updated: {now_str}</div>

<div class="footer">
  <a href="/">Home</a> · <a href="/insights">Build Logs</a> · <a href="/intelligence">Intelligence Feed</a> · <a href="/insights/feed.xml">RSS</a>
</div>

</div>
<script>{SUBSCRIBE_JS}</script>
</body>
</html>"""
    return HTMLResponse(content=page)
