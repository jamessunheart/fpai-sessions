#!/usr/bin/env python3
"""Generate static Full Potential learn articles from local canon.

The engine is offline-safe by default: it can ask ``claude -p`` for prose when
available, but every path has a deterministic fallback so nightly generation and
tests do not depend on network or paid API access.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


EDITORIAL_TITLES = [
    "Why Most Companies Misallocate Capital",
    "Hidden Cost of Fragmented Attention",
    "Knowledge Bottleneck",
    "Executive Allocation vs Productivity",
    "Capability Flywheel",
    "Allocation Intelligence Explained",
]

DEFAULT_CANON_PATHS = [
    Path("core/STATE/FOUNDATION.md"),
    Path("core/STATE/ALLOCATION_INTELLIGENCE.md"),
    Path("core/STATE/TRUST_ECONOMICS.md"),
]


@dataclass(frozen=True)
class Article:
    title: str
    slug: str
    description: str
    kicker: str
    sections: list[tuple[str, list[str]]]
    pullquote: str


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "article"


def read_canon(repo_root: Path, paths: list[Path] | None = None) -> str:
    chunks: list[str] = []
    for rel in paths or DEFAULT_CANON_PATHS:
        path = repo_root / rel
        try:
            chunks.append(path.read_text(encoding="utf-8"))
        except OSError:
            continue
    return "\n\n".join(chunks)


def canon_excerpt(canon: str, limit: int = 7000) -> str:
    text = re.sub(r"```.*?```", "", canon, flags=re.S)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def article_prompt(title: str, canon: str) -> str:
    return (
        "Write one concise Full Potential learn article as strict JSON with keys "
        "description, kicker, pullquote, sections. sections must be a list of "
        "objects with heading and paragraphs, 3 sections max, 2 paragraphs each. "
        "Voice: clear, executive, grounded in Allocation Intelligence. "
        "CTA is handled by the template, so do not include one. "
        f"Title: {title}\nCanon:\n{canon_excerpt(canon)}"
    )


def run_claude(prompt: str, *, timeout: int = 90) -> dict | None:
    if not shutil.which("claude"):
        return None
    try:
        proc = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    match = re.search(r"\{.*\}", proc.stdout, flags=re.S)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


FALLBACKS: dict[str, Article] = {
    "why-most-companies-misallocate-capital": Article(
        title="Why Most Companies Misallocate Capital",
        slug="why-most-companies-misallocate-capital",
        description="Capital leaks when companies optimize budgets without seeing the whole allocation system.",
        kicker="The problem is rarely a lack of money. It is money routed without enough intelligence.",
        pullquote="Capital is stored trust. Misallocation is trust quietly leaking out of the business.",
        sections=[
            (
                "Capital is only one resource",
                [
                    "Most teams manage capital as if it lives in finance alone. The real allocation question crosses software, labor, attention, knowledge, and AI. A dollar spent on the wrong tool often creates more hidden cost in training, handoffs, and executive attention than the invoice shows.",
                    "That is why the first pass is not a budget cut. It is a map of where capital is supposed to create future capability and where it is only preserving old motion.",
                ],
            ),
            (
                "The leaks live between departments",
                [
                    "Finance sees invoices. Operations sees workarounds. Leaders see pressure. Nobody sees the full chain from spend to capability unless the business measures allocation as one system.",
                    "The highest-value opportunities usually sit in the gaps: unused SaaS, duplicated workflows, AI tools without operating changes, and manual work that survives because no owner has the whole picture.",
                ],
            ),
            (
                "Better allocation compounds",
                [
                    "A good allocation does more than save money. It improves the next decision. The business learns which resources create capability, which promises were fiction, and which investments deserve more trust.",
                    "That is the core of Allocation Intelligence: route scarce resources, reason about the highest future capability, then feed the proof back into the next allocation.",
                ],
            ),
        ],
    ),
    "hidden-cost-of-fragmented-attention": Article(
        title="Hidden Cost of Fragmented Attention",
        slug="hidden-cost-of-fragmented-attention",
        description="Fragmented attention is an operating cost that rarely appears on the P&L.",
        kicker="Every business pays for attention twice: once in payroll, again in decisions that never compound.",
        pullquote="Attention is the first resource. When it fragments, every other allocation gets noisier.",
        sections=[
            (
                "The invoice is invisible",
                [
                    "A scattered executive calendar does not look like a cost center, but it behaves like one. Every unnecessary context switch taxes judgment, slows follow-through, and keeps the highest-value questions from receiving the cleanest attention.",
                    "The damage spreads because leaders allocate more than time. They allocate trust, priority, urgency, and permission. Fragmented attention fragments the business beneath it.",
                ],
            ),
            (
                "Productivity tools can make it worse",
                [
                    "More dashboards, automations, meetings, and AI assistants can increase noise if they do not route decisions to the right level. The point is not to do more tasks. The point is to protect the attention that changes outcomes.",
                    "A healthy system separates what only leadership can decide from what AI, operators, or existing rules can carry downstream.",
                ],
            ),
            (
                "Attention should route like capital",
                [
                    "The same question applies: where should the next scarce resource go? For attention, the answer is wherever judgment, alignment, or trust materially changes the result.",
                    "Everything else should become a surface, rule, automation, or delegated work order. That is how attention turns from a bottleneck into a compounding asset.",
                ],
            ),
        ],
    ),
}


def fallback_article(title: str) -> Article:
    slug = slugify(title)
    if slug in FALLBACKS:
        return FALLBACKS[slug]
    return Article(
        title=title,
        slug=slug,
        description=f"{title} through the lens of Allocation Intelligence.",
        kicker="The highest-leverage businesses improve the quality of allocation before they chase more activity.",
        pullquote="The organizations that win are the ones that allocate scarce resources best.",
        sections=[
            (
                "The allocation question",
                [
                    "Every organization is continuously deciding where the next scarce resource should go. Capital, time, people, knowledge, AI, and attention all enter the same test: which allocation creates the greatest future capability?",
                    "When that question is answered locally by isolated teams, the business gets local optimization and system-wide waste.",
                ],
            ),
            (
                "The better operating loop",
                [
                    "Allocation Intelligence turns scattered decisions into one loop: route the resource, reason about future capability, execute, measure the consequence, and learn before repeating.",
                    "The output is not merely lower cost. The output is a business that becomes more capable with every completed cycle.",
                ],
            ),
        ],
    )


def coerce_article(title: str, payload: dict | None) -> Article:
    fallback = fallback_article(title)
    if not payload:
        return fallback
    sections: list[tuple[str, list[str]]] = []
    for raw in payload.get("sections") or []:
        if not isinstance(raw, dict):
            continue
        heading = str(raw.get("heading") or "").strip()
        paragraphs = [str(p).strip() for p in raw.get("paragraphs") or [] if str(p).strip()]
        if heading and paragraphs:
            sections.append((heading, paragraphs[:2]))
    if not sections:
        sections = fallback.sections
    return Article(
        title=title,
        slug=fallback.slug,
        description=str(payload.get("description") or fallback.description).strip(),
        kicker=str(payload.get("kicker") or fallback.kicker).strip(),
        pullquote=str(payload.get("pullquote") or fallback.pullquote).strip(),
        sections=sections[:4],
    )


def render_article(article: Article) -> str:
    section_html: list[str] = []
    for index, (heading, paragraphs) in enumerate(article.sections):
        if index == 1:
            section_html.append(f'  <p class="pull">{html.escape(article.pullquote)}</p>')
        section_html.append(f"  <h2>{html.escape(heading)}</h2>")
        for paragraph in paragraphs:
            section_html.append(f"  <p>{html.escape(paragraph)}</p>")
    body = "\n\n".join(section_html)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(article.title)} — Full Potential</title>
  <meta name="description" content="{html.escape(article.description)}">
  <style>
    :root{{--cream:#FFF9EF;--sand:#F2E7D2;--gold:#D9A441;--text:#17211A;--muted:#5D675F;--green:#3E7C4F;--deep:#1B3A5C;--blue:#2563EB;--card:#FFF;--line:#E8DCC4}}
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:Georgia,'Times New Roman',serif;background:var(--cream);color:var(--text);line-height:1.75;font-size:1.06rem}}
    .wrap{{max-width:680px;margin:0 auto;padding:0 22px}}
    nav{{display:flex;justify-content:space-between;align-items:center;padding:18px 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
    nav .logo{{font-weight:800;color:var(--deep);text-decoration:none}}
    nav a.back{{color:var(--muted);text-decoration:none;font-size:.9rem}}
    h1{{font-size:clamp(1.9rem,5vw,2.6rem);line-height:1.15;color:var(--deep);padding:26px 0 6px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
    .kicker{{color:var(--muted);font-style:italic;padding-bottom:26px;border-bottom:1px solid var(--line);margin-bottom:28px}}
    h2{{color:var(--deep);font-size:1.3rem;margin:34px 0 10px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
    p{{margin:14px 0}}
    .pull{{font-style:italic;color:var(--deep);border-left:3px solid var(--gold);padding:6px 0 6px 18px;margin:24px 0;font-size:1.12rem}}
    .ctabox{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:28px;text-align:center;margin:44px 0}}
    .ctabox h3{{color:var(--deep);font-family:-apple-system,sans-serif;margin-bottom:8px}}
    .ctabox p{{color:var(--muted);font-size:.98rem}}
    .cta{{display:inline-block;background:var(--blue);color:#fff;font-weight:700;padding:13px 30px;border-radius:999px;text-decoration:none;font-family:-apple-system,sans-serif;margin-top:14px}}
    .fine{{color:var(--muted);font-size:.85rem;text-align:center;padding:10px 0 50px;font-family:-apple-system,sans-serif}}
  </style>
</head>
<body>
<div class="wrap">
  <nav>
    <a class="logo" href="/">FP · FULL POTENTIAL</a>
    <a class="back" href="/assessment">Free Assessment -&gt;</a>
  </nav>

  <h1>{html.escape(article.title)}</h1>
  <p class="kicker">{html.escape(article.kicker)}</p>

{body}

  <div class="ctabox">
    <h3>See your own allocation clearly</h3>
    <p>The free Full Potential Assessment returns your Allocation Score and your three highest-value opportunities.</p>
    <a class="cta" href="/assessment">Start the Free Assessment -&gt;</a>
  </div>

  <p class="fine">Powered by FPOS — the Allocation Intelligence Operating System · <a href="/" style="color:inherit">fullpotential.com</a></p>
</div>
</body>
</html>
"""


def existing_slugs(output_dir: Path) -> set[str]:
    return {path.stem for path in output_dir.glob("*.html")}


def pick_next_title(output_dir: Path) -> str:
    done = existing_slugs(output_dir)
    for title in EDITORIAL_TITLES:
        if slugify(title) not in done:
            return title
    return EDITORIAL_TITLES[0]


def generate_article(
    *,
    repo_root: Path,
    output_dir: Path,
    title: str | None = None,
    use_claude: bool = True,
    claude_runner: Callable[[str], dict | None] | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = title or pick_next_title(output_dir)
    canon = read_canon(repo_root)
    payload = None
    if use_claude:
        payload = (claude_runner or run_claude)(article_prompt(selected, canon))
    article = coerce_article(selected, payload)
    path = output_dir / f"{article.slug}.html"
    path.write_text(render_article(article), encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-dir", type=Path, default=Path("sites/fullpotential-com/learn"))
    parser.add_argument("--title", choices=EDITORIAL_TITLES)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--no-claude", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    written = []
    for index in range(max(args.count, 1)):
        title = args.title if index == 0 else None
        written.append(
            generate_article(
                repo_root=repo_root,
                output_dir=output_dir,
                title=title,
                use_claude=not args.no_claude,
            )
        )
    print(json.dumps({"ok": True, "articles": [str(path) for path in written]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
