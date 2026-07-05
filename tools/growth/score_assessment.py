#!/usr/bin/env python3
"""Allocation Score engine — the product core behind /assessment.

Turns a lead's 15-minute intake into the promised 48h deliverable: an Allocation
Score (0-100 across capital/time/attention/people/AI/knowledge) + the three
highest-value opportunities + the routed next offer (BBB v1.4). Closes the funnel
loop so the /assessment promise is TRUE, not aspirational.

$0-marginal: runs on the Max subscription via `claude -p`, NOT the metered API.
When a real paying client's confidential data flows, move to a scoped metered key
with a burn-registry row (that's product COGS, ~$0.10-0.50/audit against a $2,500
Blueprint — beautiful CCD). Until then, subscription CLI.

Rubric source: vault 07_COMPOUNDING/Savings Map Kit v1 (§5 Allocation Score).
Routing table: vault 04_DECISION/Offers/BBB v1.4.
Usage:
  score_assessment.py --lead <path>       # score one intake → deliverable md
  score_assessment.py --url <site>        # fetch public site → pre-filled intake → score
  score_assessment.py --url <site> --first-read  # fetch/summarize only, JSON
  score_assessment.py --demo              # score a synthetic lead (proof it works)
"""
from __future__ import annotations  # lazy annotations — `Path | None` etc. must not eval at def-time (crashed real leads' scores, 2026-07-05)
import argparse, hashlib, html, json, os, re, shlex, subprocess, sys, time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from pathlib import Path

DIMENSIONS = ["capital", "time", "attention", "people", "ai", "knowledge"]
WEIGHTS = {"capital": 30, "time": 20, "attention": 10, "people": 20, "ai": 10, "knowledge": 10}

# weakest-dimension → offer (BBB v1.4)
ROUTE = {
    "capital":   "Savings Split implementation — 25% of verified savings (floor $5k / cap $50k)",
    "time":      "Intelligence Solutions — automation build by AI Builders",
    "people":    "Builder placement or team training",
    "attention": "Founder-level advisory / consulting (human-led, premium)",
    "ai":        "Intelligence Partnership — $2-5k/mo, quarterly re-audits",
    "knowledge": "Intelligence Partnership — $2-5k/mo, quarterly re-audits",
}

CTA_COPY_ENV = "ASSESSMENT_CTA_COPY"
CTA_URL_ENV = "ASSESSMENT_CTA_URL"
CTA_DRAFT_MARKER = "DRAFT - James approval required"
CTA_URL_PLACEHOLDER = "ASSESSMENT_CTA_URL"
DEFAULT_DRAFT_CTA = (
    "DRAFT: Want a done-for-you Blueprint to capture the opportunities above? "
    "James will provide the final invitation copy before this emails real leads."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {"type": "object", "properties": {d: {"type": "integer"} for d in DIMENSIONS},
                   "required": DIMENSIONS, "additionalProperties": False},
        "archetype": {"type": "string"},          # memorable 2-4 word allocation signature
        "archetype_line": {"type": "string"},     # one warm sentence explaining it
        "surprise": {"type": "string"},           # the counter-intuitive insight (the "oh wow")
        "opportunities": {"type": "array", "items": {"type": "object", "properties": {
            "title": {"type": "string"}, "dimension": {"type": "string"},
            "why": {"type": "string"}, "est_annual_value": {"type": "string"}},
            "required": ["title", "dimension", "why", "est_annual_value"], "additionalProperties": False}},
        "monday_move": {"type": "string"},        # one free thing they can do Monday, no purchase
        "share_line": {"type": "string"},         # a punchy one-liner they'd actually share
        "next_step": {"type": "string"},          # DRAFT invitation only; James provides final copy
    },
    "required": [
        "scores", "archetype", "archetype_line", "surprise",
        "opportunities", "monday_move", "share_line", "next_step",
    ],
    "additionalProperties": False,
}

PROMPT = """You are the Allocation Intelligence engine behind fullpotential.com/assessment.
Your job is to make this the best 15 minutes a business owner spends this month — sharp,
warm, genuinely useful, and a little delightful. They should leave feeling SEEN and armed,
whether or not they ever buy.

Given the intake, score how well the business allocates each scarce resource (0-100, where
100 = every unit already flows to its highest-value use, 0 = severe misallocation). Be
honest and specific — a real leak scores LOW (that's the value we find). Where the intake
is thin, infer conservatively from the business type and note the assumption.

Dimensions: capital, time, attention, people, ai, knowledge.

Then produce a GREAT deliverable:
- `archetype`: a memorable 2-4 word "allocation signature" naming their pattern (e.g.
  "Time-Trapped Operator", "Cash-Rich, Attention-Poor", "The Untapped Engine"). Sticky,
  a little fun, true — something they'd repeat to a friend.
- `archetype_line`: one warm sentence explaining the archetype in plain language.
- `surprise`: the one counter-intuitive insight — "most owners think their bottleneck is X;
  yours is actually Y." The "oh, huh" moment. Only if genuinely true from the intake.
- three `opportunities` — each tied to a weak dimension, one-line why, estimated annual $
  value (range ok; "needs data" if truly unknowable). Prefer concrete finds (SaaS overlap,
  manual work AI should do, under-priced capacity, AI spend not earning).
- `monday_move`: ONE thing they can do FOR FREE Monday morning, from this assessment alone,
  that delivers real value with no purchase. Generosity first.
- `share_line`: a punchy first-person one-liner they'd actually text a friend (e.g.
  "Just found $18k/yr leaking out of my business in 15 min — free at fullpotential.com/assessment").
- `next_step`: DRAFT ONLY — exact James voice and booking/Blueprint URL are reserved for
  approval. Write one warm, low-pressure invitation that names the Blueprint or a free
  strategy call as the way to capture the opportunities above. Prefix it with
  "DRAFT:" and do not invent scarcity, pricing, guarantees, or a URL.

Tone: an unusually sharp advisor who genuinely wants them to win. Concrete over generic.
Warm, not corporate. No hype, no scarcity, no pressure — the value is the pull.

INTAKE:
{intake}

Return ONLY JSON matching this schema (no prose):
{schema}
"""

SITE_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "business_type": {"type": "string"},
        "apparent_tools_stack": {"type": "array", "items": {"type": "string"}},
        "team_signals": {"type": "string"},
        "pricing_model": {"type": "string"},
        "ops_hints": {"type": "array", "items": {"type": "string"}},
        "first_read": {"type": "string"},
        "confidence": {"type": "string"},
    },
    "required": [
        "business_type", "apparent_tools_stack", "team_signals",
        "pricing_model", "ops_hints", "first_read", "confidence",
    ],
    "additionalProperties": False,
}

SITE_SUMMARY_PROMPT = """You are preparing the first read for a Full Potential Assessment.
Use only the public website text below. Be concrete, conservative, and helpful.

Return JSON matching this schema:
{schema}

PUBLIC SITE TEXT:
{site_text}
"""

USER_AGENT = "FPAI-AssessmentBot/1.0 (+https://fullpotential.com/assessment; read-only)"
SITE_PATHS = ("/", "/about", "/pricing", "/services")
CACHE_TTL_SECONDS = 24 * 60 * 60
MAX_PAGE_CHARS = 20000


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip = 0
        self.parts = []
        self.title_parts = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        text = " ".join(html.unescape(data).split())
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
        if not self._skip:
            self.parts.append(text)

    @property
    def text(self) -> str:
        return " ".join(self.parts)

    @property
    def title(self) -> str:
        return " ".join(self.title_parts)[:160]


def normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("empty URL")
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("only public http(s) URLs are supported")
    if not parsed.netloc:
        raise ValueError("URL must include a domain")
    if parsed.username or parsed.password:
        raise ValueError("login URLs are not supported")
    host = parsed.netloc.lower()
    return urllib.parse.urlunparse((parsed.scheme, host, parsed.path or "/", "", "", ""))


def _origin(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _domain(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.lower()


def default_cache_dir() -> Path:
    return Path(os.environ.get("FPAI_ASSESSMENT_SITE_CACHE", "~/.cache/fpai/assessment-sites")).expanduser()


def cache_path_for_url(url: str, cache_dir: Path | None = None) -> Path:
    cache_dir = cache_dir or default_cache_dir()
    domain = _domain(url)
    digest = hashlib.sha256(domain.encode("utf-8")).hexdigest()[:12]
    safe = re.sub(r"[^a-z0-9.-]+", "-", domain)
    return cache_dir / f"{safe}-{digest}.json"


def _urlopen_text(url: str, timeout: float = 8) -> tuple[int, dict, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = getattr(resp, "status", 200)
        headers = {k.lower(): v for k, v in resp.headers.items()}
        raw = resp.read(512000)
    charset = "utf-8"
    ctype = headers.get("content-type", "")
    match = re.search(r"charset=([^;\s]+)", ctype)
    if match:
        charset = match.group(1)
    return status, headers, raw.decode(charset, errors="replace")


def _robots_allows(target_url: str, fetcher=_urlopen_text, timeout: float = 8) -> bool:
    robots_url = urllib.parse.urljoin(_origin(target_url) + "/", "robots.txt")
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        status, _headers, body = fetcher(robots_url, timeout)
    except Exception:
        return True
    if status >= 400:
        return True
    parser.parse(body.splitlines())
    return parser.can_fetch(USER_AGENT, target_url)


def _extract_page(url: str, status: int, headers: dict, body: str) -> dict | None:
    ctype = headers.get("content-type", "")
    if status in {401, 403} or status >= 500:
        return None
    if ctype and "html" not in ctype.lower():
        return None
    parser = _TextExtractor()
    parser.feed(body[:MAX_PAGE_CHARS])
    text = parser.text[:MAX_PAGE_CHARS]
    if len(text) < 120:
        return None
    return {"url": url, "status": status, "title": parser.title, "text": text}


def _load_cached_site(url: str, cache_dir: Path | None = None, ttl_seconds: int = CACHE_TTL_SECONDS) -> dict | None:
    path = cache_path_for_url(url, cache_dir)
    try:
        data = json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if time.time() - float(data.get("cached_at", 0)) > ttl_seconds:
        return None
    data["cached"] = True
    return data


def _write_cached_site(url: str, data: dict, cache_dir: Path | None = None) -> None:
    path = cache_path_for_url(url, cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


def fetch_public_site(url: str, *, cache_dir: Path | None = None, timeout: float = 8,
                      fetcher=_urlopen_text, use_cache: bool = True,
                      summary_runner=None) -> dict:
    """Read public website pages only: home, about, pricing, services.

    Network reads are bounded, robots-aware, and cache by domain. Login-walled,
    non-HTML, disallowed, and failing pages are skipped instead of retried.
    """
    url = normalize_url(url)
    if use_cache:
        cached = _load_cached_site(url, cache_dir)
        if cached:
            return cached

    origin = _origin(url)
    pages = []
    seen = set()
    for path in SITE_PATHS:
        target = urllib.parse.urljoin(origin + "/", path.lstrip("/"))
        if target in seen:
            continue
        seen.add(target)
        if not _robots_allows(target, fetcher=fetcher, timeout=timeout):
            pages.append({"url": target, "status": "robots_disallowed", "title": "", "text": ""})
            continue
        try:
            status, headers, body = fetcher(target, timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            pages.append({"url": target, "status": "fetch_error", "error": str(exc)[:160], "title": "", "text": ""})
            continue
        page = _extract_page(target, int(status), headers, body)
        if page:
            pages.append(page)

    data = {
        "url": url,
        "domain": _domain(url),
        "fetched_at": int(time.time()),
        "cached_at": time.time(),
        "cached": False,
        "pages": pages,
    }
    data["summary"] = summarize_site(data, model_runner=summary_runner)
    data["intake_context"] = site_intake_context(data)
    if use_cache and any(page.get("text") for page in pages):
        _write_cached_site(url, data, cache_dir)
    return data


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def summarize_site(site: dict, model_runner=None) -> dict:
    pages = [page for page in site.get("pages", []) if page.get("text")]
    combined = "\n\n".join(f"URL: {p['url']}\nTITLE: {p.get('title','')}\n{p['text'][:6000]}" for p in pages)
    if model_runner is None and "run_claude" in globals():
        model_runner = run_claude
    if model_runner and combined:
        prompt = SITE_SUMMARY_PROMPT.format(site_text=combined[:18000], schema=json.dumps(SITE_SUMMARY_SCHEMA))
        try:
            data = model_runner(prompt)
            return {
                "business_type": str(data.get("business_type", "unknown"))[:160],
                "apparent_tools_stack": [str(x)[:80] for x in data.get("apparent_tools_stack", [])[:12]],
                "team_signals": str(data.get("team_signals", "not clear"))[:240],
                "pricing_model": str(data.get("pricing_model", "not clear"))[:180],
                "ops_hints": [str(x)[:140] for x in data.get("ops_hints", [])[:8]],
                "first_read": str(data.get("first_read", ""))[:500],
                "confidence": str(data.get("confidence", "medium"))[:40],
            }
        except Exception:
            pass
    return heuristic_site_summary(site)


def heuristic_site_summary(site: dict) -> dict:
    pages = [page for page in site.get("pages", []) if page.get("text")]
    text = " ".join(page.get("text", "") for page in pages)
    low = text.lower()
    stack_markers = {
        "Shopify": ("shopify", "cart", "checkout"),
        "WordPress": ("wp-content", "wordpress"),
        "Webflow": ("webflow",),
        "Squarespace": ("squarespace",),
        "Calendly": ("calendly", "schedule a call"),
        "HubSpot": ("hubspot",),
        "Stripe": ("stripe",),
        "Klaviyo": ("klaviyo",),
        "Mailchimp": ("mailchimp",),
        "Meta Pixel": ("facebook pixel", "fbq("),
        "Google Analytics": ("google analytics", "gtag("),
        "Intercom": ("intercom",),
        "Zapier": ("zapier",),
    }
    tools = [name for name, markers in stack_markers.items() if _contains_any(low, markers)]
    if _contains_any(low, ("agency", "marketing", "brand", "creative studio")):
        business_type = "agency or services firm"
    elif _contains_any(low, ("software", "platform", "saas", "app", "api")):
        business_type = "software or platform business"
    elif _contains_any(low, ("clinic", "wellness", "therapy", "medical", "care")):
        business_type = "wellness or care practice"
    elif _contains_any(low, ("restaurant", "menu", "reservation", "catering")):
        business_type = "hospitality business"
    elif _contains_any(low, ("shop", "cart", "shipping", "collection")):
        business_type = "commerce business"
    else:
        business_type = "business type not fully clear from public pages"

    if _contains_any(low, ("pricing", "plans", "per month", "/mo", "subscription", "membership")):
        pricing = "published package/subscription pricing signals"
    elif "$" in low or _contains_any(low, ("book a call", "request a quote", "proposal")):
        pricing = "quote or consultation-led pricing signals"
    else:
        pricing = "pricing not visible on fetched public pages"

    team = "team page or people language found" if _contains_any(low, ("our team", "founder", "co-founder", "staff", "leadership")) else "team size not visible"
    ops_hints = []
    if _contains_any(low, ("book", "schedule", "appointment", "reservation")):
        ops_hints.append("conversion depends on booking/scheduling flow")
    if _contains_any(low, ("contact us", "request a quote", "discovery call", "consultation")):
        ops_hints.append("lead capture likely runs through forms or calls")
    if _contains_any(low, ("case study", "testimonials", "reviews", "results")):
        ops_hints.append("proof assets are present and can be reused in sales follow-up")
    if _contains_any(low, ("faq", "support", "help center")):
        ops_hints.append("repeat questions may be automatable")
    if not ops_hints:
        ops_hints.append("public pages are thin; intake should confirm delivery workflow and current tool stack")
    first_read = (
        f"We can already see a likely {business_type}. "
        f"{pricing.capitalize()}. {team.capitalize()}. "
        f"Main allocation clue: {ops_hints[0]}."
    )
    return {
        "business_type": business_type,
        "apparent_tools_stack": tools,
        "team_signals": team,
        "pricing_model": pricing,
        "ops_hints": ops_hints,
        "first_read": first_read,
        "confidence": "medium" if pages else "low",
    }


def site_intake_context(site: dict) -> str:
    summary = site.get("summary", {})
    pages = [page for page in site.get("pages", []) if page.get("text")]
    page_titles = "; ".join(filter(None, (page.get("title") for page in pages))) or "no titles captured"
    return "\n".join([
        f"Website: {site.get('url', '')}",
        f"Domain: {site.get('domain', '')}",
        f"Public pages read: {', '.join(page.get('url', '') for page in pages) or 'none'}",
        f"Page titles: {page_titles}",
        f"Business type: {summary.get('business_type', 'unknown')}",
        f"Apparent tools/stack: {', '.join(summary.get('apparent_tools_stack', [])) or 'not visible'}",
        f"Team signals: {summary.get('team_signals', 'not clear')}",
        f"Pricing model: {summary.get('pricing_model', 'not clear')}",
        f"Ops hints: {'; '.join(summary.get('ops_hints', [])) or 'not clear'}",
        f"First read: {summary.get('first_read', '')}",
    ])


def _json_from_model_output(output: str) -> dict:
    out = output.strip()
    # lenient JSON extraction (model may fence or add prose despite instructions)
    if "```" in out:
        out = out.split("```", 2)[1]
        if out.startswith("json"):
            out = out[4:]
    start, end = out.find("{"), out.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON in model output: {output[:300]}")
    return json.loads(out[start:end + 1])


def _load_claude_cli_env() -> dict:
    env = dict(os.environ)
    for raw_path in (
        os.environ.get("FPAI_CLAUDE_ENV", ""),
        "~/.config/fpai/claude.env",
        "/root/.config/fpai/claude.env",
    ):
        if not raw_path:
            continue
        path = Path(raw_path).expanduser()
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            key, value = line.split("=", 1)
            env[key.strip()] = shlex.split(value.strip())[0] if value.strip() else ""
    return env


def _run_claude_cli(prompt: str) -> str:
    r = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=180,
        env=_load_claude_cli_env(),
    )
    if r.returncode != 0:
        raise RuntimeError(f"claude -p failed: {(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout


def run_claude(prompt: str) -> dict:
    """$0 via model_router subscription path, with direct Claude CLI fallback."""
    try:
        from tools.intelligence.model_router import call_model

        routed = call_model(prompt, "assessment-scorer")
        return _json_from_model_output(str(routed.get("response", "")))
    except Exception as router_exc:
        try:
            return _json_from_model_output(_run_claude_cli(prompt))
        except Exception as cli_exc:
            raise RuntimeError(f"model_router failed ({router_exc}); claude CLI fallback failed ({cli_exc})") from cli_exc


def compute(scores: dict) -> tuple[int, str]:
    total = round(sum(scores[d] * WEIGHTS[d] for d in DIMENSIONS) / sum(WEIGHTS.values()))
    weakest = min(DIMENSIONS, key=lambda d: scores[d])
    return total, weakest


def cta_config() -> tuple[str, str, bool]:
    copy = os.environ.get(CTA_COPY_ENV, "").strip()
    url = os.environ.get(CTA_URL_ENV, "").strip()
    return copy, url, bool(copy and url)


def render_next_step(weakest: str, draft_next_step: str = "") -> str:
    approved_copy, cta_url, approved = cta_config()
    if approved:
        return (
            "\n## Your next step\n\n"
            f"{approved_copy}\n\n"
            f"[Book or view the Blueprint next step]({cta_url})\n"
        )

    draft_copy = (draft_next_step or DEFAULT_DRAFT_CTA).strip()
    if not draft_copy.lower().startswith("draft"):
        draft_copy = f"DRAFT: {draft_copy}"
    return (
        f"\n## Next step ({CTA_DRAFT_MARKER})\n\n"
        f"{draft_copy}\n\n"
        f"Your weakest dimension routes to: **{ROUTE[weakest]}**\n\n"
        f"[Booking/Blueprint link placeholder]({CTA_URL_PLACEHOLDER})\n\n"
        f"_Reserved: James provides final invitation copy and sets `{CTA_URL_ENV}` "
        f"before this emails real leads._\n"
    )


def render(name: str, company: str, scores: dict, total: int, weakest: str,
           opps: list, extras: dict = None) -> str:
    extras = extras or {}
    bars = "\n".join(
        f"| {d.capitalize():10} | {scores[d]:3} | {'█' * (scores[d] // 5)}{'░' * (20 - scores[d] // 5)} |"
        for d in DIMENSIONS)
    opp_md = "\n".join(
        f"{i+1}. **{o['title']}** _(weak: {o['dimension']})_ — {o['why']} · **{o['est_annual_value']}**"
        for i, o in enumerate(opps[:3]))
    archetype = extras.get("archetype", "")
    arch_block = (f"\n## Your allocation signature: **{archetype}**\n\n"
                  f"_{extras.get('archetype_line', '')}_\n") if archetype else ""
    surprise = extras.get("surprise", "")
    surprise_block = f"\n> 💡 **The thing most owners miss:** {surprise}\n" if surprise else ""
    monday = extras.get("monday_move", "")
    monday_block = (f"\n## Your free Monday move\n\n**{monday}**\n\n"
                    f"_No purchase, no catch — do this Monday and you've already gotten value from these 15 minutes._\n") if monday else ""
    share = extras.get("share_line", "")
    share_block = f"\n---\n\n*Found this useful? \"{share}\"*\n" if share else ""
    next_step_block = render_next_step(weakest, extras.get("next_step", ""))
    return f"""# Your Full Potential Assessment — {company or name}
{arch_block}
## Allocation Score: **{total}/100**

| Resource   | Score | |
|------------|-----|--------------------|
{bars}

*This measures how much of each scarce resource already flows to its highest-value use.
Your weakest dimension — **{weakest}** — is where the most capability is currently trapped.*
{surprise_block}
## Your 3 highest-value opportunities

{opp_md}
{monday_block}
{next_step_block}
{share_block}
---
*Powered by FPOS — the Allocation Intelligence Operating System · fullpotential.com*
"""


def parse_intake(text: str) -> tuple[str, str, str]:
    name = company = intake = ""
    for line in text.splitlines():
        low = line.lower()
        if low.startswith("name:"): name = line.split(":", 1)[1].strip()
        elif low.startswith("company") or "company /" in low: company = line.split(":", 1)[1].strip() if ":" in line else ""
        elif low.startswith("bottleneck:") or low.startswith("goal:"): intake += line.split(":", 1)[1].strip() + " "
    return name, company, (intake or text)[:2000]


def score_one(intake_text: str, name: str = "", company: str = "") -> str:
    prompt = PROMPT.format(intake=intake_text, schema=json.dumps(SCHEMA))
    data = run_claude(prompt)
    scores = {d: int(data["scores"].get(d, 50)) for d in DIMENSIONS}
    total, weakest = compute(scores)
    extras = {k: data.get(k, "") for k in ("archetype", "archetype_line", "surprise", "monday_move", "share_line", "next_step")}
    return render(name, company, scores, total, weakest, data.get("opportunities", []), extras)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lead")
    ap.add_argument("--url", help="public website URL to pre-fill the intake context")
    ap.add_argument("--first-read", action="store_true", help="print URL first-read JSON instead of scoring")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    if a.demo:
        intake = ("Wellness studio in Austin — sauna + cold plunge. ~8 staff. Uses Mindbody "
                  "for booking plus a separate email tool and a scheduling spreadsheet the "
                  "front desk fills by hand. Pays for ChatGPT Team but nobody really uses it. "
                  "Wants to grow to a second location this year.")
        print(score_one(intake, "Demo Owner", "Cøntrast ATX (demo)")); return

    site = None
    if a.url:
        site = fetch_public_site(a.url)
        if a.first_read:
            print(json.dumps({
                "url": site["url"],
                "domain": site["domain"],
                "cached": site.get("cached", False),
                "summary": site.get("summary", {}),
                "intake_context": site.get("intake_context", ""),
            }, indent=2))
            return

    if not a.lead and not site:
        print("need --lead <path>, --url <site>, or --demo", file=sys.stderr); sys.exit(2)
    if a.lead:
        text = Path(a.lead).read_text()
        name, company, intake = parse_intake(text)
    else:
        name = ""
        company = (site.get("domain") if site else "")
        intake = ""
    if site:
        intake = (intake + "\n\n" if intake else "") + "PUBLIC WEBSITE PRE-FILL:\n" + site["intake_context"]
    result = score_one(intake, name, company)
    if a.out:
        Path(a.out).write_text(result); print(f"→ {a.out}")
    else:
        print(result)


if __name__ == "__main__":
    main()
