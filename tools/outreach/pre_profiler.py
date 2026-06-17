#!/usr/bin/env python3
"""Public-source-only contact pre-profiler for warm first outreach."""
from __future__ import annotations

import argparse
import html
import ipaddress
import json
import os
import re
import socket
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.outreach import profile_store
from tools.probe import rate_governor

OUTREACH_VOICE_PATH = REPO_ROOT / "core" / "STATE" / "OUTREACH_VOICE.md"
MAX_FETCHES_PER_MINUTE = 5
MAX_RESONANCE_POINTS = 3
USER_AGENT = "fpai-contact-pre-profiler/1.0 (+public sources only)"
PUBLIC_SCHEMES = {"http", "https"}
PRIVATE_HOST_MARKERS = ("localhost", "127.0.0.1", "0.0.0.0", ".local", ".internal")
LOGIN_MARKERS = ("/login", "/signin", "/sign-in", "/auth", "/account", "/members", "/private")
SENSITIVE_PATTERNS = (
    re.compile(r"\b(health|diagnosis|therapy|medical|medication|illness|trauma)\b", re.I),
    re.compile(r"\b(family|children|spouse|partner|divorce|pregnant|pregnancy)\b", re.I),
    re.compile(r"\b(debt|salary|income|bank|wallet|financial|net worth|credit score)\b", re.I),
)
GENERIC_RESONANCE = {
    "interested in growth",
    "personal growth",
    "likes ai",
    "interested in ai",
    "wants to improve",
    "full potential",
}
SPECIFIC_KEYWORDS = (
    "builder", "founder", "coach", "teacher", "community", "city", "village", "conscious",
    "regenerative", "product", "project", "research", "published", "podcast", "tool", "retreat",
    "creator", "artist", "education", "wellbeing", "coordination", "climate", "systems",
)


@dataclass(frozen=True)
class ContactRecord:
    id: int | None
    name: str
    email: str | None = None
    channel: str | None = None
    notes: str | None = None
    url_hints: tuple[str, ...] = ()
    company: str | None = None


@dataclass(frozen=True)
class PublicSource:
    kind: str
    url: str
    title: str = ""
    text: str = ""


@dataclass(frozen=True)
class ContactProfile:
    contact_id: int | None
    researched_at: str
    sources: dict[str, str]
    summary: str
    resonance_points: list[dict[str, str]]
    suggested_subject: str
    suggested_body: str
    raw_notes: str
    confidence: float


class FetchRateLimiter:
    def __init__(self, *, max_per_minute: int = MAX_FETCHES_PER_MINUTE, sleeper: Callable[[float], None] = time.sleep) -> None:
        if max_per_minute <= 0:
            raise ValueError("max_per_minute must be positive")
        self.min_interval = 60.0 / max_per_minute
        self.sleeper = sleeper
        self._last_fetch: float | None = None

    def wait(self) -> None:
        now = time.monotonic()
        if self._last_fetch is not None:
            remaining = self.min_interval - (now - self._last_fetch)
            if remaining > 0:
                self.sleeper(remaining)
                now = time.monotonic()
        self._last_fetch = now


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_contact(row: dict[str, Any] | ContactRecord) -> ContactRecord:
    if isinstance(row, ContactRecord):
        return row
    hints = row.get("url_hints") or row.get("urls") or row.get("url") or ()
    if isinstance(hints, str):
        hints = [hints]
    elif isinstance(hints, dict):
        hints = [str(value) for value in hints.values() if value]
    return ContactRecord(
        id=int(row["id"]) if row.get("id") is not None else None,
        name=str(row.get("name") or "").strip(),
        email=str(row.get("email") or "").strip() or None,
        channel=str(row.get("channel") or "").strip() or None,
        notes=str(row.get("notes") or "").strip() or None,
        url_hints=tuple(str(url).strip() for url in hints if str(url).strip()),
        company=str(row.get("company") or "").strip() or None,
    )


def is_public_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").lower()
    path = parsed.path.lower()
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip and (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return False
    if looks_like_numeric_ipv4_host(host):
        return False
    return (
        parsed.scheme in PUBLIC_SCHEMES
        and bool(host)
        and not any(marker in host for marker in PRIVATE_HOST_MARKERS)
        and not any(marker in path for marker in LOGIN_MARKERS)
    )


def looks_like_numeric_ipv4_host(host: str) -> bool:
    if not host:
        return False
    labels = host.split(".")
    if len(labels) > 4:
        return False
    numericish = re.compile(r"^(?:0x[0-9a-f]+|[0-9]+)$", re.I)
    return all(bool(numericish.match(label)) for label in labels)


def ip_is_public(ip: ipaddress._BaseAddress) -> bool:
    return bool(ip.is_global)


def host_resolves_public(host: str, *, resolver: Callable[..., Any] = socket.getaddrinfo) -> bool:
    if looks_like_numeric_ipv4_host(host):
        return False
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        return ip_is_public(literal)
    try:
        rows = resolver(host, None, proto=socket.IPPROTO_TCP)
    except Exception:
        return False
    addresses: list[ipaddress._BaseAddress] = []
    for row in rows:
        sockaddr = row[4]
        if not sockaddr:
            continue
        try:
            addresses.append(ipaddress.ip_address(sockaddr[0]))
        except ValueError:
            return False
    return bool(addresses) and all(ip_is_public(address) for address in addresses)


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def normalize_public_url(url: str) -> str | None:
    candidate = str(url or "").strip()
    if not candidate:
        return None
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    if not is_public_url(candidate):
        return None
    return candidate


def source_kind(url: str) -> str:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if "linkedin.com" in host:
        return "linkedin"
    if "instagram.com" in host:
        return "instagram"
    if "twitter.com" in host or "x.com" in host:
        return "twitter"
    if "github.com" in host:
        return "github"
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "podcasts." in host or "spotify.com" in host or "apple.com" in host:
        return "published_work"
    return "website"


def strip_html(text: str) -> tuple[str, str]:
    cleaned = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", text)
    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", cleaned)
    title = " ".join(html.unescape(title_match.group(1)).split()) if title_match else ""
    cleaned = re.sub(r"(?is)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(r"(?is)</(p|div|li|h[1-6])>", "\n", cleaned)
    cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
    body = " ".join(html.unescape(cleaned).split())
    return title[:180], body[:6000]


def redact_sensitive_context(text: str) -> str:
    safe_lines: list[str] = []
    for line in str(text or "").splitlines() or [str(text or "")]:
        if any(pattern.search(line) for pattern in SENSITIVE_PATTERNS):
            continue
        safe_lines.append(line)
    return "\n".join(safe_lines).strip()


def fetch_public_source(
    url: str,
    *,
    urlopen: Any | None = None,
    limiter: FetchRateLimiter | None = None,
    resolver: Callable[..., Any] = socket.getaddrinfo,
) -> PublicSource | None:
    normalized = normalize_public_url(url)
    if not normalized:
        return None
    parsed = urllib.parse.urlparse(normalized)
    host = parsed.hostname or ""
    if urlopen is None and not host_resolves_public(host, resolver=resolver):
        return None
    if limiter:
        limiter.wait()
    request = urllib.request.Request(normalized, headers={"user-agent": USER_AGENT, "accept": "text/html,application/xhtml+xml"})
    try:
        opener = urllib.request.build_opener(NoRedirectHandler())
        opener_or_urlopen = urlopen or opener.open
        with opener_or_urlopen(request, timeout=20) as response:
            content_type = str(getattr(response, "headers", {}).get("content-type", ""))
            body = response.read(750_000).decode("utf-8", errors="replace")
    except Exception:
        return None
    if content_type and "text/html" not in content_type and "application/xhtml" not in content_type:
        title, text = "", body[:4000]
    else:
        title, text = strip_html(body)
    text = redact_sensitive_context(text)
    return PublicSource(source_kind(normalized), normalized, title, text)


def default_searcher(_query: str) -> list[str]:
    """No-op default keeps the profiler side-effect-light in unattended runs."""
    return []


def search_queries(contact: ContactRecord) -> list[str]:
    queries = [f"{contact.name} site:linkedin.com", f"{contact.name} instagram"]
    if contact.company:
        queries.append(f"{contact.name} {contact.company}")
    return queries


def collect_sources(
    contact: ContactRecord,
    *,
    searcher: Callable[[str], list[str]] = default_searcher,
    fetcher: Callable[[str], PublicSource | None] | None = None,
) -> list[PublicSource]:
    fetch = fetcher or fetch_public_source
    urls: list[str] = []
    for hint in contact.url_hints:
        normalized = normalize_public_url(hint)
        if normalized:
            urls.append(normalized)
    for query in search_queries(contact):
        try:
            urls.extend(searcher(query))
        except Exception:
            continue
    seen: set[str] = set()
    sources: list[PublicSource] = []
    for url in urls:
        normalized = normalize_public_url(url)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        source = fetch(normalized)
        if source:
            sources.append(source)
    return sources


def sentence_candidates(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", " ".join(str(text or "").split()))
    return [part.strip() for part in parts if 35 <= len(part.strip()) <= 240]


def score_sentence(sentence: str) -> int:
    lower = sentence.lower()
    return sum(2 for word in SPECIFIC_KEYWORDS if word in lower) + min(len(sentence) // 80, 2)


def best_public_sentences(sources: Iterable[PublicSource], *, limit: int = 4) -> list[str]:
    candidates: list[str] = []
    for source in sources:
        if source.title:
            candidates.append(source.title)
        candidates.extend(sentence_candidates(source.text))
    ranked = sorted(candidates, key=score_sentence, reverse=True)
    result: list[str] = []
    seen: set[str] = set()
    for item in ranked:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def note_signal(notes: str | None) -> str | None:
    safe = redact_sensitive_context(notes or "")
    if not safe:
        return None
    return " ".join(safe.split())[:260]


def is_specific_resonance(point: str) -> bool:
    normalized = " ".join(str(point or "").lower().split()).strip(". ")
    if normalized in GENERIC_RESONANCE:
        return False
    return len(normalized.split()) >= 5 and any(word in normalized for word in SPECIFIC_KEYWORDS)


def resonance_from_text(text: str, *, why_prefix: str) -> dict[str, str] | None:
    compact = " ".join(str(text or "").split()).strip(" .")
    if not compact:
        return None
    if len(compact) > 150:
        compact = compact[:147].rsplit(" ", 1)[0] + "..."
    if not is_specific_resonance(compact):
        return None
    return {
        "point": compact,
        "why_relevant": f"{why_prefix}; this gives the first message a concrete bridge into full-potential inquiry.",
    }


def build_resonance_points(contact: ContactRecord, sources: list[PublicSource]) -> list[dict[str, str]]:
    points: list[dict[str, str]] = []
    note = note_signal(contact.notes)
    if note:
        point = resonance_from_text(note, why_prefix="James supplied this directly")
        if point:
            points.append(point)
        else:
            points.append({
                "point": note,
                "why_relevant": "James supplied this directly; treat it as the highest-confidence context even when public sources are sparse.",
            })
    for sentence in best_public_sentences(sources, limit=8):
        point = resonance_from_text(sentence, why_prefix="Public profile signal")
        if point and point["point"].lower() not in {p["point"].lower() for p in points}:
            points.append(point)
        if len(points) >= MAX_RESONANCE_POINTS:
            break
    return points[:MAX_RESONANCE_POINTS]


def summarize(contact: ContactRecord, sources: list[PublicSource], resonance_points: list[dict[str, str]]) -> str:
    lead = f"{contact.name} is a contact awaiting first outreach."
    note = note_signal(contact.notes)
    if note:
        lead = f"James's note says {contact.name} is connected to: {note}."
    elif sources:
        public = best_public_sentences(sources, limit=2)
        if public:
            lead = f"{contact.name}'s public presence centers on {public[0].rstrip('.') }."
    if resonance_points:
        bridge = f"The strongest warm bridge is {resonance_points[0]['point'].rstrip('.') }."
    else:
        bridge = "Public information is sparse, so the first message should stay light and avoid pretending familiarity."
    return f"{lead} {bridge}"


def canonical_email_body() -> str:
    if not OUTREACH_VOICE_PATH.exists():
        return (
            "I'm Sunheart AI. Sunheart built me around one question: what does your full potential "
            "actually look like - and what's in the way?"
        )
    text = OUTREACH_VOICE_PATH.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'## Email Body\s+"(?P<body>.*?)"', text, re.S)
    if match:
        return match.group("body").strip()
    return " ".join(text.split())


def draft_outreach(contact: ContactRecord, resonance_points: list[dict[str, str]]) -> tuple[str, str]:
    first_name = (contact.name.split() or ["there"])[0]
    subject_detail = resonance_points[0]["point"] if resonance_points else "your full potential"
    subject_detail = subject_detail[:60].rstrip(" .,")
    subject = f"{first_name} - {subject_detail}"
    if resonance_points:
        bridge = resonance_points[0]["point"]
        body = (
            f"Hi {first_name},\n\n"
            f"I came across your work around {bridge}. That felt connected to the question Sunheart AI is built around: "
            "what does your full potential actually look like - and what's in the way?\n\n"
            "This starts with one real question, not a generic demo. If you are open to it, I would like to begin there.\n\n"
            "Reply STOP to opt out."
        )
    else:
        body = canonical_email_body().replace("[first_name]", first_name).replace("[link]", "@sunheartbrain_bot")
        if "stop to opt out" not in body.lower():
            body = f"{body}\n\nReply STOP to opt out."
    return subject, body


def confidence_score(contact: ContactRecord, sources: list[PublicSource], resonance_points: list[dict[str, str]]) -> float:
    score = 0.15
    if note_signal(contact.notes):
        score += 0.35
    if sources:
        score += min(0.30, 0.10 * len(sources))
    if any(source.text for source in sources):
        score += 0.10
    if resonance_points:
        score += min(0.10, 0.04 * len(resonance_points))
    return round(max(0.0, min(1.0, score)), 2)


def raw_research_notes(contact: ContactRecord, sources: list[PublicSource]) -> str:
    sections = [f"contact={contact.name}"]
    note = note_signal(contact.notes)
    if note:
        sections.append(f"james_notes={note}")
    for source in sources:
        text = source.text[:1200]
        sections.append(f"{source.kind} {source.url}\ntitle={source.title}\n{text}")
    if not sources:
        sections.append("public_sources=none")
    return redact_sensitive_context("\n\n".join(sections))[:8000]


def build_profile(
    contact_input: dict[str, Any] | ContactRecord,
    *,
    searcher: Callable[[str], list[str]] = default_searcher,
    fetcher: Callable[[str], PublicSource | None] | None = None,
) -> ContactProfile:
    contact = normalize_contact(contact_input)
    sources = collect_sources(contact, searcher=searcher, fetcher=fetcher)
    points = build_resonance_points(contact, sources)
    summary = summarize(contact, sources, points)
    subject, body = draft_outreach(contact, points)
    source_map: dict[str, str] = {}
    for source in sources:
        source_map.setdefault(source.kind, source.url)
    return ContactProfile(
        contact_id=contact.id,
        researched_at=utc_stamp(),
        sources=source_map,
        summary=summary,
        resonance_points=points,
        suggested_subject=subject,
        suggested_body=body,
        raw_notes=raw_research_notes(contact, sources),
        confidence=confidence_score(contact, sources, points),
    )


def profile_and_store(
    contact_input: dict[str, Any] | ContactRecord,
    *,
    conn: Any | None = None,
    connector: Callable[[], Any] = rate_governor.connect_from_env,
    searcher: Callable[[str], list[str]] = default_searcher,
    fetcher: Callable[[str], PublicSource | None] | None = None,
) -> ContactProfile:
    profile = build_profile(contact_input, searcher=searcher, fetcher=fetcher)
    own_conn = conn is None
    db = conn or connector()
    try:
        profile_store.insert_contact_profile(db, profile=profile)
    finally:
        if own_conn and hasattr(db, "close"):
            db.close()
    return profile


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a private pre-contact profile from public sources.")
    parser.add_argument("--contact-json", required=True, help="JSON object with name, optional id/email/notes/url_hints.")
    parser.add_argument("--store", action="store_true", help="Insert the generated profile into brain_index.contact_profiles.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    contact = json.loads(args.contact_json)
    limiter = FetchRateLimiter(sleeper=time.sleep)
    fetcher = lambda url: fetch_public_source(url, limiter=limiter)
    if args.store:
        profile = profile_and_store(contact, fetcher=fetcher)
    else:
        profile = build_profile(contact, fetcher=fetcher)
    print(json.dumps(asdict(profile), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
