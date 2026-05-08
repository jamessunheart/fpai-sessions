#!/usr/bin/env python3
"""Generate cockpit-map.html from core/STATE/NOW.md + core/STATE/catalog.json.

Single self-contained HTML: priority view, money view, attention view, drift flags,
service tree by tag. Open in any browser. Re-run after editing NOW.md.

Usage: python3 tools/gen_cockpit_map.py
"""
from __future__ import annotations
import json
import os
import re
import subprocess
from datetime import datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOW = ROOT / "core/STATE/NOW.md"
CATALOG = ROOT / "core/STATE/catalog.json"
SERVICES_DIR = ROOT / "SERVICES"
OUT = ROOT / "cockpit-map.html"
AGREEMENTS_REGISTRY = ROOT / "core/INTENT/AGREEMENTS/registry.json"
INTENT_DIR = ROOT / "core/INTENT"


def read_now() -> str:
    return NOW.read_text(encoding="utf-8")


def read_catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def list_services() -> list[str]:
    if not SERVICES_DIR.exists():
        return []
    return sorted(
        p.name
        for p in SERVICES_DIR.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def recent_commits(n: int = 10) -> list[tuple[str, str]]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(ROOT), "log", f"-{n}", "--pretty=format:%h%x09%s"],
            text=True,
        )
        return [tuple(line.split("\t", 1)) for line in out.strip().split("\n") if line]
    except Exception:
        return []


def last_commit_iso() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "log", "-1", "--pretty=format:%cI"],
            text=True,
        ).strip()
    except Exception:
        return None


def file_mtime_iso(path: Path) -> str | None:
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        return None


def commits_by_day(days: int = 30) -> list[tuple[str, int]]:
    """Return [(YYYY-MM-DD, count)] for the last `days` days, oldest first."""
    from collections import Counter
    from datetime import timedelta
    try:
        out = subprocess.check_output(
            ["git", "-C", str(ROOT), "log", f"--since={days} days ago", "--pretty=format:%cs"],
            text=True,
        )
        c = Counter(line for line in out.strip().split("\n") if line)
    except Exception:
        c = {}
    today = datetime.now().date()
    series = []
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        series.append((d, c.get(d, 0)))
    return series


def parse_money(s: str) -> float:
    """Extract a dollar number from strings like '$69.88' or '~$30–50' (uses lower bound)."""
    m = re.search(r"\$?\s*~?\$?(\d+(?:\.\d+)?)", s.replace(",", ""))
    return float(m.group(1)) if m else 0.0


def read_agreements() -> dict:
    """Return parsed registry.json or empty stub."""
    try:
        return json.loads(AGREEMENTS_REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        return {"count": 0, "agreements": []}


def count_intent_docs() -> int:
    """Count canonical INTENT docs (excludes README)."""
    if not INTENT_DIR.exists():
        return 0
    return sum(
        1 for p in INTENT_DIR.iterdir()
        if p.is_file() and p.suffix == ".md" and p.name != "README.md"
    )


def count_proofs() -> int:
    proofs = INTENT_DIR / "AGREEMENTS" / "proofs"
    if not proofs.exists():
        return 0
    return sum(
        1 for p in proofs.iterdir()
        if p.is_file() and p.suffix == ".md" and not p.name.startswith(".")
    )


def count_champions() -> tuple[int, int]:
    """Return (total_champions, public_champions) by scanning AGREEMENTS/champions/."""
    return (len(read_champions()), sum(1 for c in read_champions() if c.get("public")))


def read_champions() -> list[dict]:
    """Return list of champion dicts parsed from AGREEMENTS/champions/*.md front-matter."""
    champ_dir = INTENT_DIR / "AGREEMENTS" / "champions"
    if not champ_dir.exists():
        return []
    out = []
    for p in sorted(champ_dir.iterdir()):
        if not (p.is_file() and p.suffix == ".md" and not p.name.startswith(".")):
            continue
        try:
            text = p.read_text(encoding="utf-8")
            fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
            if not fm:
                continue
            data: dict = {}
            for line in fm.group(1).split("\n"):
                m = re.match(r"^([a-z_]+):\s*(.*)$", line)
                if m:
                    key, val = m.group(1), m.group(2).strip().strip('"')
                    if val.lower() == "true":
                        val = True
                    elif val.lower() == "false":
                        val = False
                    data[key] = val
            data["_path"] = str(p)
            out.append(data)
        except Exception:
            pass
    return out


def read_proofs() -> list[dict]:
    """Return list of proof loop dicts parsed from AGREEMENTS/proofs/*.md front-matter."""
    proof_dir = INTENT_DIR / "AGREEMENTS" / "proofs"
    if not proof_dir.exists():
        return []
    out = []
    for p in sorted(proof_dir.iterdir()):
        if not (p.is_file() and p.suffix == ".md" and not p.name.startswith(".")):
            continue
        try:
            text = p.read_text(encoding="utf-8")
            fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
            if not fm:
                continue
            data: dict = {}
            for line in fm.group(1).split("\n"):
                m = re.match(r"^([a-z_]+):\s*(.*)$", line)
                if m:
                    key, val = m.group(1), m.group(2).strip().strip('"')
                    if val.lower() == "true":
                        val = True
                    elif val.lower() == "false":
                        val = False
                    data[key] = val
            data["_path"] = str(p)
            out.append(data)
        except Exception:
            pass
    return out


def render_champions_list(champions: list[dict]) -> str:
    """Render the Champions Roll as a list of public champions."""
    public = [c for c in champions if c.get("public")]
    if not public:
        return "<p class='muted'>No public signatures yet. <strong>The first signature is yours.</strong> Sign above.</p>"
    rows = []
    for c in public:
        num = c.get("champion_number", "")
        name = c.get("name", "[unnamed]")
        date = c.get("date_signed", "")
        role = c.get("role", "")
        handle = c.get("handle", "")
        rows.append(
            f"<div class='champion-row'>"
            f"<div class='champion-num'>#{escape(str(num))}</div>"
            f"<div class='champion-info'>"
            f"<div class='champion-name'>{escape(str(name))}</div>"
            f"{('<div class=\"champion-role\">' + escape(str(role)) + '</div>') if role else ''}"
            f"</div>"
            f"<div class='champion-meta'>"
            f"{('<span>' + escape(str(handle)) + '</span>') if handle else ''}"
            f"<span class='champion-date'>{escape(str(date))}</span>"
            f"</div>"
            f"</div>"
        )
    return f"<div class='champions-list'>{''.join(rows)}</div>"


def render_proofs_list(proofs: list[dict]) -> str:
    """Render the Public Proofs roll."""
    public = [p for p in proofs if (p.get("consent") or "").lower() == "public"]
    if not public:
        return ""
    rows = []
    for p in public:
        loop_n = p.get("loop_number", "?")
        player = p.get("player", "[unnamed]")
        date = p.get("date_committed") or p.get("date_started", "")
        status = p.get("status", "")
        path = p.get("_path", "")
        rows.append(
            f"<div class='champion-row'>"
            f"<div class='champion-num'>L{escape(str(loop_n))}</div>"
            f"<div class='champion-info'>"
            f"<div class='champion-name'>{escape(str(player))}</div>"
            f"<div class='champion-role'>Loop {escape(str(loop_n))} &middot; {escape(str(status))}</div>"
            f"</div>"
            f"<div class='champion-meta'>"
            f"<span class='champion-date'>{escape(str(date))}</span>"
            f"</div>"
            f"</div>"
        )
    return f"<div class='champions-list'>{''.join(rows)}</div>"


def count_civ_quest_commits(days: int = 7) -> int:
    """Roughly: commits in last N days that touch core/INTENT/ — Civ-Quest milestones."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(ROOT), "log", f"--since={days} days ago", "--oneline", "--", "core/INTENT/"],
            text=True,
        )
        return sum(1 for line in out.strip().split("\n") if line)
    except Exception:
        return 0


def strip_front_matter(md: str) -> str:
    """Drop YAML front-matter block from the top of a markdown doc."""
    if md.startswith("---"):
        end = md.find("\n---", 3)
        if end != -1:
            return md[end + 4:].lstrip()
    return md


def md_to_html(md: str) -> str:
    """Tiny markdown → HTML converter. Handles headings, lists, bold, italic,
    inline code, code blocks, blockquotes, hr, paragraphs, links. Good enough
    for Agreement bodies; not a full CommonMark engine."""
    # Code blocks first (escape contents)
    code_blocks: list[str] = []

    def stash_code(m: re.Match) -> str:
        code_blocks.append(escape(m.group(1)))
        return f"@@CODEBLOCK_{len(code_blocks) - 1}@@"

    md = re.sub(r"```[a-zA-Z0-9]*\n(.*?)```", stash_code, md, flags=re.DOTALL)

    out: list[str] = []
    in_ul = False
    in_ol = False

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    def inline(s: str) -> str:
        # Don't escape — we trust agreement files. Keep markup intact.
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*(?!\*)([^*\n]+?)\*(?!\*)", r"<em>\1</em>", s)
        s = re.sub(r"`([^`\n]+?)`", r"<code>\1</code>", s)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<a class='link' href='\2' target='_blank'>\1</a>", s)
        return s

    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            out.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    for line in md.splitlines():
        stripped = line.rstrip()
        if not stripped:
            flush_paragraph()
            close_lists()
            continue
        if stripped == "---":
            flush_paragraph()
            close_lists()
            out.append("<hr/>")
            continue
        h = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if h:
            flush_paragraph()
            close_lists()
            level = len(h.group(1))
            out.append(f"<h{level}>{inline(h.group(2))}</h{level}>")
            continue
        ul = re.match(r"^[-*]\s+(.+)$", stripped)
        if ul:
            flush_paragraph()
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline(ul.group(1))}</li>")
            continue
        ol = re.match(r"^\d+\.\s+(.+)$", stripped)
        if ol:
            flush_paragraph()
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{inline(ol.group(1))}</li>")
            continue
        bq = re.match(r"^>\s*(.*)$", stripped)
        if bq:
            flush_paragraph()
            close_lists()
            out.append(f"<blockquote>{inline(bq.group(1))}</blockquote>")
            continue
        # Otherwise: paragraph text
        paragraph.append(stripped)

    flush_paragraph()
    close_lists()

    html = "\n".join(out)
    # Restore code blocks
    for i, code in enumerate(code_blocks):
        html = html.replace(f"@@CODEBLOCK_{i}@@", f"<pre><code>{code}</code></pre>")
    return html


def agreement_file_path(agreement_id: str) -> Path | None:
    """Resolve an agreement_id to its on-disk file path."""
    if not agreement_id:
        return None
    date_part, _, rest = agreement_id.partition("_")
    fname_body = rest.upper().replace("-", "_")
    return INTENT_DIR / "AGREEMENTS" / f"{date_part}_{fname_body}.md"


def extract_section(md: str, header: str) -> str:
    """Pull a markdown section by its `## Header` line until the next `## ` or `---`."""
    pattern = rf"## {re.escape(header)}.*?(?=^## |^---\s*$)"
    m = re.search(pattern, md, flags=re.MULTILINE | re.DOTALL)
    return m.group(0) if m else ""


def md_table_to_rows(md: str) -> list[list[str]]:
    """Parse first markdown table found in `md`. Returns list[row] including header."""
    rows = []
    in_table = False
    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            # skip separator rows like |---|---|
            if all(set(c) <= set("-: ") for c in cells):
                continue
            rows.append(cells)
            in_table = True
        elif in_table:
            break
    return rows


# ---- Section extractors ----------------------------------------------------

def extract_focus(md: str) -> str:
    m = re.search(
        r"## CURRENT FOCUS.*?(?=^## |^---\s*$)",
        md,
        flags=re.MULTILINE | re.DOTALL,
    )
    return m.group(0) if m else ""


def extract_open_decisions(md: str) -> list[str]:
    m = re.search(
        r"## OPEN DECISIONS.*?(?=^## |^---\s*$)",
        md,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not m:
        return []
    items = re.findall(r"^\d+\.\s+(.+)$", m.group(0), flags=re.MULTILINE)
    return items


def extract_live_now_table(md: str) -> list[list[str]]:
    m = re.search(
        r"## WHAT'S LIVE NOW.*?(?=^## |^---\s*$)",
        md,
        flags=re.MULTILINE | re.DOTALL,
    )
    return md_table_to_rows(m.group(0)) if m else []


def extract_money_table(md: str) -> list[list[str]]:
    m = re.search(
        r"### Outflow.*?(?=^### |^## |^---\s*$)",
        md,
        flags=re.MULTILINE | re.DOTALL,
    )
    return md_table_to_rows(m.group(0)) if m else []


def extract_inflow_table(md: str) -> list[list[str]]:
    m = re.search(
        r"### Inflow.*?(?=^### |^## |^---\s*$)",
        md,
        flags=re.MULTILINE | re.DOTALL,
    )
    return md_table_to_rows(m.group(0)) if m else []


def extract_30day_rubric(md: str) -> list[str]:
    m = re.search(
        r"## 30-DAY SUCCESS RUBRIC.*?(?=^## |^---\s*$)",
        md,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not m:
        return []
    return re.findall(r"^- \[[ x]\]\s+(.+)$", m.group(0), flags=re.MULTILINE)


def extract_drift_lines(md: str) -> list[str]:
    """Pull '- **xxx drift**' style callouts from each view."""
    drift = []
    for tag in ("Money drift", "Attention drift", "Drift:"):
        for line in md.splitlines():
            if tag.lower() in line.lower() and not line.startswith("##"):
                clean = line.strip("-* ").strip()
                if clean:
                    drift.append(clean)
    return drift


def extract_drift_bullets(md: str) -> list[str]:
    """Bullets immediately after '### Money drift' or '### Attention drift'."""
    bullets = []
    for header in ("### Money drift / blind spots", "### Attention drift / blind spots"):
        m = re.search(
            rf"{re.escape(header)}.*?(?=^### |^## |^---\s*$)",
            md,
            flags=re.MULTILINE | re.DOTALL,
        )
        if m:
            for line in m.group(0).splitlines():
                if line.startswith("- "):
                    bullets.append(line[2:].strip())
    return bullets


# ---- HTML rendering --------------------------------------------------------

CSS = """
:root {
  /* Foundation — midnight navy (like the posters) */
  --bg: #0a1428;
  --bg-deep: #060d1c;
  --surface: #14213d;
  --surface-2: #1d2c4d;
  --border: #2c3d63;

  /* Text — warm cream/parchment */
  --text: #f5ead8;
  --text-bright: #fff7e8;
  --muted: #8fa1c2;

  /* Primary accent — warm gold */
  --accent: #e8b974;
  --accent-bright: #f5d089;
  --accent-soft: rgba(232, 185, 116, 0.12);
  --accent-glow: rgba(232, 185, 116, 0.35);

  /* Layer / status palette — earth + sky harmony */
  --p1: #e57b7b;          /* coral — Healing */
  --p2: #7cc4a8;          /* sage — Regeneration */
  --infra: #7cb8e0;       /* sky — Intelligence */
  --cruft: #5a6680;       /* slate — withdrawn */
  --unknown: #b89cd5;     /* lavender — Service */
  --good: #84d488;        /* sage-bright — alive */
  --warn: #e8c479;        /* amber — caution */
  --bad: #e58787;         /* soft coral — alert */
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
  background:
    radial-gradient(ellipse 1200px 600px at 50% -100px, rgba(232, 185, 116, 0.06), transparent 70%),
    radial-gradient(ellipse 800px 400px at 100% 0%, rgba(124, 196, 168, 0.04), transparent 60%),
    radial-gradient(ellipse 600px 600px at 0% 100%, rgba(184, 156, 213, 0.04), transparent 60%),
    var(--bg);
  color: var(--text);
  line-height: 1.55;
  font-size: 14px;
  position: relative;
  overflow-x: hidden;
  min-height: 100vh;
}

/* Mobile sticky stage bar */
.mobile-stage-bar {
  position: fixed;
  top: 3px;
  left: 0;
  right: 0;
  background: var(--surface);
  border-bottom: 1px solid var(--accent);
  padding: 6px 14px;
  font-size: 11px;
  z-index: 999;
  display: none;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.4);
}
.mobile-stage-bar .msb-stage { color: var(--accent-bright); font-weight: 700; }
.mobile-stage-bar .msb-score { color: var(--accent); }
.mobile-stage-bar .msb-next { color: var(--muted); font-size: 10px; flex: 1; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 700px) {
  .mobile-stage-bar.show { display: flex; }
  body.has-mobile-bar .wrap { padding-top: 36px; }
}

/* Scroll progress bar */
.scroll-progress {
  position: fixed;
  top: 0;
  left: 0;
  height: 3px;
  width: 0;
  background: linear-gradient(90deg, var(--accent), var(--good));
  z-index: 1000;
  transition: width 0.1s ease-out;
  box-shadow: 0 0 8px rgba(232, 185, 116, 0.5);
}

/* Starfield background */
.starfield {
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  opacity: 0.6;
}
.star {
  fill: var(--accent-bright);
  animation: twinkle 5s ease-in-out infinite;
}

/* Horizon glow at the very top — sunrise feel */
.horizon-glow {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 200px;
  background: radial-gradient(ellipse 800px 200px at 50% 0%, rgba(232, 185, 116, 0.10), transparent 70%);
  pointer-events: none;
  z-index: -1;
}
@keyframes twinkle {
  0%, 100% { opacity: 0.15; }
  50% { opacity: 0.5; }
}

/* Universal hover lift on cards */
.card,
.queue,
.onboarding-card,
.sign-card,
.champions-card,
.invite-card,
.scoreboard,
.player-scoreboard,
.metrics-glossary,
.steward-queue,
.funnel-card,
.founder-profile,
.player-hero,
.field-hero,
.next-move,
.treasury-card,
.framing,
.eco-layer,
.metric-card,
.glossary-item,
.wpap-mod,
.wpap-phase,
.proof-loop-card,
.steward-item,
.champion-row,
.inline-doc,
.agreement {
  transition: transform 0.18s ease-out, box-shadow 0.18s ease-out, border-color 0.18s ease-out;
}
.card:hover,
.queue:hover,
.onboarding-card:hover,
.sign-card:hover,
.champions-card:hover,
.invite-card:hover,
.scoreboard:hover,
.player-scoreboard:hover,
.metrics-glossary:hover,
.steward-queue:hover,
.funnel-card:hover,
.next-move:hover,
.treasury-card:hover,
.framing:hover,
.metric-card:hover,
.glossary-item:hover,
.wpap-mod:hover,
.wpap-phase:hover,
.proof-loop-card:hover,
.steward-item:hover,
.champion-row:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(232, 185, 116, 0.15);
}

/* Step completion celebration */
@keyframes burst {
  0% { transform: scale(1); }
  40% { transform: scale(1.15); filter: drop-shadow(0 0 8px var(--good)); }
  100% { transform: scale(1); }
}
.onboard-step.celebrating .step-num {
  animation: burst 0.6s ease-out;
  background: var(--good);
  color: #062013;
  border-color: var(--good);
}

/* Champion-row glow when first added */
@keyframes glowIn {
  0% { box-shadow: 0 0 0 rgba(132, 212, 136, 0); }
  50% { box-shadow: 0 0 24px rgba(132, 212, 136, 0.6); }
  100% { box-shadow: 0 0 0 rgba(132, 212, 136, 0); }
}
.champion-row:first-child {
  animation: glowIn 2.5s ease-out 0.5s;
}

/* Page entrance fade-up */
.wrap > * {
  animation: fadeUp 0.5s ease-out backwards;
}
.wrap > *:nth-child(1) { animation-delay: 0s; }
.wrap > *:nth-child(2) { animation-delay: 0.05s; }
.wrap > *:nth-child(3) { animation-delay: 0.1s; }
.wrap > *:nth-child(4) { animation-delay: 0.15s; }
.wrap > *:nth-child(5) { animation-delay: 0.2s; }
.wrap > *:nth-child(n+6) { animation-delay: 0.25s; }
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Welcome modal */
.welcome-modal {
  position: fixed;
  inset: 0;
  background: rgba(14, 17, 22, 0.94);
  backdrop-filter: blur(8px);
  display: none;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  padding: 24px;
  animation: welcomeFade 0.4s ease-out;
}
.welcome-modal.show { display: flex; }
@keyframes welcomeFade {
  from { opacity: 0; }
  to { opacity: 1; }
}
.welcome-card {
  background: linear-gradient(135deg, rgba(232, 185, 116,0.12), rgba(132, 212, 136,0.06));
  border: 1px solid var(--accent);
  border-radius: 16px;
  padding: 36px 32px;
  max-width: 520px;
  text-align: center;
  box-shadow: 0 24px 80px rgba(0,0,0,0.6), 0 0 60px rgba(232, 185, 116,0.15);
  animation: welcomeRise 0.5s ease-out;
}
@keyframes welcomeRise {
  from { opacity: 0; transform: translateY(20px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.welcome-icon { font-size: 48px; margin-bottom: 12px; }
.welcome-card button { font-family: inherit; cursor: pointer; border: none; }

/* Sticky TOC */
.toc-nav {
  position: fixed;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 500;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  pointer-events: none;
}
.toc-toggle {
  pointer-events: auto;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--accent);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  font-size: 16px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.15s;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.toc-toggle:hover { background: var(--accent); color: #1a0e02; transform: scale(1.05); }
.toc-list {
  pointer-events: auto;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 4px;
  display: none;
  flex-direction: column;
  gap: 2px;
  min-width: 200px;
  max-height: 70vh;
  overflow-y: auto;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}
.toc-nav.open .toc-list { display: flex; }
.toc-link {
  background: transparent;
  border: none;
  text-align: left;
  color: var(--muted);
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.1s;
  border-left: 2px solid transparent;
}
.toc-link:hover { background: var(--surface-2); color: var(--text); }
.toc-link.active { color: var(--accent); border-left-color: var(--accent); background: rgba(232, 185, 116,0.06); }

@media (max-width: 700px) {
  .toc-nav { right: 8px; }
  .toc-list { max-width: calc(100vw - 80px); font-size: 11px; }
  .header-row { flex-direction: column; gap: 12px; }
  .mode-toggle { width: 100%; }
  .mode-btn { flex: 1; padding: 8px 6px; font-size: 12px; }
  .wrap { padding: 12px; }
  h1 { font-size: 20px; }
  .player-hero { padding: 20px; }
  .next-move { flex-direction: column; align-items: stretch; gap: 12px; padding: 12px 16px; }
  .nm-cta { text-align: center; }
  .funnel-step { width: 100%; }
}

/* Greeting badge */
.greeting {
  display: inline-block;
  background: rgba(232, 185, 116, 0.12);
  color: var(--accent);
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  margin-left: 8px;
  letter-spacing: 0.3px;
}
.greeting::before {
  content: "✨ ";
}
.wrap { max-width: 1400px; margin: 0 auto; padding: 24px; position: relative; z-index: 1; }
h1 {
  font-family: "Cormorant Garamond", "Iowan Old Style", Georgia, serif;
  font-size: 36px;
  margin: 0 0 4px;
  font-weight: 600;
  letter-spacing: -0.5px;
  background: linear-gradient(135deg, var(--text-bright) 0%, var(--accent-bright) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
h2 { font-size: 18px; margin: 0 0 12px; color: var(--accent-bright); font-weight: 600; letter-spacing: -0.2px; }
h3 { font-size: 12px; margin: 16px 0 8px; color: var(--muted); text-transform: uppercase; letter-spacing: 1.2px; font-weight: 600; }
.subtitle { color: var(--muted); margin-bottom: 24px; }
.filter {
  background: linear-gradient(135deg, rgba(232, 185, 116, 0.08), rgba(124, 196, 168, 0.04));
  border: 1px solid var(--accent);
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 24px;
  font-style: italic;
  color: var(--accent-bright);
  box-shadow: 0 4px 16px rgba(232, 185, 116, 0.08);
}

/* Principle banner — "The Game Plays Itself" */
.principle-banner {
  display: grid;
  grid-template-columns: 60px 1fr;
  gap: 18px;
  align-items: center;
  background:
    radial-gradient(ellipse at top right, rgba(232, 185, 116, 0.10), transparent 60%),
    linear-gradient(135deg, rgba(184, 156, 213, 0.06), rgba(124, 196, 168, 0.04));
  border: 1px solid var(--accent);
  border-radius: 14px;
  padding: 18px 22px;
  margin-bottom: 24px;
  position: relative;
  overflow: hidden;
}
.principle-banner::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 90% 50%, rgba(232, 185, 116, 0.06), transparent 40%);
  pointer-events: none;
}
.pb-glyph {
  font-size: 44px;
  text-align: center;
  line-height: 1;
  filter: drop-shadow(0 0 12px rgba(232, 185, 116, 0.4));
  animation: spin-slow 60s linear infinite;
}
@keyframes spin-slow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.pb-label { font-size: 10px; color: var(--accent); letter-spacing: 1.8px; font-weight: 700; }
.pb-quote {
  font-family: "Cormorant Garamond", "Iowan Old Style", Georgia, serif;
  font-size: 22px;
  color: var(--text-bright);
  font-style: italic;
  margin-top: 6px;
  line-height: 1.4;
  font-weight: 500;
  letter-spacing: -0.2px;
}
.pb-test { font-size: 12px; color: var(--muted); margin-top: 8px; line-height: 1.6; }
.pb-test strong { color: var(--accent-bright); font-weight: 600; }
.pb-link { font-size: 11px; color: var(--accent); display: inline-block; margin-top: 6px; text-decoration: none; }
.pb-link:hover { color: var(--accent-bright); text-decoration: underline; }
@media (max-width: 700px) { .principle-banner { grid-template-columns: 1fr; text-align: center; } .pb-glyph { margin: 0 auto; } }

/* Signaling banner */
.signaling-banner {
  display: grid;
  grid-template-columns: 60px 1fr;
  gap: 18px;
  align-items: center;
  background:
    radial-gradient(ellipse at top left, rgba(124, 184, 224, 0.08), transparent 60%),
    linear-gradient(135deg, rgba(124, 196, 168, 0.04), rgba(232, 185, 116, 0.04));
  border: 1px solid var(--p2);
  border-radius: 14px;
  padding: 18px 22px;
  margin-bottom: 24px;
  position: relative;
  overflow: hidden;
}
.signaling-banner::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 10% 50%, rgba(124, 184, 224, 0.06), transparent 40%);
  pointer-events: none;
}
@keyframes pulse-glow {
  0%, 100% { filter: drop-shadow(0 0 8px rgba(124, 184, 224, 0.2)); }
  50% { filter: drop-shadow(0 0 16px rgba(124, 184, 224, 0.5)); }
}
.sb-glyph {
  font-size: 44px;
  text-align: center;
  line-height: 1;
  animation: pulse-glow 3s ease-in-out infinite;
}
.sb-label { font-size: 10px; color: var(--p2); letter-spacing: 1.8px; font-weight: 700; }
.sb-quote {
  font-family: "Cormorant Garamond", "Iowan Old Style", Georgia, serif;
  font-size: 22px;
  color: var(--text-bright);
  font-style: italic;
  margin-top: 6px;
  line-height: 1.4;
  font-weight: 500;
  letter-spacing: -0.2px;
}
.sb-test { font-size: 12px; color: var(--muted); margin-top: 8px; line-height: 1.6; }
.sb-test strong { color: var(--p2); font-weight: 600; }
@media (max-width: 700px) { .signaling-banner { grid-template-columns: 1fr; text-align: center; } .sb-glyph { margin: 0 auto; } }

/* Field Pulse */
.field-pulse {
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--p2);
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 24px;
}
.fp-header { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.fp-label {
  font-size: 11px;
  letter-spacing: 1.5px;
  color: var(--p2);
  font-weight: 700;
}
.fp-label::before {
  content: "";
  display: inline-block;
  width: 8px;
  height: 8px;
  background: var(--good);
  border-radius: 50%;
  margin-right: 6px;
  animation: pulse-dot 2s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.2); }
}
.fp-sub { font-size: 11px; color: var(--muted); }
.fp-feed { display: flex; flex-direction: column; gap: 4px; max-height: 200px; overflow-y: auto; }
.fp-event {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 10px;
  padding: 6px 10px;
  background: var(--surface-2);
  border-radius: 4px;
  font-size: 12px;
  align-items: center;
  animation: fpSlideIn 0.4s ease-out;
}
@keyframes fpSlideIn {
  from { opacity: 0; transform: translateX(-8px); }
  to { opacity: 1; transform: translateX(0); }
}
.fp-icon { font-size: 14px; }
.fp-msg { color: var(--text); }
.fp-time { color: var(--muted); font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 10px; }
.fp-empty { color: var(--muted); font-size: 12px; font-style: italic; padding: 6px 10px; }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
@media (max-width: 1100px) { .grid { grid-template-columns: 1fr; } }
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}
.card.full { grid-column: 1 / -1; }
.kpi { font-size: 28px; font-weight: 700; color: var(--accent); }
.kpi-label { color: var(--muted); font-size: 12px; text-transform: uppercase; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); vertical-align: top; }
th { color: var(--muted); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.badge.P1 { background: var(--p1); color: #1a0606; }
.badge.P2 { background: var(--p2); color: #052622; }
.badge.infra { background: var(--infra); color: #0a1d28; }
.badge.cruft { background: var(--cruft); color: #d6dde6; }
.badge.unknown { background: var(--unknown); color: #200d36; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
.dot.live { background: var(--good); }
.dot.warn { background: var(--warn); }
.dot.bad { background: var(--bad); }
.live-status {
  background: var(--muted);
  transition: background 0.3s;
}
.live-table td:first-child { width: 16px; padding-right: 0; }
ul { padding-left: 20px; margin: 8px 0; }
li { margin-bottom: 4px; }
details { margin: 8px 0; }
details summary {
  cursor: pointer;
  padding: 6px 8px;
  background: var(--surface-2);
  border-radius: 4px;
  user-select: none;
  font-weight: 600;
}
details summary:hover { background: var(--border); }
details[open] summary { margin-bottom: 8px; }
.svc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 4px 12px;
  margin: 8px 0 0 8px;
  font-size: 13px;
}
.svc { color: var(--text); text-decoration: none; padding: 2px 0; }
.svc:hover { color: var(--accent); text-decoration: underline; }
.svc.untagged { color: var(--unknown); }
.drift {
  background: rgba(248, 113, 113, 0.08);
  border-left: 3px solid var(--bad);
  padding: 12px 16px;
  border-radius: 4px;
  margin-bottom: 12px;
}
.drift strong { color: var(--bad); }
.commits { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 12px; }
.commits .sha { color: var(--accent); margin-right: 8px; }
footer { color: var(--muted); font-size: 12px; margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--border); }
.search {
  width: 100%;
  padding: 8px 12px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
  font-size: 13px;
  margin-bottom: 8px;
}
.search:focus { outline: none; border-color: var(--accent); }
.toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.tag-pill {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--muted);
  cursor: pointer;
  user-select: none;
}
.tag-pill.active { background: var(--accent); color: #1a0e02; border-color: var(--accent); }
a.link { color: var(--accent); text-decoration: none; }
a.link:hover { text-decoration: underline; }
.queue {
  background: linear-gradient(135deg, rgba(232, 185, 116,0.06), rgba(232, 185, 116,0.02));
  border: 1px solid var(--accent);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
}
.queue h2 { margin-top: 0; }
.queue-row { display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 12px; }
.queue-stat { flex: 1 1 140px; }
.queue-stat .n { font-size: 32px; font-weight: 700; color: var(--accent); line-height: 1; }
.queue-stat .lbl { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }
.queue ol { margin: 0; padding-left: 20px; }
.untagged-callout {
  background: rgba(184, 156, 213, 0.08);
  border-left: 3px solid var(--unknown);
  padding: 12px 16px;
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 13px;
}
.untagged-callout strong { color: var(--unknown); }
.freshness {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  margin: 8px 0 24px;
}
.fresh-row { display: flex; gap: 24px; flex-wrap: wrap; }
.fresh-stat { display: flex; flex-direction: column; min-width: 140px; }
.fresh-lbl { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }
.fresh-val { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 13px; color: var(--text); margin-top: 2px; }
.fresh-rel { font-size: 11px; color: var(--accent); margin-top: 2px; }
#autoStatus.on { color: var(--good); }
#autoStatus.stale { color: var(--bad); }

/* Money breakdown bar */
.money-bar { margin-bottom: 16px; }
.bar-track {
  display: flex;
  height: 28px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--border);
}
.bar-seg { transition: filter 0.15s; }
.bar-seg:hover { filter: brightness(1.2); }
.bar-total { font-size: 13px; color: var(--muted); margin-top: 8px; }
.bar-total strong { color: var(--accent); font-size: 18px; }
.bar-legend { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px; font-size: 12px; }
.leg-item { display: inline-flex; align-items: center; gap: 6px; }
.leg-sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; }
.leg-pct { color: var(--muted); margin-left: 4px; }

/* Tag donut layout */
.donut-row { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }
.donut-legend { display: flex; flex-direction: column; gap: 4px; font-size: 12px; }
.donut-legend .leg-item { gap: 8px; }
.donut-legend .leg-pct { color: var(--text); font-weight: 600; }

/* Sparkline */
.sparkline-card { margin-top: 8px; }
.sparkline-meta { display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); margin-bottom: 4px; }

/* Mission row */
.mission-row { display: flex; gap: 24px; flex-wrap: wrap; }
.mission-block { flex: 1 1 240px; }

.mission-poster-row {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 24px;
  align-items: start;
}
@media (max-width: 800px) {
  .mission-poster-row { grid-template-columns: 1fr; }
}
.mission-poster {
  display: block;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border);
  transition: transform 0.15s, box-shadow 0.15s;
  background: #000;
}
.mission-poster:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(232, 185, 116, 0.15);
  border-color: var(--accent);
}
.mission-poster img {
  display: block;
  width: 100%;
  height: auto;
}
.mission-content { min-width: 0; }
.christ-row { display: flex; flex-wrap: wrap; gap: 6px; }
.christ-pill {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 11px;
  color: var(--text);
}
.christ-pill strong {
  color: var(--accent);
  margin-right: 2px;
  font-size: 13px;
}

/* Agreement expandable cards */
.agreement {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 8px;
  overflow: hidden;
}
.agreement[open] { border-color: var(--accent); }
.agreement-summary {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  list-style: none;
}
.agreement-summary::-webkit-details-marker { display: none; }
.agreement-summary:hover { background: rgba(232, 185, 116, 0.04); }
.ag-date { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 12px; color: var(--muted); min-width: 88px; }
.ag-parties { font-weight: 600; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ag-status { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
.ag-expand { font-size: 11px; color: var(--accent); margin-left: auto; }
.agreement[open] .ag-expand { color: var(--muted); }
.agreement-meta { padding: 0 16px 8px 40px; border-bottom: 1px solid var(--border); }
.agreement-body {
  padding: 16px 16px 16px 40px;
  font-size: 13px;
  line-height: 1.6;
}

/* Embedded markdown styling */
.markdown-body h1, .markdown-body h2, .markdown-body h3 { color: var(--accent); margin-top: 16px; margin-bottom: 8px; }
.markdown-body h1 { font-size: 18px; }
.markdown-body h2 { font-size: 15px; }
.markdown-body h3 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); }
.markdown-body p { margin: 8px 0; }
.markdown-body ul, .markdown-body ol { margin: 8px 0; padding-left: 24px; }
.markdown-body li { margin-bottom: 4px; }
.markdown-body strong { color: var(--text); font-weight: 700; }
.markdown-body em { color: var(--accent); font-style: italic; }
.markdown-body code { background: var(--bg); padding: 1px 5px; border-radius: 3px; font-size: 12px; }
.markdown-body pre { background: var(--bg); padding: 10px; border-radius: 4px; overflow-x: auto; }
.markdown-body pre code { background: none; padding: 0; }
.markdown-body blockquote { border-left: 3px solid var(--accent); padding: 6px 12px; margin: 12px 0; color: var(--muted); font-style: italic; background: rgba(232, 185, 116,0.04); }
.markdown-body hr { border: none; border-top: 1px solid var(--border); margin: 16px 0; }
.markdown-body a.link { word-break: break-word; }

/* Ecosystem layered cards */
.eco-tagline {
  text-align: center;
  font-size: 12px;
  color: var(--accent);
  letter-spacing: 2px;
  margin: 16px 0 4px;
  text-transform: uppercase;
}
.eco-poster-row {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 24px;
  margin: 8px 0 16px;
  align-items: start;
}
@media (max-width: 900px) { .eco-poster-row { grid-template-columns: 1fr; } }
.three-framings { display: flex; flex-direction: column; gap: 10px; }
.framing {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 6px;
  padding: 10px 14px;
}
.framing p, .framing ul { margin: 4px 0 0; font-size: 12px; line-height: 1.5; color: var(--text); }
.framing ul { padding-left: 18px; }
.framing li { margin-bottom: 2px; }

.ecosystem { display: flex; flex-direction: column; gap: 6px; margin: 4px 0 8px; }
.eco-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; }
@media (max-width: 900px) { .eco-row { grid-template-columns: 1fr; } }
.eco-layer {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
}
details.eco-layer { display: block; }
details.eco-layer > summary {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  cursor: pointer;
  list-style: none;
  user-select: none;
}
details.eco-layer > summary::-webkit-details-marker { display: none; }
details.eco-layer[open] {
  background: var(--surface);
}
.eco-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--surface);
  border: 1px solid var(--border);
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 12px;
  font-weight: 700;
  color: var(--accent);
  flex-shrink: 0;
  margin-top: 2px;
}
.eco-icon { font-size: 22px; flex-shrink: 0; line-height: 1; margin-top: 2px; }
.eco-title-block { flex: 1; min-width: 0; }
.eco-title { font-weight: 700; font-size: 14px; color: var(--text); }
.eco-subtitle { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
.eco-tag { font-size: 12px; color: var(--text); margin-top: 4px; font-style: italic; opacity: 0.92; }
.eco-tag em { color: var(--accent); font-style: normal; }
.eco-components {
  list-style: none;
  padding: 8px 0 0 36px;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 4px;
  font-size: 12px;
}
.eco-components li {
  padding: 3px 8px;
  background: var(--bg);
  border-radius: 3px;
  color: var(--muted);
}
.eco-components li strong { color: var(--accent); }

/* Color accents per layer */
.eco-philosophy { border-left: 3px solid var(--accent); }
.eco-org { border-left: 3px solid #4ecdc4; }
.eco-agreement { border-left: 3px solid var(--good); }
.eco-party { border-left: 3px solid #b58be0; }
.eco-weekend { border-left: 3px solid #a3e635; }
.eco-ai { border-left: 3px solid #7ec8e3; }
.eco-village { border-left: 3px solid var(--good); }
.eco-media { border-left: 3px solid #b58be0; }
.eco-econ { border-left: 3px solid var(--accent); }
.eco-vision { border-left: 3px solid var(--accent); background: linear-gradient(135deg, rgba(232, 185, 116,0.10), transparent); padding: 14px 16px; }

/* WPAP section */
.wpap-tldr {
  background: rgba(124, 184, 224, 0.06);
  border-left: 3px solid #7ec8e3;
  padding: 12px 16px;
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--text);
  line-height: 1.7;
  font-style: italic;
}
.wpap-modules {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px;
  margin-bottom: 4px;
}
.wpap-mod {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  border-left: 3px solid #7ec8e3;
}
.wpap-icon { font-size: 18px; flex-shrink: 0; line-height: 1.2; }
.wpap-name { font-weight: 700; font-size: 13px; color: var(--text); }
.wpap-fn { font-size: 11px; color: var(--muted); margin-top: 2px; }

.wpap-phases {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px;
}
.wpap-phase {
  padding: 12px 14px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  border-top: 3px solid var(--border);
}
.wpap-phase-current {
  border-top-color: var(--good);
  background: linear-gradient(180deg, rgba(132, 212, 136,0.06), var(--surface-2));
}
.wpap-phase-num {
  font-size: 10px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}
.wpap-phase-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  margin-top: 4px;
}
.wpap-phase-tag {
  font-size: 11px;
  color: var(--muted);
  margin-top: 4px;
  line-height: 1.4;
}
.wpap-phase-status {
  font-size: 11px;
  color: var(--accent);
  margin-top: 8px;
  font-weight: 600;
}
.wpap-phase-current .wpap-phase-status { color: var(--good); }

/* Treasury & Game */
.treasury-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 8px 0 16px;
}
@media (max-width: 900px) { .treasury-row { grid-template-columns: 1fr; } }
.treasury-card {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 8px;
  padding: 16px;
}
.t-icon { font-size: 28px; line-height: 1; margin-bottom: 8px; }
.t-title { font-weight: 700; font-size: 16px; color: var(--text); }
.t-version { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
.t-tag { font-style: italic; color: var(--accent); margin: 12px 0; font-size: 13px; }
.t-points { padding-left: 20px; margin: 8px 0 0; font-size: 12px; line-height: 1.6; }
.t-points li { margin-bottom: 4px; }
.t-points strong { color: var(--text); }

.proof-loop-card {
  background: linear-gradient(135deg, rgba(132, 212, 136,0.08), rgba(232, 185, 116,0.04));
  border: 1px solid var(--good);
  border-radius: 8px;
  padding: 18px 20px;
  margin: 8px 0 16px;
}
.proof-loop-header { display: flex; align-items: center; gap: 14px; margin-bottom: 8px; }
.proof-loop-header .t-icon { font-size: 32px; margin-bottom: 0; }
.proof-7day {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 6px;
  margin-top: 8px;
}
.proof-day {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.proof-day-num {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 10px;
  color: var(--accent);
  font-weight: 700;
  text-transform: uppercase;
}

/* Mode toggle */
.header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.header-sub { color: var(--muted); font-size: 13px; margin-top: 2px; }
.mode-toggle {
  display: inline-flex;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 4px;
  gap: 2px;
}
.mode-btn {
  background: transparent;
  border: none;
  color: var(--muted);
  font-size: 13px;
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.15s;
  font-family: inherit;
}
.mode-btn:hover { background: var(--surface-2); color: var(--text); }
.mode-btn.active {
  background: linear-gradient(135deg, var(--accent), var(--accent-bright));
  color: #1c1305;
  box-shadow: 0 2px 8px rgba(232, 185, 116, 0.3);
}

body.mode-founder .player-only,
body.mode-founder .field-only { display: none !important; }
body.mode-player .founder-only,
body.mode-player .field-only { display: none !important; }
body.mode-field .founder-only,
body.mode-field .player-only { display: none !important; }

/* Founder profile */
.founder-profile {
  background: linear-gradient(135deg, rgba(232, 185, 116,0.08), rgba(124, 196, 168,0.04));
  border: 1px solid var(--accent);
  border-radius: 10px;
  padding: 20px 24px;
  margin-bottom: 24px;
}
.profile-row { display: grid; grid-template-columns: auto 1fr auto; gap: 20px; align-items: center; }
@media (max-width: 800px) { .profile-row { grid-template-columns: 1fr; } }
.profile-avatar {
  font-size: 56px;
  width: 80px;
  height: 80px;
  background: var(--surface);
  border: 2px solid var(--accent);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.profile-role { font-size: 11px; color: var(--accent); letter-spacing: 1.5px; font-weight: 700; }
.profile-name { font-size: 24px; font-weight: 700; color: var(--text); margin: 4px 0; }
.profile-quest { font-size: 14px; color: var(--text); }
.profile-rule { font-size: 12px; color: var(--muted); margin-top: 6px; font-style: italic; }
.profile-rule em { color: var(--accent); }
.profile-stats { display: flex; gap: 24px; }
.profile-stat { text-align: center; min-width: 80px; }
.profile-stat-n { font-size: 28px; font-weight: 700; color: var(--accent); line-height: 1; }
.profile-stat-lbl { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }
.profile-roles { margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border); display: flex; flex-direction: column; gap: 6px; }
.role-item { font-size: 12px; color: var(--text); line-height: 1.5; }
.role-item strong { color: var(--accent); }

/* Steward queue */
.steward-queue {
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 24px;
}
.steward-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 8px;
}
.steward-item {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px 14px;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  align-items: start;
}
.steward-item.steward-pending { border-left: 3px solid var(--warn); }
.steward-icon { font-size: 18px; line-height: 1.2; }
.steward-action { font-weight: 700; font-size: 13px; color: var(--text); grid-column: 2; }
.steward-detail { font-size: 11px; color: var(--muted); line-height: 1.5; grid-column: 2; margin-top: 2px; }

/* Player hero */
.player-hero {
  background: linear-gradient(135deg, rgba(132, 212, 136,0.08), rgba(232, 185, 116,0.04));
  border: 1px solid var(--good);
  border-radius: 12px;
  padding: 32px 36px;
  margin-bottom: 24px;
  text-align: center;
}
.player-cta-row { display: flex; gap: 12px; justify-content: center; margin-top: 20px; flex-wrap: wrap; }
.player-cta-primary {
  background: linear-gradient(135deg, var(--good), var(--p2));
  color: #0a1f15;
  padding: 14px 24px;
  border-radius: 10px;
  text-decoration: none;
  font-weight: 700;
  font-size: 16px;
  transition: all 0.18s ease-out;
  box-shadow: 0 4px 16px rgba(132, 212, 136, 0.2);
  border: none;
  cursor: pointer;
  font-family: inherit;
}
.player-cta-primary:hover {
  background: linear-gradient(135deg, var(--accent-bright), var(--accent));
  color: #1c1305;
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(232, 185, 116, 0.3);
}
.player-cta-secondary {
  background: var(--surface-2);
  color: var(--text);
  padding: 14px 24px;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 600;
  font-size: 14px;
  border: 1px solid var(--border);
}
.player-cta-secondary:hover { border-color: var(--accent); color: var(--accent); }

/* Field hero */
.field-hero {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
}
.field-stats { display: flex; gap: 32px; margin-top: 16px; flex-wrap: wrap; }
.field-stat { text-align: center; min-width: 100px; }

/* Founder Scoreboard / Player Scoreboard */
.scoreboard, .player-scoreboard {
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 24px;
}
.player-scoreboard { border-left-color: var(--good); }
.metric-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
}
.metric-card {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px;
}
.metric-icon { font-size: 20px; line-height: 1; margin-bottom: 4px; }
.metric-n {
  font-size: 28px;
  font-weight: 700;
  color: var(--accent);
  line-height: 1;
}
.metric-frac { font-size: 14px; color: var(--muted); }
.metric-lbl { font-size: 11px; color: var(--text); margin-top: 4px; line-height: 1.3; }
.metric-sub { font-size: 10px; color: var(--muted); margin-top: 4px; }

/* Awareness Ladder */
.ladder {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.rung {
  background: var(--surface-2);
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 14px;
  font-size: 12px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.15s;
  font-weight: 600;
  flex: 1;
  min-width: 90px;
}
.rung:hover { border-color: var(--accent); color: var(--text); }
.rung.active {
  background: var(--accent);
  color: #1a0e02;
  border-color: var(--accent);
}
.rung.passed {
  background: rgba(232, 185, 116, 0.15);
  color: var(--accent);
  border-color: var(--accent);
}

/* 6 C's sliders */
.cs-meta { margin: 8px 0 12px; padding: 10px 14px; background: rgba(232, 185, 116, 0.06); border-left: 3px solid var(--accent); border-radius: 4px; }
.cs-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; }
@media (max-width: 700px) { .cs-row { grid-template-columns: 1fr; } }
.c-row {
  display: grid;
  grid-template-columns: 160px 1fr 32px;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  padding: 4px 0;
}
.cs-meta .c-row { grid-template-columns: 1fr 1fr 32px; }
.c-label { color: var(--text); }
.c-label .muted { color: var(--muted); font-size: 11px; font-weight: 400; }
.c-slider {
  appearance: none;
  -webkit-appearance: none;
  height: 4px;
  background: var(--border);
  border-radius: 2px;
  outline: none;
  width: 100%;
}
.c-slider::-webkit-slider-thumb {
  appearance: none;
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  background: var(--accent);
  border-radius: 50%;
  cursor: pointer;
}
.c-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  background: var(--accent);
  border-radius: 50%;
  cursor: pointer;
  border: none;
}
.c-value {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 12px;
  color: var(--accent);
  font-weight: 700;
  text-align: right;
}

/* Metrics glossary */
.metrics-glossary {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 24px;
}
.glossary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 10px;
}
.glossary-item {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 14px;
}
.glossary-term { font-weight: 700; color: var(--accent); font-size: 13px; margin-bottom: 4px; }
.glossary-def { font-size: 11px; color: var(--text); line-height: 1.5; }
.glossary-def code { font-size: 11px; }
.glossary-def strong { color: var(--accent); }

/* Identity prompt — for returning Champions who haven't logged in yet */
.identity-prompt {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 16px;
  align-items: center;
  background: linear-gradient(135deg, rgba(124, 184, 224, 0.08), rgba(184, 156, 213, 0.04));
  border: 1px dashed var(--infra);
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 16px;
}
.ip-icon { font-size: 28px; line-height: 1; }
.ip-label { font-size: 10px; color: var(--infra); letter-spacing: 1.2px; font-weight: 700; }
.ip-text { font-size: 12px; color: var(--muted); margin-top: 4px; }
.ip-row { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.ip-row input {
  flex: 1;
  min-width: 200px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px 12px;
  color: var(--text);
  font-size: 13px;
  font-family: inherit;
}
.ip-row input:focus { outline: none; border-color: var(--infra); }
.ip-row button { font-size: 13px; padding: 8px 16px; }
.ip-error { font-size: 11px; color: var(--bad); margin-top: 6px; }

/* Game State card — aggregate field metrics, top of page */
.game-state-card {
  background: linear-gradient(135deg, rgba(232, 185, 116, 0.06), rgba(124, 196, 168, 0.04));
  border: 1px solid var(--border);
  border-top: 3px solid var(--accent);
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 16px;
}
.gs-header { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.gs-label {
  font-size: 11px;
  letter-spacing: 1.5px;
  color: var(--accent-bright);
  font-weight: 700;
}
.gs-label::before {
  content: "";
  display: inline-block;
  width: 8px;
  height: 8px;
  background: var(--good);
  border-radius: 50%;
  margin-right: 8px;
  animation: pulse-dot-strong 1.6s ease-in-out infinite;
  box-shadow: 0 0 0 0 rgba(132, 212, 136, 0.7);
}
@keyframes pulse-dot-strong {
  0% { box-shadow: 0 0 0 0 rgba(132, 212, 136, 0.7); transform: scale(1); }
  50% { box-shadow: 0 0 0 8px rgba(132, 212, 136, 0); transform: scale(1.3); }
  100% { box-shadow: 0 0 0 0 rgba(132, 212, 136, 0); transform: scale(1); }
}
.gs-tagline { font-size: 12px; color: var(--muted); font-style: italic; }
.gs-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 6px;
}
.gs-metric {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 8px;
  text-align: center;
}
.gs-metric-accent { border-color: var(--accent); background: rgba(232,185,116,0.08); }
.gs-icon { font-size: 18px; line-height: 1; }
.gs-n {
  font-size: 22px;
  font-weight: 700;
  color: var(--accent);
  margin-top: 4px;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
}
.gs-metric-accent .gs-n { color: var(--accent-bright); font-size: 26px; }
.gs-metric { transition: all 0.3s ease-out; }
.gs-metric.changed {
  transform: scale(1.05);
  border-color: var(--good);
  box-shadow: 0 0 16px rgba(132, 212, 136, 0.3);
}
.gs-lbl { font-size: 10px; color: var(--muted); margin-top: 4px; line-height: 1.2; }

/* Progression Path bar */
.progression-bar {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
.pb-rail {
  position: relative;
  height: 4px;
  background: var(--surface-2);
  border-radius: 2px;
  margin: 0 22px 16px;
}
.pb-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--good), var(--accent), var(--accent-bright));
  border-radius: 2px;
  transition: width 0.6s ease-out;
}
.pb-stages {
  display: flex;
  justify-content: space-between;
  position: relative;
  margin-top: -28px;
}
.pb-stage {
  text-align: center;
  width: 44px;
  margin-top: 0;
}
.pbs-glyph {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  background: var(--surface);
  border: 2px solid var(--border);
  border-radius: 50%;
  margin: 0 auto;
  transition: all 0.18s;
  filter: grayscale(0.5);
  opacity: 0.5;
}
.pbs-name {
  font-size: 9px;
  color: var(--muted);
  margin-top: 4px;
  letter-spacing: 0.3px;
}
.pb-stage.passed .pbs-glyph {
  border-color: var(--good);
  background: rgba(132, 212, 136, 0.12);
  filter: grayscale(0);
  opacity: 0.85;
}
.pb-stage.current .pbs-glyph {
  border-color: var(--accent);
  background: rgba(232, 185, 116, 0.15);
  box-shadow: 0 0 16px rgba(232, 185, 116, 0.4);
  filter: grayscale(0);
  opacity: 1;
  transform: scale(1.15);
}
.pb-stage.current .pbs-name {
  color: var(--accent-bright);
  font-weight: 700;
}
.pb-unlock {
  margin-top: 12px;
  padding: 10px 14px;
  background: var(--surface-2);
  border-left: 3px solid var(--accent);
  border-radius: 4px;
  font-size: 12px;
  color: var(--text);
  line-height: 1.5;
}
.pb-unlock strong { color: var(--accent-bright); }

/* Player State panel */
.player-state {
  background: linear-gradient(135deg, rgba(132, 212, 136, 0.08), rgba(232, 185, 116, 0.04));
  border: 1px solid var(--good);
  border-radius: 12px;
  padding: 18px 22px;
  margin-bottom: 16px;
}
.ps-header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 16px;
  align-items: center;
  margin-bottom: 14px;
}
.ps-icon { font-size: 36px; line-height: 1; }
.ps-label { font-size: 10px; color: var(--good); letter-spacing: 1.5px; font-weight: 700; }
.ps-name { font-size: 22px; font-weight: 700; color: var(--text-bright); margin-top: 2px; }
.ps-stage {
  display: inline-block;
  margin-top: 6px;
  padding: 3px 10px;
  background: var(--surface);
  border: 1px solid var(--accent);
  border-radius: 999px;
  font-size: 11px;
  color: var(--accent-bright);
  font-weight: 600;
  letter-spacing: 0.3px;
}
.ps-score { text-align: right; }
.ps-score-n {
  font-size: 32px;
  font-weight: 700;
  color: var(--accent-bright);
  line-height: 1;
}
.ps-score-lbl { font-size: 10px; color: var(--muted); letter-spacing: 0.5px; text-transform: uppercase; }
.ps-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
  margin-bottom: 14px;
}
.ps-stat {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px;
  text-align: center;
}
.ps-stat-n {
  font-size: 22px;
  font-weight: 700;
  color: var(--accent);
  line-height: 1;
}
.ps-stat-lbl { font-size: 10px; color: var(--muted); margin-top: 4px; }
.ps-invite {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 6px;
  padding: 10px 14px;
  margin-bottom: 8px;
}
.ps-invite-label {
  font-size: 10px;
  color: var(--accent);
  letter-spacing: 1px;
  font-weight: 700;
  margin-bottom: 6px;
}
.ps-invite-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ps-invite-url {
  flex: 1;
  background: var(--bg);
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 11px;
  color: var(--text);
  overflow-x: auto;
  white-space: nowrap;
  display: inline-block;
}
.ps-tip { font-size: 11px; color: var(--muted); margin: 8px 0 0; line-height: 1.5; }
.ps-match-row { display: flex; align-items: center; gap: 10px; margin-top: 12px; flex-wrap: wrap; }
.ps-match-btn {
  background: var(--accent); color: var(--bg); border: none; border-radius: 6px;
  padding: 9px 16px; font-weight: 700; font-size: 13px; cursor: pointer;
}
.ps-match-btn:hover { filter: brightness(1.08); }
.ps-match-btn:disabled { opacity: 0.6; cursor: progress; }
.ps-match-hint { font-size: 10px; color: var(--muted); }
.ps-match-hint code { background: var(--surface-2); padding: 1px 5px; border-radius: 3px; font-size: 10px; }
.ps-match-result {
  background: var(--surface-2); border: 1px solid var(--accent); border-radius: 8px;
  padding: 12px 14px; margin-top: 10px; font-size: 13px; line-height: 1.6;
}
.ps-match-result-icon { font-size: 22px; line-height: 1; margin-right: 6px; vertical-align: middle; }
.ps-match-result-text { color: var(--text); }
.ps-match-result-cta {
  display: inline-block; margin-top: 8px; background: var(--accent); color: var(--bg);
  text-decoration: none; padding: 6px 12px; border-radius: 5px; font-size: 12px; font-weight: 700;
}
.ps-match-result-cta:hover { filter: brightness(1.08); }
.ps-contrib { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); }
.ps-contrib-label { font-size: 10px; color: var(--accent); letter-spacing: 1px; font-weight: 700; margin-bottom: 6px; }
.ps-contrib-row { display: flex; flex-wrap: wrap; gap: 6px; }
.ps-contrib-pill {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 11px;
  color: var(--muted);
}
.ps-contrib-pill strong { color: var(--accent); margin-right: 3px; }

/* Goal card (Loop 21) — founder's 30-day goal, public top-of-page */
.goal-card {
  background: linear-gradient(135deg, rgba(232,185,116,0.18) 0%, rgba(132,212,136,0.10) 100%);
  border: 2px solid var(--accent);
  border-radius: 14px;
  padding: 20px 24px;
  margin: 0 0 18px;
  box-shadow: 0 2px 18px rgba(232,185,116,0.10);
}
.goal-header { display: flex; align-items: center; gap: 14px; }
.goal-icon { font-size: 34px; line-height: 1; }
.goal-title-block { flex: 1; min-width: 0; }
.goal-label { font-size: 10px; color: var(--accent); letter-spacing: 1.6px; font-weight: 700; }
.goal-title { font-size: 19px; font-weight: 700; color: var(--text); margin-top: 3px; line-height: 1.3; }
.goal-progress { text-align: right; }
.goal-progress-n { font-size: 32px; font-weight: 800; color: var(--accent); line-height: 1; font-family: ui-monospace, "SF Mono", Menlo, monospace; }
.goal-progress-lbl { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; margin-top: 2px; }
.goal-blurb { color: var(--text); font-size: 13px; line-height: 1.7; margin: 12px 0 8px; opacity: 0.92; }
.goal-meta { font-size: 11px; color: var(--muted); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.goal-meta-item strong { color: var(--text); }
.goal-meta a { color: var(--accent); text-decoration: none; border-bottom: 1px dashed var(--accent); }
.goal-meta a:hover { color: var(--text); }
.goal-meta-sep { color: var(--border); }

/* Paths overview (Loop 20) — one Game, many ways in */
.paths-card {
  background: linear-gradient(135deg, rgba(60,60,90,0.16) 0%, rgba(80,60,40,0.12) 100%);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px 22px;
  margin: 16px 0;
}
.paths-header { display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
.paths-icon { font-size: 28px; line-height: 1; }
.paths-title-block { flex: 1; }
.paths-label { font-size: 10px; color: var(--accent); letter-spacing: 1.4px; font-weight: 700; }
.paths-title { font-size: 16px; font-weight: 700; color: var(--text); margin-top: 2px; }
.paths-blurb { color: var(--muted); font-size: 12px; line-height: 1.6; margin: 6px 0 14px; }
.paths-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}
.path-tile {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s, transform 0.1s;
}
.path-tile.path-live { border-color: var(--accent); cursor: pointer; }
.path-tile.path-live:hover { transform: translateY(-1px); border-color: var(--accent); }
a.path-tile { display: flex; }
.path-glyph { font-size: 22px; line-height: 1; }
.path-name { font-weight: 700; font-size: 13px; color: var(--text); margin-top: 2px; }
.path-desc { font-size: 11px; color: var(--muted); line-height: 1.5; flex: 1; }
.path-status { font-size: 10px; letter-spacing: 0.6px; font-weight: 600; margin-top: 4px; }
.path-status-live { color: #84d488; }
.path-status-soon { color: var(--accent); }
.path-status-watch { color: var(--muted); }

/* Retreat Interest card (Loop 15) */
.retreat-card {
  background: linear-gradient(135deg, rgba(40,80,60,0.18) 0%, rgba(60,40,80,0.14) 100%);
  border: 1px solid var(--accent);
  border-radius: 12px;
  padding: 20px 22px;
  margin: 18px 0 16px;
  position: relative;
}
.retreat-header { display: flex; align-items: center; gap: 14px; margin-bottom: 6px; }
.retreat-icon { font-size: 32px; line-height: 1; }
.retreat-title-block { flex: 1; min-width: 0; }
.retreat-label { font-size: 10px; color: var(--accent); letter-spacing: 1.4px; font-weight: 700; }
.retreat-title { font-size: 18px; font-weight: 700; color: var(--text); margin-top: 2px; }
.retreat-counter { text-align: right; }
.retreat-counter-n { font-size: 28px; font-weight: 800; color: var(--accent); line-height: 1; font-family: ui-monospace, "SF Mono", Menlo, monospace; }
.retreat-counter-lbl { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; margin-top: 2px; }
.retreat-blurb { color: var(--muted); font-size: 13px; line-height: 1.6; margin: 8px 0 14px; }
.retreat-form { display: flex; flex-direction: column; gap: 10px; }
.retreat-field { display: flex; flex-direction: column; gap: 4px; position: relative; }
.retreat-field > span { font-size: 11px; color: var(--accent); letter-spacing: 0.6px; text-transform: uppercase; font-weight: 600; }
.retreat-field input,
.retreat-field textarea {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 10px;
  color: var(--text);
  font: inherit;
  font-size: 13px;
  resize: vertical;
}
.retreat-field input:focus,
.retreat-field textarea:focus { border-color: var(--accent); outline: none; }
.retreat-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 4px;
  flex-wrap: wrap;
}
.retreat-checkbox { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--muted); cursor: pointer; }
.retreat-submit {
  background: var(--accent);
  color: var(--bg);
  border: none;
  border-radius: 6px;
  padding: 10px 18px;
  font-weight: 700;
  cursor: pointer;
  font-size: 13px;
}
.retreat-submit:hover { filter: brightness(1.1); }
.retreat-submit:disabled { opacity: 0.6; cursor: progress; }
.retreat-msg {
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
}
.retreat-msg.ok { background: rgba(132,212,136,0.14); border: 1px solid rgba(132,212,136,0.5); color: var(--text); }
.retreat-msg.err { background: rgba(212,90,90,0.14); border: 1px solid rgba(212,90,90,0.5); color: var(--text); }

/* Inviter banner — when arriving via someone's invite link */
.inviter-banner {
  background: linear-gradient(135deg, rgba(184, 156, 213, 0.12), rgba(132, 212, 136, 0.04));
  border: 1px solid var(--unknown);
  border-radius: 10px;
  padding: 12px 18px;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--text-bright);
}
.inviter-banner .inv-icon { font-size: 20px; margin-right: 8px; }
.inviter-banner strong { color: var(--accent-bright); }

/* Next move coach */
.next-move {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 20px;
  background: linear-gradient(135deg, rgba(232, 185, 116,0.08), rgba(232, 185, 116,0.02));
  border: 1px solid var(--accent);
  border-radius: 8px;
  margin-bottom: 16px;
}
.nm-icon { font-size: 28px; color: var(--accent); flex-shrink: 0; }
.nm-text { flex: 1; min-width: 0; }
.nm-label { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; font-weight: 700; }
.nm-action { font-size: 16px; font-weight: 700; color: var(--text); margin-top: 4px; }
.nm-cta {
  background: var(--accent);
  color: #1a0e02;
  padding: 10px 16px;
  border-radius: 6px;
  text-decoration: none;
  font-weight: 700;
  font-size: 13px;
  flex-shrink: 0;
}
.nm-cta:hover { transform: translateY(-1px); }

/* Funnel */
.funnel-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 24px;
}
.funnel { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.funnel-step {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 16px;
  display: grid;
  grid-template-columns: 60px 1fr;
  gap: 12px;
  align-items: center;
  width: min(100%, 480px);
}
.funnel-step-active { border-left: 3px solid var(--good); }
.funnel-num { font-size: 22px; font-weight: 700; color: var(--accent); text-align: center; }
.funnel-label { font-weight: 700; font-size: 13px; color: var(--text); }
.funnel-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }
.funnel-arrow { color: var(--muted); font-size: 12px; }

/* Onboarding journey */
.onboarding-card {
  background: var(--surface);
  border: 1px solid var(--good);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 24px;
}
.onboard-steps { display: flex; flex-direction: column; gap: 6px; }
.onboard-step {
  display: grid;
  grid-template-columns: 24px 36px 1fr;
  gap: 12px;
  align-items: start;
  padding: 12px 14px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}
.onboard-step:hover { border-color: var(--good); }
.onboard-step input[type="checkbox"] {
  width: 20px;
  height: 20px;
  margin-top: 2px;
  accent-color: var(--good);
  cursor: pointer;
}
.onboard-step input[type="checkbox"]:checked ~ .step-content .step-title {
  text-decoration: line-through;
  color: var(--muted);
}
.step-num {
  width: 32px;
  height: 32px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-weight: 700;
  color: var(--accent);
  font-size: 14px;
}
.step-title { font-weight: 700; font-size: 14px; color: var(--text); }
.step-desc { font-size: 12px; color: var(--muted); margin-top: 4px; line-height: 1.5; }

/* Quick Reference rail — Three Currencies, Player Promise, etc. */
.quick-ref {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 8px;
  margin-bottom: 16px;
}
.qr-card {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-top: 3px solid var(--accent);
  border-radius: 8px;
  padding: 12px 14px;
}
.qr-icon { font-size: 22px; line-height: 1; }
.qr-title { font-weight: 700; font-size: 13px; color: var(--text-bright); margin-top: 4px; }
.qr-list { list-style: none; padding: 0; margin: 8px 0 0; font-size: 11px; line-height: 1.6; color: var(--muted); }
.qr-list li { padding: 2px 0; }
.qr-list strong { color: var(--accent); }

/* Connective tissue between player-journey sections */
.connector {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  margin: -8px 0 12px;
  background: rgba(232, 185, 116, 0.04);
  border-left: 2px dashed var(--accent);
  border-radius: 0 6px 6px 0;
}
.conn-arrow {
  font-size: 18px;
  color: var(--accent);
  flex-shrink: 0;
}
.conn-text {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.5;
  font-style: italic;
}

/* Progressive disclosure: completed forms collapse to summary */
.sign-card.completed,
.character-card-quest.completed,
.proof-submit-card.completed {
  position: relative;
}
.sign-card.completed > *:not(h2),
.character-card-quest.completed > *:not(h2),
.proof-submit-card.completed > *:not(h2) {
  display: none;
}
.sign-card.completed h2::after,
.character-card-quest.completed h2::after,
.proof-submit-card.completed h2::after {
  content: " · ✓ done — click to expand";
  font-size: 11px;
  font-weight: 400;
  color: var(--good);
  letter-spacing: 0;
  text-transform: none;
}
.sign-card.completed,
.character-card-quest.completed,
.proof-submit-card.completed {
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.18s;
}
.sign-card.completed:hover,
.character-card-quest.completed:hover,
.proof-submit-card.completed:hover { opacity: 1; }
.sign-card.completed.expanded > *,
.character-card-quest.completed.expanded > *,
.proof-submit-card.completed.expanded > * { display: revert; }

/* Next step gets gold ring */
.next-step {
  box-shadow: 0 0 0 2px var(--accent), 0 8px 32px rgba(232,185,116,0.18);
}

/* Sign Agreement form */
.sign-card {
  background: var(--surface);
  border: 1px solid var(--good);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 24px;
}
.sign-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 14px;
  margin-bottom: 16px;
}
@media (max-width: 700px) { .sign-form { grid-template-columns: 1fr; } }
.sign-form label { display: flex; flex-direction: column; gap: 4px; font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
.sign-form label.sign-radio {
  flex-direction: row;
  align-items: center;
  gap: 8px;
  text-transform: none;
  letter-spacing: normal;
  font-size: 13px;
  color: var(--text);
  font-weight: 400;
}
.sign-form label:has(textarea) { grid-column: 1 / -1; }
.sign-form input, .sign-form textarea {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px 10px;
  color: var(--text);
  font-size: 13px;
  font-family: inherit;
  text-transform: none;
  letter-spacing: normal;
  font-weight: 400;
}
.sign-form input:focus, .sign-form textarea:focus { outline: none; border-color: var(--good); }
.sign-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.sign-actions button { font-family: inherit; cursor: pointer; border: none; }

.sign-extras {
  margin: 12px 0;
}
.sign-extras-summary {
  cursor: pointer;
  color: var(--accent);
  font-size: 12px;
  padding: 8px 12px;
  background: var(--surface-2);
  border-radius: 6px;
  user-select: none;
  list-style: none;
}
.sign-extras-summary::-webkit-details-marker { display: none; }
.sign-extras-summary:hover { background: var(--border); }
.sign-extras[open] .sign-extras-summary::after { content: " (collapse)"; opacity: 0.6; }

.sign-confirmation {
  margin-top: 20px;
  padding: 24px;
  background: linear-gradient(135deg, rgba(132, 212, 136,0.10), rgba(232, 185, 116,0.06));
  border: 1px solid var(--good);
  border-radius: 10px;
  text-align: center;
  display: none;
  animation: signCelebrate 0.6s ease-out;
}
.sign-confirmation.show { display: block; }
@keyframes signCelebrate {
  from { opacity: 0; transform: translateY(8px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.sc-burst { font-size: 48px; line-height: 1; margin-bottom: 8px; animation: burst 0.6s ease-out; }
.sign-confirmation h3 { color: var(--good); margin: 8px 0 4px; font-size: 18px; }
.sign-confirmation p { font-size: 13px; color: var(--text); margin: 6px 0; }
.sc-action { color: var(--muted); font-size: 12px; }
.sc-next { background: var(--surface-2); padding: 10px 14px; border-radius: 6px; margin-top: 12px; }

/* Character Quest */
.character-card-quest {
  background: linear-gradient(135deg, rgba(184, 156, 213, 0.08), rgba(232, 185, 116, 0.04));
  border: 1px solid var(--unknown);
  border-radius: 10px;
  padding: 18px 22px;
  margin-bottom: 24px;
}
.card-tiers, .card-levels {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 6px;
  margin: 8px 0;
}
.card-tier, .card-level {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 12px;
  text-align: center;
  font-size: 12px;
}
.card-level { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.cl-num { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 13px; font-weight: 700; color: var(--accent); }
.cl-name { font-weight: 700; font-size: 12px; color: var(--text); }
.cl-detail { font-size: 10px; color: var(--muted); }
.ct-icon { font-size: 22px; line-height: 1; }
.ct-label { font-weight: 700; font-size: 12px; margin-top: 4px; color: var(--text); }
.ct-sub { font-size: 10px; color: var(--muted); margin-top: 2px; }

/* Proof submit card */
.proof-submit-card {
  background: linear-gradient(135deg, rgba(132, 212, 136, 0.06), rgba(124, 196, 168, 0.04));
  border: 1px solid var(--good);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 24px;
}

/* Champions Roll */
.champions-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 24px;
}

/* Brand subtitle */
.brand-sub { font-size: 14px; font-weight: 400; color: var(--muted); margin-left: 4px; }
@media (max-width: 700px) { .brand-sub { display: block; font-size: 12px; margin-left: 0; margin-top: 2px; } }

/* Founder Witness card (player mode social proof) */
.founder-witness-card {
  background: linear-gradient(135deg, rgba(232, 185, 116,0.10), rgba(124, 196, 168,0.04));
  border: 1px solid var(--accent);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 16px;
  position: relative;
  overflow: hidden;
}
.founder-witness-card::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top right, rgba(232, 185, 116,0.08), transparent 50%);
  pointer-events: none;
}
.fw-row { display: grid; grid-template-columns: 56px 1fr; gap: 16px; align-items: start; position: relative; }
.fw-icon {
  font-size: 36px;
  width: 56px;
  height: 56px;
  background: var(--surface);
  border: 2px solid var(--accent);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.fw-label { font-size: 10px; color: var(--accent); letter-spacing: 1.5px; font-weight: 700; }
.fw-quote {
  font-family: "Cormorant Garamond", "Iowan Old Style", Georgia, serif;
  font-size: 18px;
  color: var(--text-bright);
  margin-top: 8px;
  line-height: 1.5;
  font-style: italic;
  font-weight: 500;
}
.fw-attribution { font-size: 11px; color: var(--muted); margin-top: 8px; }

/* After-sign card */
.after-sign-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 24px;
}
.after-sign-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 8px;
}
.after-step {
  display: grid;
  grid-template-columns: 36px 1fr;
  gap: 12px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 14px;
}
.after-step-num {
  font-size: 24px;
  color: var(--accent);
  font-weight: 700;
  line-height: 1;
}
.after-step-title { font-weight: 700; font-size: 13px; color: var(--text); }
.after-step-desc { font-size: 11px; color: var(--muted); margin-top: 4px; line-height: 1.5; }

/* Champions list */
.champions-list { display: flex; flex-direction: column; gap: 6px; }
.champion-row {
  display: grid;
  grid-template-columns: 56px 1fr auto;
  gap: 14px;
  align-items: center;
  padding: 10px 14px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--good);
  border-radius: 6px;
}
.champion-num {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 14px;
  font-weight: 700;
  color: var(--accent);
  text-align: center;
  background: var(--bg);
  border-radius: 4px;
  padding: 6px 8px;
}
.champion-info { min-width: 0; }
.champion-name { font-weight: 700; color: var(--text); font-size: 14px; }
.champion-role { font-size: 11px; color: var(--muted); margin-top: 2px; }
.champion-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; font-size: 11px; color: var(--muted); }
.champion-date { font-family: ui-monospace, "SF Mono", Menlo, monospace; }

/* Invitation */
.invite-card {
  background: linear-gradient(135deg, rgba(124, 196, 168,0.06), transparent);
  border: 1px solid #4ecdc4;
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 24px;
}
.invite-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.invite-actions button, .invite-actions a { font-family: inherit; cursor: pointer; border: none; }
.invite-preview pre { word-break: break-word; }

/* Canonical Library wrapper — collapsed by default, click to reveal all docs */
.canonical-library-wrapper {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  margin: 16px 0;
  overflow: hidden;
}
.canonical-library-wrapper[open] { border-color: var(--accent); }
.cl-summary {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  cursor: pointer;
  list-style: none;
  user-select: none;
}
.cl-summary::-webkit-details-marker { display: none; }
.cl-summary:hover { background: rgba(232,185,116,0.04); }
.cl-icon { font-size: 26px; line-height: 1; }
.cl-title-block { flex: 1; min-width: 0; }
.cl-title { font-weight: 700; font-size: 14px; color: var(--text); }
.cl-sub { font-size: 11px; color: var(--muted); margin-top: 4px; line-height: 1.4; }
.cl-expand { font-size: 11px; color: var(--accent); white-space: nowrap; }
.canonical-library-wrapper[open] .cl-expand { display: none; }
.canonical-library-wrapper > .canonical-library {
  padding: 0 18px 18px;
  border-top: 1px solid var(--border);
}

/* Canonical Documents Library — inline rendering */
.canonical-library {
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px;
  margin: 8px 0 16px;
}
.inline-doc {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}
.inline-doc[open] { border-color: var(--accent); }
.inline-doc-summary {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  list-style: none;
}
.inline-doc-summary::-webkit-details-marker { display: none; }
.inline-doc-summary:hover { background: rgba(232, 185, 116,0.04); }
.doc-icon { font-size: 22px; line-height: 1; flex-shrink: 0; }
.doc-title-block { flex: 1; min-width: 0; }
.doc-title { font-weight: 700; font-size: 14px; color: var(--text); }
.doc-subtitle { font-size: 11px; color: var(--accent); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
.doc-summary { font-size: 12px; color: var(--muted); margin-top: 4px; }
.doc-expand { font-size: 11px; color: var(--accent); margin-left: auto; flex-shrink: 0; }
.inline-doc[open] .doc-expand { color: var(--muted); }
.inline-doc-body {
  padding: 16px 24px 20px;
  border-top: 1px solid var(--border);
  background: var(--surface);
  font-size: 13px;
  line-height: 1.7;
  max-height: 70vh;
  overflow-y: auto;
}

/* Loop poster row + 4 quadrants */
.loop-poster-row {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 24px;
  margin: 8px 0 16px;
  align-items: start;
}
@media (max-width: 900px) { .loop-poster-row { grid-template-columns: 1fr; } }
.loop-quadrants {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
@media (max-width: 600px) { .loop-quadrants { grid-template-columns: 1fr; } }
.loop-q {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 14px;
  position: relative;
}
.loop-q-num {
  position: absolute;
  top: 8px;
  right: 12px;
  width: 22px;
  height: 22px;
  background: var(--surface);
  border: 1px solid var(--accent);
  color: var(--accent);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 11px;
  font-weight: 700;
}
.loop-q-icon { font-size: 26px; line-height: 1; margin-bottom: 4px; }
.loop-q-title { font-weight: 700; font-size: 13px; color: var(--text); }
.loop-q-sub { font-size: 10px; color: var(--accent); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
.loop-q-tag { font-size: 11px; color: var(--muted); margin-top: 6px; line-height: 1.4; }
.loop-q-1 { border-left: 3px solid #b89cd5; }   /* magenta — Party */
.loop-q-2 { border-left: 3px solid #84d488; }   /* green — Game */
.loop-q-3 { border-left: 3px solid #7cb8e0; }   /* blue — Apprentice */
.loop-q-4 { border-left: 3px solid var(--accent); } /* gold — Builder */

/* Progression path */
.progression-row {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  justify-content: center;
  margin: 8px 0;
}
.prog-stage {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  text-align: center;
  flex: 1;
  min-width: 140px;
  border-top: 3px solid var(--accent);
}
.prog-icon { font-size: 24px; line-height: 1; }
.prog-name { font-weight: 700; font-size: 13px; color: var(--text); margin-top: 4px; }
.prog-quote { font-size: 10px; color: var(--muted); margin-top: 4px; font-style: italic; line-height: 1.3; }
.prog-arrow { color: var(--muted); font-size: 16px; }
@media (max-width: 700px) { .prog-arrow { display: none; } }

/* 7 System Areas */
.systems-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 8px;
}
.sys-card {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px 14px;
  border-top: 3px solid var(--p2);
}
.sys-icon { font-size: 22px; line-height: 1; }
.sys-name { font-weight: 700; font-size: 13px; color: var(--text); margin-top: 4px; }
.sys-desc { font-size: 11px; color: var(--muted); margin-top: 4px; line-height: 1.5; }
.sys-card:nth-child(1) { border-top-color: #b89cd5; }
.sys-card:nth-child(2) { border-top-color: #7cb8e0; }
.sys-card:nth-child(3) { border-top-color: var(--accent); }
.sys-card:nth-child(4) { border-top-color: #e57b7b; }
.sys-card:nth-child(5) { border-top-color: var(--good); }
.sys-card:nth-child(6) { border-top-color: var(--accent-bright); }
.sys-card:nth-child(7) { border-top-color: var(--p2); }

/* Framework poster row */
.framework-poster-row {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 24px;
  margin: 8px 0 16px;
  align-items: start;
}
@media (max-width: 900px) { .framework-poster-row { grid-template-columns: 1fr; } }
.framework-content { min-width: 0; }
"""


JS = """
const search = document.getElementById('svcSearch');
const pills = document.querySelectorAll('.tag-pill');
const allSvc = document.querySelectorAll('.svc');
const allGroups = document.querySelectorAll('details.svc-group');

let activeTags = new Set(['P1','P2','infra','cruft','unknown']);

function applyFilters() {
  const q = (search?.value || '').toLowerCase().trim();
  allGroups.forEach(g => {
    const tag = g.dataset.tag;
    const items = g.querySelectorAll('.svc');
    let visible = 0;
    items.forEach(s => {
      const name = s.textContent.toLowerCase();
      const matchesText = !q || name.includes(q);
      const matchesTag = activeTags.has(tag);
      const show = matchesText && matchesTag;
      s.style.display = show ? '' : 'none';
      if (show) visible++;
    });
    g.style.display = (visible > 0 || (!q && activeTags.has(tag))) ? '' : 'none';
    if (q && visible > 0) g.open = true;
  });
}

if (search) search.addEventListener('input', applyFilters);
pills.forEach(p => {
  p.addEventListener('click', () => {
    const t = p.dataset.tag;
    if (activeTags.has(t)) { activeTags.delete(t); p.classList.remove('active'); }
    else { activeTags.add(t); p.classList.add('active'); }
    applyFilters();
  });
});

// --- Live probes ---------------------------------------------------------
// Fire mode=no-cors fetch for each probe row. Opaque success = reachable.
// AbortController gives us a 5s ceiling. Failure means DNS / network / timeout.
async function probeRow(row) {
  const url = row.dataset.probe;
  const dot = row.querySelector('.live-status');
  if (!url || !dot) return;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5000);
  try {
    await fetch(url, { mode: 'no-cors', signal: controller.signal, cache: 'no-store' });
    dot.classList.add('live');
    dot.title = 'reachable';
  } catch (e) {
    // mixed-content blocks (http on https page) and private hosts land here.
    if (url.startsWith('http://') && location.protocol === 'https:') {
      dot.classList.add('warn');
      dot.title = 'probe blocked (mixed-content)';
    } else {
      dot.classList.add('bad');
      dot.title = 'unreachable: ' + (e.name || 'error');
    }
  } finally {
    clearTimeout(timer);
  }
}

document.querySelectorAll('tr.probe').forEach(probeRow);
document.querySelectorAll('tr.no-probe .live-status').forEach(d => {
  d.style.background = 'var(--cruft)';
  d.title = 'no URL to probe';
});

// --- Relative timestamps -------------------------------------------------
function relTime(iso) {
  if (!iso) return '';
  const t = new Date(iso).getTime();
  if (isNaN(t)) return '';
  const diff = (Date.now() - t) / 1000;
  if (diff < 60) return Math.round(diff) + 's ago';
  if (diff < 3600) return Math.round(diff/60) + 'm ago';
  if (diff < 86400) return Math.round(diff/3600) + 'h ago';
  return Math.round(diff/86400) + 'd ago';
}
function refreshRelTimes() {
  document.querySelectorAll('.fresh-rel[data-ts]').forEach(el => {
    el.textContent = relTime(el.dataset.ts);
  });
}
refreshRelTimes();
setInterval(refreshRelTimes, 30000);

// --- Welcome modal (first-time visitors) ----------------------------------
(function initWelcome() {
  const modal = document.getElementById('welcomeModal');
  if (!modal) return;
  let seen = false;
  try { seen = localStorage.getItem('fpai-cockpit-welcomed') === '1'; } catch (e) {}
  if (!seen) modal.classList.add('show');
  function dismiss() {
    modal.classList.remove('show');
    try { localStorage.setItem('fpai-cockpit-welcomed', '1'); } catch (e) {}
  }
  document.getElementById('welcomeDismiss')?.addEventListener('click', dismiss);
  document.getElementById('welcomeStart')?.addEventListener('click', () => {
    dismiss();
    setTimeout(() => {
      const wrapper = document.querySelector('.canonical-library-wrapper');
      if (wrapper) wrapper.open = true;
      const target = document.getElementById('doc-manifesto');
      if (target) {
        target.open = true;
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 300);
  });
  document.getElementById('welcomeSign')?.addEventListener('click', () => {
    dismiss();
    setTimeout(() => {
      const target = document.getElementById('signCard');
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 300);
  });
})();

// --- Sticky TOC navigation ------------------------------------------------
(function initTOC() {
  const nav = document.getElementById('tocNav');
  const list = document.getElementById('tocList');
  const toggle = document.getElementById('tocToggle');
  if (!nav || !list || !toggle) return;

  // Find all h2 elements in the wrap (skip ones inside inline-doc bodies)
  const headings = Array.from(document.querySelectorAll('.wrap h2')).filter(h => {
    return !h.closest('.inline-doc-body');
  });

  headings.forEach((h, i) => {
    if (!h.id) h.id = 'sec-' + i;
    const txt = h.textContent.replace(/\s+—.*/, '').replace(/\s+\d+/, '').trim().slice(0, 40);
    const btn = document.createElement('button');
    btn.className = 'toc-link';
    btn.textContent = txt;
    btn.addEventListener('click', () => {
      h.scrollIntoView({ behavior: 'smooth', block: 'start' });
      nav.classList.remove('open');
    });
    list.appendChild(btn);
  });

  toggle.addEventListener('click', () => nav.classList.toggle('open'));

  // Highlight active section as you scroll
  const links = list.querySelectorAll('.toc-link');
  function updateActive() {
    let active = 0;
    const scrollY = window.scrollY + 100;
    headings.forEach((h, i) => {
      if (h.offsetTop <= scrollY) active = i;
    });
    links.forEach((l, i) => l.classList.toggle('active', i === active));
  }
  document.addEventListener('scroll', updateActive, { passive: true });
  updateActive();
})();

// --- Scroll progress bar -------------------------------------------------
(function initScrollProgress() {
  const bar = document.getElementById('scrollProgress');
  if (!bar) return;
  function update() {
    const h = document.documentElement;
    const total = h.scrollHeight - h.clientHeight;
    const pct = total > 0 ? (h.scrollTop / total) * 100 : 0;
    bar.style.width = pct + '%';
  }
  document.addEventListener('scroll', update, { passive: true });
  update();
})();

// --- Starfield (subtle, slow, atmospheric) -------------------------------
(function initStarfield() {
  const svg = document.getElementById('starfield');
  if (!svg) return;
  const w = window.innerWidth;
  const h = Math.max(window.innerHeight, document.documentElement.scrollHeight);
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  svg.setAttribute('width', w);
  svg.setAttribute('height', h);
  // Density: ~1 star per 12000px²
  const count = Math.min(180, Math.floor((w * h) / 12000));
  let stars = '';
  for (let i = 0; i < count; i++) {
    const x = Math.random() * w;
    const y = Math.random() * h;
    const r = Math.random() * 1.4 + 0.3;
    const delay = Math.random() * 4;
    stars += `<circle class="star" cx="${x.toFixed(0)}" cy="${y.toFixed(0)}" r="${r.toFixed(1)}" style="animation-delay:${delay.toFixed(1)}s" />`;
  }
  svg.innerHTML = stars;
})();

// --- Identity prompt — Champions who haven't logged in yet -------------
(function initIdentity() {
  const promptEl = document.getElementById('identityPrompt');
  if (!promptEl) return;
  let saved = '';
  try { saved = localStorage.getItem('fpai-cockpit-name') || ''; } catch (e) {}
  if (saved) {
    promptEl.style.display = 'none';
    return;
  }
  const submit = async () => {
    const name = (document.getElementById('ipName')?.value || '').trim();
    const errEl = document.getElementById('ipError');
    if (!name) { return; }
    try {
      const res = await fetch('/api/champion/lookup?name=' + encodeURIComponent(name), { cache: 'no-store' });
      const d = await res.json();
      if (!d.champion) {
        if (errEl) {
          errEl.textContent = 'No Champion found by that name. Sign below to become one — or check the spelling.';
          errEl.style.display = '';
        }
        return;
      }
      try { localStorage.setItem('fpai-cockpit-name', name); } catch (e) {}
      promptEl.style.display = 'none';
      if (typeof loadPlayerState === 'function') loadPlayerState();
    } catch (e) {
      if (errEl) {
        errEl.textContent = 'Could not reach the substrate. Try again.';
        errEl.style.display = '';
      }
    }
  };
  document.getElementById('ipSubmit')?.addEventListener('click', submit);
  document.getElementById('ipName')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') submit(); });
})();

// --- Animated number count-up ------------------------------------------
function animateNumber(el, from, to, duration = 800) {
  if (!el) return;
  const fromN = Number(from) || 0;
  const toN = Number(to) || 0;
  if (fromN === toN) { el.textContent = to; return; }
  const start = performance.now();
  const tick = (now) => {
    const elapsed = Math.min(1, (now - start) / duration);
    // ease-out cubic
    const eased = 1 - Math.pow(1 - elapsed, 3);
    const v = Math.round(fromN + (toN - fromN) * eased);
    el.textContent = String(to).startsWith('+') ? '+' + v : v;
    if (elapsed < 1) requestAnimationFrame(tick);
    else el.textContent = to;
  };
  requestAnimationFrame(tick);
}

// --- Game State (aggregate field metrics) -------------------------------
let _gsLast = {};
async function loadGameState() {
  try {
    const res = await fetch('/api/champion/stats', { cache: 'no-store' });
    if (!res.ok) return;
    const d = await res.json();
    const animate = (id, newVal) => {
      const el = document.getElementById(id);
      if (!el) return;
      const oldVal = _gsLast[id] !== undefined ? _gsLast[id] : 0;
      animateNumber(el, oldVal, newVal);
      // Pulse the parent metric card if value changed
      if (oldVal !== newVal && _gsLast[id] !== undefined) {
        const card = el.closest('.gs-metric');
        if (card) {
          card.classList.add('changed');
          setTimeout(() => card.classList.remove('changed'), 1400);
        }
      }
      _gsLast[id] = newVal;
    };
    animate('gsChampions', d.champions?.total ?? 0);
    animate('gsCards', d.cards?.total ?? 0);
    animate('gsProofs', d.proofs?.total ?? 0);
    animate('gsAffiliates', d.affiliate_links ?? 0);
    animate('gsScore', d.field_score_sum ?? 0);

    // === Goal panel — public progress on the 30-day goal ===
    const gpN = document.getElementById('goalProgressN');
    const gpL = document.getElementById('goalProgressLbl');
    const gTitle = document.getElementById('goalTitle');
    const gBlurb = document.getElementById('goalBlurb');
    const totalChamps = d.champions?.total ?? 0;
    if (gpN) gpN.textContent = totalChamps;
    if (gpL) gpL.textContent = totalChamps === 1 ? 'Champion (just James)' : (totalChamps + ' Champion' + (totalChamps === 1 ? '' : 's'));
    // When goal is hit (≥2 champions), reframe the panel as achieved + show what's next
    if (totalChamps >= 2) {
      if (gTitle) gTitle.textContent = '✓ Goal hit. The Game is no longer N=1.';
      if (gBlurb) gBlurb.textContent = 'The substrate proved it can hold a non-founder Champion. Next 30-day goal forms from here — see core/STATE/AI_GOALS.md for the AI system\\'s working goals.';
    }
    const growth = d.growth_this_week?.total ?? 0;
    const gEl = document.getElementById('gsGrowth');
    if (gEl) {
      const oldG = Number(String(_gsLast.gsGrowth || '0').replace('+', '')) || 0;
      animateNumber(gEl, oldG, '+' + growth);
      _gsLast.gsGrowth = growth;
    }
    // Tagline auto-adapts to field state
    const tagline = document.getElementById('gsTagline');
    if (tagline) {
      const total = (d.champions?.total ?? 0) + (d.proofs?.total ?? 0);
      if (total < 5) tagline.textContent = 'A new game. The first signatures are seeding the field.';
      else if (total < 50) tagline.textContent = 'Early players. The Game is beginning to play itself.';
      else if (total < 500) tagline.textContent = 'The field is alive. Loops compound. Witnesses confirm.';
      else tagline.textContent = 'A movement in motion. Each Champion adds their voice.';
    }
  } catch (e) {}
}
loadGameState();
setInterval(loadGameState, 60000);

// --- Inviter capture (?inviter=NAME URL param) -------------------------
(function captureInviter() {
  try {
    const params = new URLSearchParams(window.location.search);
    const inv = (params.get('inviter') || '').trim();
    if (inv) {
      // Persist for sign payload + display
      localStorage.setItem('fpai-cockpit-inviter', inv);
      const banner = document.getElementById('inviterBanner');
      const txt = document.getElementById('inviterText');
      if (banner && txt) {
        txt.innerHTML = 'You arrived through <strong>' + inv.replace(/[<>&]/g, '') + '</strong>\\'s invite. When you sign, they\\'re credited as your inviter — their Field Score grows alongside yours.';
        banner.style.display = 'block';
      }
    } else {
      // Show banner if previously stored from a redirect
      const stored = localStorage.getItem('fpai-cockpit-inviter');
      if (stored) {
        const banner = document.getElementById('inviterBanner');
        const txt = document.getElementById('inviterText');
        if (banner && txt) {
          txt.innerHTML = 'Your inviter on record: <strong>' + stored.replace(/[<>&]/g, '') + '</strong>';
          banner.style.display = 'block';
        }
      }
    }
  } catch (e) {}
})();

// --- Player State (renders for anyone who's identified locally) -------
async function loadPlayerState() {
  let name = '';
  try {
    name = localStorage.getItem('fpai-cockpit-name') || '';
  } catch (e) {}
  if (!name) return;
  const card = document.getElementById('playerStateCard');
  try {
    const res = await fetch('/api/champion/lookup?name=' + encodeURIComponent(name), { cache: 'no-store' });
    if (!res.ok) return;
    const d = await res.json();
    if (!d.champion && d.proofs_filed === 0 && d.affiliates_count === 0 && !d.card_present) {
      // Player isn't on the substrate yet; don't show
      return;
    }
    if (card) card.style.display = '';
    const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    setText('psName', d.name);
    setText('psScore', d.field_score_simple);
    setText('psChampNum', d.champion ? '#' + d.champion.champion_number : '—');
    setText('psLoops', d.proofs_filed);
    setText('psAffiliates', d.affiliates_count);
    setText('psCard', d.card_present ? (d.card_level || '✓') : '—');
    const url = location.origin + location.pathname + '?inviter=' + encodeURIComponent(d.name);
    const inviteEl = document.getElementById('psInviteUrl');
    if (inviteEl) inviteEl.textContent = url;

    // === Compute stage from completion state ===
    let stage = 'Visitor';
    let stageGlyph = '👋';
    if (d.champion) { stage = 'Guest'; stageGlyph = '👥'; }
    if (d.champion && d.card_present) { stage = 'Player'; stageGlyph = '🎮'; }
    if (d.champion && d.card_present && d.proofs_filed >= 1) { stage = 'Apprentice'; stageGlyph = '🎓'; }
    if (d.champion && d.card_present && d.proofs_filed >= 3) { stage = 'Steward'; stageGlyph = '🌱'; }
    if (d.champion && d.card_present && d.proofs_filed >= 3 && d.affiliates_count >= 3) { stage = 'Builder'; stageGlyph = '🏗'; }
    if (d.proofs_filed >= 10 && d.affiliates_count >= 10) { stage = 'Legend'; stageGlyph = '👑'; }
    setText('psStage', stageGlyph + ' ' + stage);

    // Progression bar — animate fill + highlight current stage
    const stageOrder = ['Visitor', 'Guest', 'Player', 'Apprentice', 'Steward', 'Builder', 'Legend'];
    const currentIdx = stageOrder.indexOf(stage);
    const fillPct = currentIdx <= 0 ? 4 : (currentIdx / (stageOrder.length - 1)) * 100;
    const fillEl = document.getElementById('pbFill');
    if (fillEl) fillEl.style.width = fillPct + '%';
    document.querySelectorAll('.pb-stage').forEach((el, i) => {
      el.classList.toggle('passed', i < currentIdx);
      el.classList.toggle('current', i === currentIdx);
    });
    const unlockEl = document.getElementById('pbUnlock');
    if (unlockEl) {
      const unlocks = {
        'Visitor':    `<strong>Next: Guest</strong> · Sign the World Peace Agreement to join the Roll.`,
        'Guest':      `<strong>Next: Player</strong> · Build your Character so others can find you for matching.`,
        'Player':     `<strong>Next: Apprentice</strong> · Run a 7-Day First Game and file your first Proof.`,
        'Apprentice': `<strong>Next: Steward</strong> · File ${Math.max(0, 3 - d.proofs_filed)} more Proof${(3 - d.proofs_filed) === 1 ? '' : 's'} to ascend.`,
        'Steward':    `<strong>Next: Builder</strong> · Bring ${Math.max(0, 3 - d.affiliates_count)} more aligned ${(3 - d.affiliates_count) === 1 ? 'person' : 'people'} into the Game.`,
        'Builder':    `<strong>Next: Legend</strong> · Build infrastructure that outlasts you. ${Math.max(0, 10 - d.proofs_filed)} more Proofs · ${Math.max(0, 10 - d.affiliates_count)} more Affiliates.`,
        'Legend':     `<strong>Legend</strong> · Legacy that outlasts you. The Game continues to play through what you built.`,
      };
      unlockEl.innerHTML = unlocks[stage] || '';
    }

    // Mobile sticky stage bar
    const msb = document.getElementById('mobileStageBar');
    if (msb) {
      msb.innerHTML = `<span class="msb-stage">${stageGlyph} ${stage}</span><span class="msb-score">·  ${d.field_score_simple} pts</span><span class="msb-next">→ ${(!d.champion ? 'Sign' : !d.card_present ? 'Build Character' : d.proofs_filed === 0 ? 'File Proof' : 'Share invite')}</span>`;
      msb.classList.add('show');
      document.body.classList.add('has-mobile-bar');
    }

    const tip = document.getElementById('psTip');
    if (tip) {
      let alreadyInterested = false;
      try { alreadyInterested = !!localStorage.getItem('fpai-cockpit-retreat-interest'); } catch (e) {}
      const next = !d.champion ? 'Sign the Agreement to become a Champion.'
        : !d.card_present ? 'Build your Character next (5 min · AI Port-In above).'
        : d.proofs_filed === 0 ? 'Run a 7-Day First Game and file your first Proof.'
        : d.affiliates_count === 0 ? 'Share your invite link — when an aligned person signs through it, your score grows.'
        : alreadyInterested ? 'You\\'re on the retreat list. Pick another path above too — the Game opens many doors.'
        : 'Pick a path below — retreat, apprenticeship, village, parties, commerce, coaching, witnessing. Many doors, one Game.';
      tip.textContent = '→ ' + next;
    }

    // === Paths overview + Retreat Interest panel — visible to any signed Champion ===
    const pathsCard = document.getElementById('pathsCard');
    if (pathsCard && d.champion) {
      pathsCard.style.display = '';
    }
    const retreatCard = document.getElementById('retreatCard');
    if (retreatCard && d.champion) {
      retreatCard.style.display = '';
    }

    // === Your Contributions ===
    const contribRow = document.getElementById('psContribRow');
    const contribCard = document.getElementById('psContrib');
    if (contribRow && contribCard) {
      const pills = [];
      if (d.champion) pills.push(`<span class="ps-contrib-pill"><strong>🌀</strong>Champion #${d.champion.champion_number}</span>`);
      if (d.proofs_filed > 0) pills.push(`<span class="ps-contrib-pill"><strong>🌱</strong>${d.proofs_filed} proof${d.proofs_filed === 1 ? '' : 's'}</span>`);
      if (d.affiliates_count > 0) pills.push(`<span class="ps-contrib-pill"><strong>🤝</strong>${d.affiliates_count} affiliate${d.affiliates_count === 1 ? '' : 's'}</span>`);
      if (d.card_present) pills.push(`<span class="ps-contrib-pill"><strong>🎴</strong>Character ${d.card_level || ''}</span>`);
      if (pills.length > 0) {
        contribRow.innerHTML = pills.join('');
        contribCard.style.display = '';
      }
    }

    // === Progressive disclosure: collapse completed forms ===
    progressiveDisclosure({
      signed: !!d.champion,
      hasCard: !!d.card_present,
      hasProof: d.proofs_filed > 0,
      hasAffiliate: d.affiliates_count > 0,
    });
  } catch (e) {}
}

// Allow click-to-expand on completed forms
document.addEventListener('click', (ev) => {
  const card = ev.target.closest('.sign-card.completed, .character-card-quest.completed, .proof-submit-card.completed');
  if (!card) return;
  // Only expand on the heading click (not on body)
  if (ev.target.tagName === 'BUTTON' || ev.target.closest('input, textarea, select, a, button')) return;
  card.classList.toggle('expanded');
});

function progressiveDisclosure(state) {
  // Collapse the Sign card if signed
  const signCard = document.getElementById('signCard');
  if (signCard && state.signed && !signCard.classList.contains('completed')) {
    signCard.classList.add('completed');
  }
  // Collapse the Character section if a card is present
  const ccQuest = document.getElementById('characterCardQuest');
  if (ccQuest && state.hasCard && !ccQuest.classList.contains('completed')) {
    ccQuest.classList.add('completed');
  }
  // Collapse the Proof Submit if at least one proof filed
  const proofCard = document.getElementById('proofSubmitCard');
  if (proofCard && state.hasProof && !proofCard.classList.contains('completed')) {
    proofCard.classList.add('completed');
  }
  // Reveal the relevant "next step" by adding a focus class
  let target = null;
  if (!state.signed) target = signCard;
  else if (!state.hasCard) target = ccQuest;
  else if (!state.hasProof) target = proofCard;
  if (target) target.classList.add('next-step');
}
loadPlayerState();
setInterval(loadPlayerState, 60000);

// --- Retreat Interest (Loop 15) -----------------------------------------
async function loadRetreatCount() {
  try {
    const res = await fetch('/api/retreat/stats', { cache: 'no-store' });
    if (!res.ok) return;
    const d = await res.json();
    const el = document.getElementById('retreatCount');
    if (el) el.textContent = d.public ?? d.total ?? '0';
  } catch (e) {}
}
loadRetreatCount();
setInterval(loadRetreatCount, 90000);

async function loadRetreatRoll() {
  try {
    const res = await fetch('/api/retreat/list', { cache: 'no-store' });
    if (!res.ok) return;
    const d = await res.json();
    const items = d.interests || [];
    const wrap = document.getElementById('retreatRoll');
    const list = document.getElementById('retreatRollList');
    const countEl = document.getElementById('retreatRollCount');
    if (!wrap || !list) return;
    if (items.length === 0) { wrap.style.display = 'none'; return; }
    if (countEl) countEl.textContent = items.length;
    list.innerHTML = items.map(it => {
      const player = (it.player || '[anonymous]').replace(/[<>]/g, '');
      const dates = (it.preferred_dates || '').replace(/[<>]/g, '');
      const date = (it.date_submitted || '').replace(/[<>]/g, '');
      return `<div class="champion-row"><div class="champion-num">🌴</div><div class="champion-info"><div class="champion-name">${player}</div><div class="champion-role">${dates ? 'Window: ' + dates : 'Open to dates'}</div></div><div class="champion-meta"><span class="champion-date">${date}</span></div></div>`;
    }).join('');
    wrap.style.display = '';
  } catch (e) {}
}
loadRetreatRoll();
setInterval(loadRetreatRoll, 120000);

document.getElementById('rtSubmit')?.addEventListener('click', async (ev) => {
  ev.preventDefault();
  const btn = document.getElementById('rtSubmit');
  const msg = document.getElementById('retreatMsg');
  const showMsg = (text, kind) => {
    if (!msg) return;
    msg.className = 'retreat-msg ' + kind;
    msg.textContent = text;
    msg.style.display = '';
  };
  let player = '';
  try { player = localStorage.getItem('fpai-cockpit-name') || ''; } catch (e) {}
  if (!player) {
    showMsg('Identify yourself first via "Already a Coherent Champion?" above.', 'err');
    return;
  }
  const dates = (document.getElementById('rtDates')?.value || '').trim();
  const contribution = (document.getElementById('rtContrib')?.value || '').trim();
  const why = (document.getElementById('rtWhy')?.value || '').trim();
  const isPublic = !!document.getElementById('rtPublic')?.checked;
  const honeypot = (document.getElementById('rtCompany')?.value || '').trim();

  if (btn) { btn.disabled = true; btn.textContent = 'Submitting…'; }
  try {
    const res = await fetch('/api/retreat/interest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        player,
        preferred_dates: dates || null,
        contribution: contribution || null,
        why_irresistible: why || null,
        consent: isPublic ? 'public' : 'private',
        company: honeypot || null,
      }),
    });
    const d = await res.json();
    if (!res.ok || !d.ok) {
      showMsg(d.detail || 'Could not submit. Try again in a moment.', 'err');
    } else {
      showMsg(d.message || 'You\\'re on the list. Thank you.', 'ok');
      try { localStorage.setItem('fpai-cockpit-retreat-interest', '1'); } catch (e) {}
      ['rtDates', 'rtContrib', 'rtWhy'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });
      loadRetreatCount();
      loadRetreatRoll();
    }
  } catch (e) {
    showMsg('Network error. Try again.', 'err');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '🌴 I\\'m interested →'; }
  }
});

// --- /match button + keyboard shortcut (Loop 24) -----------------------
async function runMatch() {
  let name = '';
  try { name = localStorage.getItem('fpai-cockpit-name') || ''; } catch (e) {}
  const btn = document.getElementById('psMatchBtn');
  const out = document.getElementById('psMatchResult');
  if (!out) return;
  if (btn) { btn.disabled = true; btn.textContent = '🎯 Finding your next move…'; }
  try {
    const url = '/api/champion/match' + (name ? '?name=' + encodeURIComponent(name) : '');
    const res = await fetch(url, { cache: 'no-store' });
    const d = await res.json();
    if (!d.ok) {
      out.innerHTML = '<span class="ps-match-result-text">Could not match: ' + (d.error || 'unknown error').replace(/[<>]/g, '') + '</span>';
    } else {
      const safeMove = (d.move || '').replace(/[<>]/g, '');
      const safeUrl = (d.url || '').replace(/[<>"']/g, '');
      const safeIcon = d.icon || '🎯';
      const ctaHtml = safeUrl ? '<a class="ps-match-result-cta" href="' + safeUrl + '">→ Take this move</a>' : '';
      out.innerHTML = '<span class="ps-match-result-icon">' + safeIcon + '</span><span class="ps-match-result-text">' + safeMove + '</span><br>' + ctaHtml;
    }
    out.style.display = '';
  } catch (e) {
    out.innerHTML = '<span class="ps-match-result-text">Network error. Try again.</span>';
    out.style.display = '';
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '🎯 What\\'s my next move?'; }
  }
}
document.getElementById('psMatchBtn')?.addEventListener('click', runMatch);

// Listen for slash-commands typed anywhere on the page (intercept before they go nowhere)
let _slashBuffer = '';
let _slashTimer = null;
document.addEventListener('keydown', (ev) => {
  // Skip if user is typing in an input/textarea
  if (ev.target.matches('input, textarea, select, [contenteditable]')) return;
  if (ev.key === '/') {
    _slashBuffer = '/';
    if (_slashTimer) clearTimeout(_slashTimer);
    _slashTimer = setTimeout(() => { _slashBuffer = ''; }, 2500);
    return;
  }
  if (_slashBuffer.startsWith('/') && /^[a-z]$/i.test(ev.key)) {
    _slashBuffer += ev.key.toLowerCase();
    if (_slashTimer) clearTimeout(_slashTimer);
    _slashTimer = setTimeout(() => { _slashBuffer = ''; }, 2500);
  }
  if (ev.key === 'Enter' && _slashBuffer.startsWith('/')) {
    const cmd = _slashBuffer.slice(1).toLowerCase();
    _slashBuffer = '';
    if (cmd === 'match') { ev.preventDefault(); runMatch(); }
    else if (cmd === 'game') { ev.preventDefault(); window.open('https://t.me/sunheartbrain_bot?text=/game', '_blank'); }
    else if (cmd === 'characters' || cmd === 'champions') {
      ev.preventDefault();
      const el = document.querySelector('.champions-card');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }
  }
});

document.getElementById('psCopyInviteBtn')?.addEventListener('click', async () => {
  const url = document.getElementById('psInviteUrl')?.textContent || '';
  try {
    await navigator.clipboard.writeText(url);
    const btn = document.getElementById('psCopyInviteBtn');
    if (btn) {
      btn.textContent = '✓ Copied';
      setTimeout(() => { btn.textContent = '📋 Copy'; }, 3000);
    }
  } catch (e) {
    alert('Could not copy. URL: ' + url);
  }
});

// --- Personalized greeting ----------------------------------------------
(function initGreeting() {
  const el = document.getElementById('greeting');
  if (!el) return;
  let name = '';
  try {
    const cs = JSON.parse(localStorage.getItem('fpai-cockpit-cs') || '{}');
    name = localStorage.getItem('fpai-cockpit-name') || '';
  } catch (e) {}
  // Also try to pick up from sign form on input
  const nameInput = document.getElementById('signName');
  function setGreeting(n) {
    if (n && n.trim()) {
      el.innerHTML = '<span class="greeting">welcome, ' + n.split(' ')[0] + '</span>';
      try { localStorage.setItem('fpai-cockpit-name', n.trim()); } catch (e) {}
    }
  }
  if (name) setGreeting(name);
  if (nameInput) {
    if (name && !nameInput.value) nameInput.value = name;
    nameInput.addEventListener('input', () => setGreeting(nameInput.value));
  }
})();

// --- Onboarding journey + Next Move coach ---------------------------------
const ONBOARD_KEY = 'fpai-cockpit-onboard';
const NEXT_MOVES = [
  { key: 'read', action: 'Read the Manifesto.', cta: 'Read inline →', href: '#doc-manifesto', openDoc: 'doc-manifesto' },
  { key: 'sign', action: 'Sign the World Peace Agreement.', cta: 'Sign now →', href: '#signCard' },
  { key: 'play', action: 'Run your 7-Day First Game.', cta: 'Open prompt →', href: '#doc-agreement-builder', openDoc: 'doc-agreement-builder' },
  { key: 'witness', action: 'Get one witness signature on your proof.', cta: 'Find a witness →', href: '#onboardSteps' },
  { key: 'invite', action: 'Bring one aligned person.', cta: 'Open invitation →', href: '#inviteCopyBtn' },
  { key: 'done', action: 'Run another loop, witness someone else, become a steward.', cta: 'Keep going →', href: '#' },
];
function loadOnboard() {
  try { return JSON.parse(localStorage.getItem(ONBOARD_KEY) || '{}'); } catch(e) { return {}; }
}
function saveOnboard(s) {
  try { localStorage.setItem(ONBOARD_KEY, JSON.stringify(s)); } catch(e) {}
}
function updateNextMove() {
  const state = loadOnboard();
  let nextIdx = NEXT_MOVES.findIndex(m => m.key !== 'done' && !state[m.key]);
  if (nextIdx === -1) nextIdx = NEXT_MOVES.length - 1;
  const move = NEXT_MOVES[nextIdx];
  const actionEl = document.getElementById('nmAction');
  const ctaEl = document.getElementById('nmCta');
  if (actionEl) actionEl.textContent = move.action;
  if (ctaEl) {
    ctaEl.textContent = move.cta;
    ctaEl.href = move.href;
    // For doc anchors, open the details element when clicked
    if (move.openDoc) {
      ctaEl.onclick = (ev) => {
        const doc = document.getElementById(move.openDoc);
        if (doc) doc.open = true;
      };
    } else {
      ctaEl.onclick = null;
    }
  }
}
const obState = loadOnboard();
document.querySelectorAll('.onboard-step input[type="checkbox"]').forEach(cb => {
  const key = cb.dataset.stepKey;
  if (obState[key]) cb.checked = true;
  cb.addEventListener('change', () => {
    obState[key] = cb.checked;
    saveOnboard(obState);
    updateNextMove();
    if (cb.checked) {
      const step = cb.closest('.onboard-step');
      if (step) {
        step.classList.add('celebrating');
        setTimeout(() => step.classList.remove('celebrating'), 700);
      }
    }
  });
});
updateNextMove();

// --- Sign the Agreement --------------------------------------------------
function buildSignedAgreement() {
  const name = (document.getElementById('signName')?.value || '').trim();
  const handle = (document.getElementById('signHandle')?.value || '').trim();
  const email = (document.getElementById('signEmail')?.value || '').trim();
  const witness = (document.getElementById('signWitness')?.value || '').trim();
  const why = (document.getElementById('signWhy')?.value || '').trim();
  const isPublic = document.querySelector('input[name="signPublic"]:checked')?.value === 'true';
  const today = new Date().toISOString().slice(0, 10);
  const safeName = name || 'unsigned';
  const slug = safeName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'unnamed';
  const filename = `${today}_${slug}.md`;

  const md = `---
champion_id: ${today}_${slug}
date_signed: ${today}
name: ${name || '[your name]'}
handle: ${handle}
email: ${email}
witness: ${witness}
public: ${isPublic}
status: signed
manifesto_version: v1.0
---

# Coherent Champion of CHRIST

I, **${name || '[your name]'}**, having read the Coherent Champions of CHRIST Manifesto v1.0,
sign the World Peace Agreement.

## I agree

- to practice peace in thought, word, and action
- to reduce unnecessary suffering
- to seek understanding before hatred
- to repair where I have caused harm
- to protect life, truth, beauty, and future generations
- to become trustworthy with intelligence, influence, and resources
- that peace must become visible through action

*Signed not in perfection, but in sincere participation.*

${why ? `## Why I am signing\n\n${why}\n` : ''}
## Witness

${witness || '(no witness named at signing)'}

## Visibility

This signature is **${isPublic ? 'PUBLIC' : 'PRIVATE'}** — ${isPublic ? 'I consent to appearing on the public Champions Roll.' : 'this is a private signing; I prefer not to be listed publicly.'}

---

*Date: ${today}*
*Filename suggestion: \`core/INTENT/AGREEMENTS/champions/${filename}\`*
`;
  return { md, filename, name, isPublic };
}

function showSignConfirmation(name, action) {
  const card = document.getElementById('signCard');
  if (!card) return;
  let conf = document.getElementById('signConfirmation');
  if (!conf) {
    conf = document.createElement('div');
    conf.id = 'signConfirmation';
    conf.className = 'sign-confirmation';
    card.appendChild(conf);
  }
  conf.innerHTML = `
    <div class="sc-burst">✨</div>
    <h3>You signed the World Peace Agreement.</h3>
    <p>You are <strong>${name.split(' ')[0]}</strong>, Coherent Champion in formation.</p>
    <p class="sc-action">Your file was ${action}. Email it to <code>james.rick.stinson@gmail.com</code> if you haven't already — once it's committed to the repo, your name appears in the Champions Roll below.</p>
    <p class="sc-next"><strong>Your next move:</strong> open the AI-Assisted Player Card prompt and run your first 7-Day Game. <a class="link" href="#doc-agreement-builder" onclick="document.getElementById('doc-agreement-builder').open=true;">Open the prompt →</a></p>
  `;
  conf.classList.add('show');
  // Mark sign step in onboarding journey
  try {
    const ob = JSON.parse(localStorage.getItem('fpai-cockpit-onboard') || '{}');
    ob.sign = true;
    localStorage.setItem('fpai-cockpit-onboard', JSON.stringify(ob));
    const cb = document.querySelector('.onboard-step input[data-step-key="sign"]');
    if (cb) cb.checked = true;
    if (typeof updateNextMove === 'function') updateNextMove();
  } catch (e) {}
}

document.getElementById('signCopyBtn')?.addEventListener('click', async () => {
  const { md, name } = buildSignedAgreement();
  if (!name || name === 'unsigned') { alert('Please enter your name first.'); return; }
  try {
    await navigator.clipboard.writeText(md);
    document.getElementById('signCopyBtn').textContent = '✓ Copied';
    setTimeout(() => { document.getElementById('signCopyBtn').textContent = '📋 Copy signed Agreement'; }, 3000);
    showSignConfirmation(name, 'copied to your clipboard');
  } catch (e) {
    alert('Could not copy to clipboard. Use Download instead.');
  }
});

document.getElementById('signDownloadBtn')?.addEventListener('click', () => {
  const { md, filename, name } = buildSignedAgreement();
  if (!name || name === 'unsigned') { alert('Please enter your name first.'); return; }
  const blob = new Blob([md], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
  showSignConfirmation(name, `downloaded as ${filename}`);
});

document.getElementById('signEmailBtn')?.addEventListener('click', (e) => {
  e.preventDefault();
  const { md, name } = buildSignedAgreement();
  if (!name || name === 'unsigned') { alert('Please enter your name first.'); return; }
  const subject = encodeURIComponent(`World Peace Agreement signed — ${name}`);
  const body = encodeURIComponent(md);
  window.location.href = `mailto:james.rick.stinson@gmail.com?subject=${subject}&body=${body}`;
  showSignConfirmation(name, 'opened in your email');
});

// --- Character Quest -----------------------------------------------
const CARD_PORTIN_PROMPT = `You are helping me draft my Character for the Full Potential Game — a purpose-driven social network where players coordinate around quests, offers/needs matching, and witnessed reputation. Cards have a privacy-tiered, progressive structure.

Using everything you know about me from our prior conversations and any context I've shared with you, draft my Character following the schema below.

CRITICAL RULES:
- Be honest. For fields where you don't have enough data, write "[NEEDS INPUT]". Do not fabricate.
- Don't slip into hero-myth or marketing voice. Plain, direct, true.
- For the Reality layer, only fill what's actually documented. Mark gaps clearly.
- After the draft, list the top 5 fields where you most need my input to refine.

VISIBILITY TIERS:
🌐 Public — syndicates to social media
👥 Player — visible to other game players
🤍 Inner Circle — visible only to my Witness Roster
🔒 Sacred — only me + my AI

LEVELS (progressive depth):
🟢 L1 Signup · 🟡 L2 Player · 🔵 L3 Matching Depth · 🟣 L4 Living Character

SCHEMA TO FILL (output as clean markdown matching this structure):

# [MY NAME] — Character

## ✦ ASPIRATIONAL

### 🌐 🟢 Public Bio
[One paragraph, ~280 chars max, syndication-ready. Lead with name + archetype, mission shorthand, current activity, what I'm available for.]

### 🌐 🟢 Identity
- Full name + chosen name(s)
- Roles
- Locations
- Self-described archetype (my own myth-name for myself)

### 🌐 🟢 Mission
[One sentence. What I'm playing for.]

### Active Quests
🌐 🟢 Public titles (3–5)
👥 🟡 Player view: each quest with current status + bottleneck

### 🌐 🟢 Offers (3–6, concrete, verb-led)

### 👥 🟡 Needs

### 👥 🟡 Give / Receive / Deal Breakers

### 🌐 🟡 Living Agreements (how to engage with me)

### 🪶 👥 🔵 Energy / Typing
- Human Design (Type, Strategy, Authority, Profile, Definition)
- Astrology (Sun / Moon / Rising; full chart at L4)
- Enneagram (type + wing)
- Gene Keys (Life's Work, Evolution, Radiance, Purpose)
- Self-described archetype

### ⚙️ 👥 🔵 Operating Style
- Timezone + working hours
- Async ↔ Sync ratio
- Communication channels (ranked)
- Response time norm
- Meeting tolerance
- Solo ↔ Collaborative ratio
- Languages spoken

### 🛠 👥 🔵 Skills & Domains
- Concrete skills (verbs)
- Domain expertise
- Tool stack
- Witness domains (what I'm qualified to witness on someone else's card)

### 📖 🤍 🔵 Story / Mythos
- Origin story (1–2 paragraphs · plain, not marketing voice)
- Wound → Medicine
- Lineages (teachers, traditions, books, frameworks)
- Initiation moments

### 🌱 👥 🔵 Body / Practice
- Daily practices
- Body / temple notes (optional)
- Substances / sobriety status (🤍 Inner)
- Sleep pattern

### 🤝 👥 🔵 Compatibility
- Best collaborator type
- What shuts me down (friction triggers)
- Conflict style
- Trust default

## ✦ REALITY (mark every field [NEEDS INPUT] unless you have specific documented evidence)

### 👥 Receipts — what shipped (last 90 days)
### 🤍 Designed but not yet shipped (active build)
### 🤍 Graveyard — consciously released
### 🤍 Recurring Patterns
### 🔒 Money Reality
### 🤍 Body / Energy / Capacity (this week)
### Relational Reality (👥 Active / 🤍 Drifted-Ended / 🔒 Family / 👥 Currently seeking)
### 👥 Witness Roster (3–5 people authorized to call drift between Aspirational and Reality)

End with: "Top 5 fields where I most need your input to refine:" followed by the list.`;

document.getElementById('cardCopyPromptBtn')?.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(CARD_PORTIN_PROMPT);
    const btn = document.getElementById('cardCopyPromptBtn');
    if (btn) {
      btn.textContent = '✓ Copied — paste into your AI';
      setTimeout(() => { btn.textContent = '📋 Copy AI Port-In Prompt'; }, 4000);
    }
  } catch (e) {
    alert('Could not copy. Open the Quest doc and copy from there.');
  }
});

document.getElementById('cardSubmitBtn')?.addEventListener('click', async () => {
  const player = (document.getElementById('cardPlayer')?.value || '').trim();
  const handle = (document.getElementById('cardHandle')?.value || '').trim();
  const email = (document.getElementById('cardEmail')?.value || '').trim();
  const level = document.getElementById('cardLevel')?.value || 'L1';
  const visibility_default = document.getElementById('cardVisibility')?.value || 'player';
  const card_markdown = (document.getElementById('cardMarkdown')?.value || '').trim();
  const honeypot = (document.getElementById('cardHoneypot')?.value || '').trim();

  if (!player) { alert('Please enter your name.'); return; }
  if (card_markdown.length < 20) { alert('Please paste your Character markdown (the AI will produce something substantial).'); return; }

  const btn = document.getElementById('cardSubmitBtn');
  if (btn) { btn.disabled = true; btn.textContent = '🎴 Submitting...'; }

  try {
    const res = await fetch('/api/champion/card/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player, handle, email, level, visibility_default, card_markdown, company: honeypot }),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      const msg = data?.detail || data?.message || ('HTTP ' + res.status);
      throw new Error(msg);
    }
    if (btn) { btn.textContent = `✓ Card ${data.level} saved`; }
    const card = document.getElementById('characterCardQuest');
    if (card && !document.getElementById('cardConfirm')) {
      const conf = document.createElement('div');
      conf.id = 'cardConfirm';
      conf.className = 'sign-confirmation show';
      conf.innerHTML = `<div class="sc-burst">🎴</div><h3>Character ${data.level} saved.</h3><p>${escapeHTML(data.message || '')}</p><p class="sc-action">Your card is now a node in the network. You can update it anytime by submitting again with the same name.</p>`;
      card.appendChild(conf);
    }
  } catch (e) {
    if (btn) { btn.disabled = false; btn.textContent = '🎴 Submit my Character'; }
    alert('Could not submit: ' + e.message);
  }
});

// --- Proof Submit (file a completed loop) -----------------------------
document.getElementById('prfSubmitBtn')?.addEventListener('click', async () => {
  const player = (document.getElementById('prfPlayer')?.value || '').trim();
  const loopRaw = (document.getElementById('prfLoop')?.value || '').trim();
  const quest = (document.getElementById('prfQuest')?.value || '').trim();
  const output = (document.getElementById('prfOutput')?.value || '').trim();
  if (!player) { alert('Please enter your name or handle.'); return; }
  if (!loopRaw) { alert('Please enter a loop number.'); return; }
  if (!quest) { alert('Please enter the quest you set out to deliver.'); return; }
  if (!output) { alert('Please describe the output — what was completed.'); return; }
  const loop_number = parseInt(loopRaw, 10);
  if (isNaN(loop_number) || loop_number < 1) { alert('Loop number must be a positive integer.'); return; }
  const result = (document.getElementById('prfResult')?.value || '').trim();
  const witness = (document.getElementById('prfWitness')?.value || '').trim();
  const email = (document.getElementById('prfEmail')?.value || '').trim();
  const consent = document.querySelector('input[name="prfConsent"]:checked')?.value || 'public';
  const honeypot = (document.getElementById('prfHoneypot')?.value || '').trim();

  const btn = document.getElementById('prfSubmitBtn');
  if (btn) { btn.disabled = true; btn.textContent = '🌱 Filing...'; }
  try {
    const res = await fetch('/api/champion/proof/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player, handle: '', email, loop_number, quest, output, result, witness, consent, agreement_type: 'deliverable_by_date', company: honeypot }),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      const msg = data?.detail || data?.message || ('HTTP ' + res.status);
      throw new Error(msg);
    }
    if (btn) { btn.textContent = `✓ ${data.message || 'Filed'}`; }
    // Trigger Pulse refresh so the new event shows up
    setTimeout(() => { if (typeof loadFieldPulse === 'function') loadFieldPulse(); }, 500);
    // Show celebration card
    const card = document.getElementById('proofSubmitCard');
    if (card && !document.getElementById('prfConfirm')) {
      const conf = document.createElement('div');
      conf.id = 'prfConfirm';
      conf.className = 'sign-confirmation show';
      conf.innerHTML = `<div class="sc-burst">🌱</div><h3>Proof L${loop_number} filed.</h3><p>${escapeHTML(data.message || '')}</p><p class="sc-action">It will appear in the Field Pulse within seconds.</p>`;
      card.appendChild(conf);
    }
  } catch (e) {
    if (btn) { btn.disabled = false; btn.textContent = '🌱 File the proof'; }
    alert('Could not submit: ' + e.message);
  }
});

// --- Sign & Submit (the substrate-direct path: the Game plays itself) ---
document.getElementById('signSubmitBtn')?.addEventListener('click', async () => {
  const name = (document.getElementById('signName')?.value || '').trim();
  if (!name) { alert('Please enter your name first.'); return; }
  const handle = (document.getElementById('signHandle')?.value || '').trim();
  const email = (document.getElementById('signEmail')?.value || '').trim();
  const witness = (document.getElementById('signWitness')?.value || '').trim();
  const why = (document.getElementById('signWhy')?.value || '').trim();
  const isPublic = document.querySelector('input[name="signPublic"]:checked')?.value === 'true';
  const honeypot = (document.getElementById('signHoneypot')?.value || '').trim();
  const btn = document.getElementById('signSubmitBtn');
  if (btn) { btn.disabled = true; btn.textContent = '🌀 Signing...'; }
  try {
    let inviter = '';
    try { inviter = localStorage.getItem('fpai-cockpit-inviter') || ''; } catch (e) {}
    const res = await fetch('/api/champion/sign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, handle, email, witness, public: isPublic, why, inviter, company: honeypot }),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      const msg = data?.detail || data?.message || ('HTTP ' + res.status);
      throw new Error(msg);
    }
    showSignConfirmation(name, `submitted live — you are Coherent Champion #${data.champion_number}`);
    if (btn) { btn.textContent = `✓ Champion #${data.champion_number}`; }
    // Refresh the live Roll
    setTimeout(loadLiveChampions, 500);
  } catch (e) {
    if (btn) { btn.disabled = false; btn.textContent = '🌀 Sign & join the Roll'; }
    alert('Could not submit: ' + e.message + '. Try Email or Download as backup.');
  }
});

// --- Live Champions Roll fetch ----------------------------------------
async function loadLiveChampions() {
  try {
    const res = await fetch('/api/champion/list', { cache: 'no-store' });
    if (!res.ok) return;
    const data = await res.json();
    const liveCount = data.count || 0;
    if (liveCount === 0) return;
    // Find existing champions list and append/merge
    const list = document.querySelector('.champions-list');
    if (!list) return;
    // Don't duplicate James (champion_number 1 is on the static page already);
    // append any with champion_number > 0 from the live API that aren't already in DOM
    const seenNames = new Set(
      Array.from(list.querySelectorAll('.champion-name')).map(el => el.textContent.trim())
    );
    let appended = 0;
    for (const c of data.champions) {
      const name = c.name || '[unnamed]';
      if (seenNames.has(name)) continue;
      const num = c.champion_number || '?';
      const date = c.date_signed || '';
      const handle = c.handle || '';
      const role = c.role || '';
      const row = document.createElement('div');
      row.className = 'champion-row';
      row.innerHTML = `
        <div class="champion-num">#${num}</div>
        <div class="champion-info">
          <div class="champion-name">${escapeHTML(name)}</div>
          ${role ? '<div class="champion-role">' + escapeHTML(role) + '</div>' : ''}
        </div>
        <div class="champion-meta">
          ${handle ? '<span>' + escapeHTML(handle) + '</span>' : ''}
          <span class="champion-date">${escapeHTML(date)}</span>
        </div>
      `;
      list.appendChild(row);
      appended++;
    }
    if (appended > 0) {
      const card = list.closest('.champions-card');
      const heading = card?.querySelector('h2');
      if (heading) {
        const m = heading.innerHTML.match(/(\d+) signed · (\d+) public/);
        if (m) {
          heading.innerHTML = heading.innerHTML.replace(/(\d+) signed/, liveCount + ' signed').replace(/(\d+) public/, liveCount + ' public');
        }
      }
    }
  } catch (e) {
    // Silent — the static Roll still shows
  }
}
function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
loadLiveChampions();
setInterval(loadLiveChampions, 60000); // refresh every minute

// --- Field Pulse — live activity ticker ----------------------------------
async function loadFieldPulse() {
  try {
    const res = await fetch('/api/champion/recent?limit=8', { cache: 'no-store' });
    if (!res.ok) return;
    const data = await res.json();
    const feed = document.getElementById('fpFeed');
    if (!feed) return;
    if (!data.events || data.events.length === 0) {
      feed.innerHTML = '<div class="fp-empty">Listening for signals — be the first to sign.</div>';
      return;
    }
    feed.innerHTML = data.events.map(e => {
      const t = e.ts ? relativeTime(e.ts) : '';
      const icon = e.kind === 'signature' ? '🌀' : '⚡';
      const evIcon = e.icon || (e.kind === 'proof' ? '🌱' : '🌀');
      return '<div class="fp-event"><span class="fp-icon">' + evIcon + '</span><span class="fp-msg">' + escapeHTML(e.message || '') + '</span><span class="fp-time">' + escapeHTML(t) + '</span></div>';
    }).join('');
    const sub = document.getElementById('fpSub');
    if (sub) sub.textContent = `live · ${data.events.length} recent signal${data.events.length === 1 ? '' : 's'}`;
  } catch (e) {
    // Silent fail
  }
}
function relativeTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return Math.round(diff) + 's ago';
  if (diff < 3600) return Math.round(diff / 60) + 'm ago';
  if (diff < 86400) return Math.round(diff / 3600) + 'h ago';
  return Math.round(diff / 86400) + 'd ago';
}
loadFieldPulse();
setInterval(loadFieldPulse, 30000); // refresh every 30s

// --- Invitation generator ------------------------------------------------
function buildInvitation() {
  let me = '';
  try { me = localStorage.getItem('fpai-cockpit-name') || ''; } catch (e) {}
  const baseUrl = (typeof location !== 'undefined') ? (location.origin + location.pathname) : 'https://fullpotential.com/game';
  const inviteUrl = me ? (baseUrl + '?inviter=' + encodeURIComponent(me)) : baseUrl;
  const fromLine = me ? `\\n\\nFrom: ${me}` : '';

  return `Reality is already a game. This is the guide for those who know.

I'm signing the World Peace Agreement and starting a 7-Day First Game — a proof-based operating system for human potential. Six pillars: Coherence · Healing · Regeneration · Intelligence · Service · Truth.

It's not a religion. It's not a movement. It's a practice of becoming trustworthy with power.

If you're tired of chaos, manipulation, performative outrage — read the Manifesto. Sign if it lands. Run your first 7-day proof loop.

Coherent Champions of CHRIST: ${inviteUrl}

We are human and AI allies, committed to bringing coherence, healing, and regeneration to our world.${fromLine}`;
}

document.getElementById('inviteCopyBtn')?.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(buildInvitation());
    document.getElementById('inviteCopyBtn').textContent = '✓ Copied — paste anywhere';
    setTimeout(() => { document.getElementById('inviteCopyBtn').textContent = '📋 Copy invitation'; }, 3000);
  } catch (e) {
    alert('Could not copy. Use the preview below.');
  }
});

const inviteWa = document.getElementById('inviteWhatsApp');
if (inviteWa) inviteWa.href = `https://wa.me/?text=${encodeURIComponent(buildInvitation())}`;

const inviteEmail = document.getElementById('inviteEmail');
if (inviteEmail) {
  inviteEmail.addEventListener('click', (e) => {
    e.preventDefault();
    const subject = encodeURIComponent('You should see this — Coherent Champions of CHRIST');
    const body = encodeURIComponent(buildInvitation());
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
  });
}

const invitePreview = document.getElementById('invitePreview');
if (invitePreview) invitePreview.textContent = buildInvitation();

// --- Awareness Ladder ----------------------------------------------------
const LADDER_KEY = 'fpai-cockpit-ladder';
const LADDER_NOTES = [
  'Noise — scattered, unfiltered input. Most days start here.',
  'Distraction — pulled by competing inputs; intent fragmented.',
  'Attention — chosen focus. The first directed move.',
  'Zense — felt shift; the body recognizes it has been called back.',
  'Presence — undivided here-and-now. Reactive spirals stop.',
  'Coherence — alignment between thought, word, action.',
  'Flow — effortless engaged work; time dilates.',
  'Stillness — full coherence at rest. Rare. Earned.',
];
function setLadder(rung) {
  document.querySelectorAll('.rung').forEach((r, i) => {
    r.classList.toggle('active', i === rung);
    r.classList.toggle('passed', i < rung);
  });
  const note = document.getElementById('ladderNote');
  if (note) note.textContent = LADDER_NOTES[rung] || '';
  try { localStorage.setItem(LADDER_KEY, rung); } catch (e) {}
}
document.querySelectorAll('.rung').forEach((r, i) => {
  r.addEventListener('click', () => setLadder(i));
});
(function initLadder() {
  let saved = 2;
  try { saved = parseInt(localStorage.getItem(LADDER_KEY) || '2', 10); } catch (e) {}
  setLadder(isNaN(saved) ? 2 : saved);
})();

// --- 6 C's sliders -------------------------------------------------------
const CS_KEY = 'fpai-cockpit-cs';
function loadCs() {
  try { return JSON.parse(localStorage.getItem(CS_KEY) || '{}'); } catch (e) { return {}; }
}
function saveCs(state) {
  try { localStorage.setItem(CS_KEY, JSON.stringify(state)); } catch (e) {}
}
const csState = loadCs();
document.querySelectorAll('.c-slider').forEach(s => {
  const key = s.dataset.c;
  if (csState[key] !== undefined) s.value = csState[key];
  const valEl = document.querySelector(`.c-value[data-for="${key}"]`);
  if (valEl) valEl.textContent = s.value;
  s.addEventListener('input', () => {
    csState[key] = s.value;
    saveCs(csState);
    if (valEl) valEl.textContent = s.value;
  });
});

// --- Mode toggle ---------------------------------------------------------
const MODE_KEY = 'fpai-cockpit-mode';
const MODES = {
  founder: 'Founder cockpit · steward queue · adoption funnel · all metrics visible.',
  player: 'Reality is already a game. This is the guide for those who know.',
  field: 'The public aggregate · proof loops · champions roll · treasury growth.',
};

function setMode(mode) {
  if (!MODES[mode]) mode = 'founder';
  document.body.classList.remove('mode-founder', 'mode-player', 'mode-field');
  document.body.classList.add('mode-' + mode);
  document.querySelectorAll('.mode-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.mode === mode);
  });
  const sub = document.getElementById('modeSubtitle');
  if (sub) sub.textContent = MODES[mode];
  try { localStorage.setItem(MODE_KEY, mode); } catch (e) {}
}

document.querySelectorAll('.mode-btn').forEach(b => {
  b.addEventListener('click', () => setMode(b.dataset.mode));
});

(function initMode() {
  let saved = 'founder';
  try { saved = localStorage.getItem(MODE_KEY) || 'founder'; } catch (e) {}
  setMode(saved);
})();

// --- Auto-reload when the file regenerates -------------------------------
// The generator stamps data-generated on the freshness card. Poll the file
// itself every 15s; if its embedded timestamp has changed, reload.
const myGenerated = document.getElementById('freshness')?.dataset.generated;
const autoStatus = document.getElementById('autoStatus');

async function checkForUpdate() {
  if (!myGenerated || !autoStatus) return;
  try {
    const res = await fetch(location.href, { cache: 'no-store' });
    const text = await res.text();
    const m = text.match(/data-generated="([^"]+)"/);
    if (m && m[1] !== myGenerated) {
      autoStatus.textContent = 'newer file detected — reloading…';
      autoStatus.className = 'fresh-val stale';
      setTimeout(() => location.reload(), 600);
      return;
    }
    autoStatus.textContent = 'on (15s poll)';
    autoStatus.className = 'fresh-val on';
  } catch (e) {
    autoStatus.textContent = 'paused (' + (e.name || 'error') + ')';
    autoStatus.className = 'fresh-val';
  }
}
checkForUpdate();
setInterval(checkForUpdate, 15000);
"""


URL_RE = re.compile(r"https?://[^\s)<>\"]+")
BARE_DOMAIN_RE = re.compile(
    r"\b((?:[a-z0-9][a-z0-9-]*\.)+(?:com|ai|io|me|net|org|co|app|dev|sh)(?:/[^\s)<>\"]*)?)\b",
    re.IGNORECASE,
)


def _wrap(url: str, full: str | None = None) -> str:
    href = full or url
    if not href.startswith("http"):
        href = "https://" + href
    return f"<a class='link' href='{href}' target='_blank' rel='noopener'>{url}</a>"


def linkify(text: str) -> str:
    """Escape a cell's text and convert URLs / bare domains into clickable links."""
    safe = escape(text)
    # full URLs first (so we don't double-wrap their domain)
    safe = URL_RE.sub(lambda m: _wrap(m.group(0)), safe)
    # bare domains (skip anything already inside an <a ...>...</a>)
    parts = re.split(r"(<a\s[^>]*>.*?</a>)", safe)
    for i, p in enumerate(parts):
        if p.startswith("<a "):
            continue
        parts[i] = BARE_DOMAIN_RE.sub(lambda m: _wrap(m.group(0)), p)
    return "".join(parts)


def render_table(rows: list[list[str]]) -> str:
    if not rows:
        return "<p class='muted'>(none)</p>"
    head, *body = rows
    th = "".join(f"<th>{escape(c)}</th>" for c in head)
    trs = "".join(
        "<tr>" + "".join(f"<td>{linkify(c)}</td>" for c in r) + "</tr>"
        for r in body
    )
    return f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"


def _first_probable_url(text: str) -> str | None:
    """Extract the first URL or bare domain we can actually fetch."""
    m = URL_RE.search(text)
    if m:
        return m.group(0)
    m = BARE_DOMAIN_RE.search(text)
    if m:
        return "https://" + m.group(0)
    return None


TAG_COLORS = {
    "P1": "#ff6b6b",
    "P2": "#4ecdc4",
    "infra": "#7ec8e3",
    "cruft": "#5a6068",
    "unknown": "#b58be0",
}


def render_tag_donut(counts: dict[str, int], size: int = 140) -> str:
    """Inline SVG donut chart of service tag distribution."""
    total = sum(counts.values()) or 1
    cx = cy = size / 2
    r_outer = size / 2 - 4
    r_inner = r_outer * 0.55
    parts = [
        f"<svg viewBox='0 0 {size} {size}' width='{size}' height='{size}' "
        f"style='display:block'>"
    ]
    angle = -90  # start at top
    import math
    for tag in ("P1", "P2", "infra", "unknown", "cruft"):
        n = counts.get(tag, 0)
        if not n:
            continue
        sweep = 360 * n / total
        a1 = math.radians(angle)
        a2 = math.radians(angle + sweep)
        # large-arc flag if sweep > 180
        large = 1 if sweep > 180 else 0
        x1, y1 = cx + r_outer * math.cos(a1), cy + r_outer * math.sin(a1)
        x2, y2 = cx + r_outer * math.cos(a2), cy + r_outer * math.sin(a2)
        x3, y3 = cx + r_inner * math.cos(a2), cy + r_inner * math.sin(a2)
        x4, y4 = cx + r_inner * math.cos(a1), cy + r_inner * math.sin(a1)
        d = (
            f"M {x1:.2f} {y1:.2f} "
            f"A {r_outer} {r_outer} 0 {large} 1 {x2:.2f} {y2:.2f} "
            f"L {x3:.2f} {y3:.2f} "
            f"A {r_inner} {r_inner} 0 {large} 0 {x4:.2f} {y4:.2f} Z"
        )
        parts.append(
            f"<path d='{d}' fill='{TAG_COLORS[tag]}' opacity='0.92'>"
            f"<title>{tag}: {n} ({100*n/total:.0f}%)</title></path>"
        )
        angle += sweep
    parts.append(
        f"<text x='{cx}' y='{cy - 4}' text-anchor='middle' "
        f"font-size='20' font-weight='700' fill='var(--text)'>{total}</text>"
        f"<text x='{cx}' y='{cy + 14}' text-anchor='middle' "
        f"font-size='10' fill='var(--muted)'>services</text>"
    )
    parts.append("</svg>")
    return "".join(parts)


def render_money_bar(rows: list[list[str]]) -> str:
    """Stacked horizontal SVG bar of monthly burn breakdown."""
    if not rows or len(rows) < 2:
        return ""
    body = rows[1:]
    items: list[tuple[str, float]] = []
    total = 0.0
    for r in body:
        if not r or len(r) < 2:
            continue
        if "TOTAL" in r[0].upper():
            total = parse_money(r[1])
            continue
        v = parse_money(r[1])
        if v > 0:
            items.append((r[0], v))
    if not items:
        return ""
    if total <= 0:
        total = sum(v for _, v in items)
    items.sort(key=lambda x: -x[1])
    palette = ["#ff6b6b", "#f7b955", "#4ecdc4", "#7ec8e3", "#b58be0", "#a3e635", "#fb923c", "#5a6068"]
    parts = ["<div class='money-bar'><div class='bar-track'>"]
    legend = ["<div class='bar-legend'>"]
    for i, (label, v) in enumerate(items):
        pct = 100 * v / total
        color = palette[i % len(palette)]
        parts.append(
            f"<div class='bar-seg' style='width:{pct:.2f}%;background:{color};' "
            f"title='{escape(label)}: ${v:.2f} ({pct:.0f}%)'></div>"
        )
        legend.append(
            f"<span class='leg-item'><span class='leg-sw' style='background:{color}'></span>"
            f"{escape(label)} <span class='leg-pct'>${v:.0f} · {pct:.0f}%</span></span>"
        )
    parts.append("</div>")
    legend.append("</div>")
    parts.append(
        f"<div class='bar-total'>Total: <strong>${total:.2f}</strong>/mo</div>"
    )
    parts.extend(legend)
    parts.append("</div>")
    return "".join(parts)


def render_sparkline(series: list[tuple[str, int]], width: int = 360, height: int = 56) -> str:
    """SVG bar sparkline of commits/day for the past N days."""
    if not series:
        return ""
    n = len(series)
    max_v = max((v for _, v in series), default=1) or 1
    pad = 2
    bar_w = (width - pad * 2) / n
    parts = [
        f"<svg viewBox='0 0 {width} {height}' width='100%' height='{height}' "
        f"style='display:block'>"
    ]
    # baseline
    parts.append(
        f"<line x1='0' y1='{height - 1}' x2='{width}' y2='{height - 1}' "
        f"stroke='var(--border)' stroke-width='1'/>"
    )
    today = series[-1][0]
    for i, (d, v) in enumerate(series):
        x = pad + i * bar_w
        h = (height - 6) * (v / max_v) if v else 0
        y = height - 2 - h
        if v == 0:
            # tiny stub for visual rhythm even on empty days
            parts.append(
                f"<rect x='{x:.2f}' y='{height - 3}' width='{max(bar_w-1,1):.2f}' height='1.5' "
                f"fill='var(--border)'><title>{d}: 0</title></rect>"
            )
        else:
            color = "var(--accent)" if d != today else "var(--good)"
            parts.append(
                f"<rect x='{x:.2f}' y='{y:.2f}' width='{max(bar_w-1,1):.2f}' height='{h:.2f}' "
                f"fill='{color}' rx='1'><title>{d}: {v} commit{'s' if v != 1 else ''}</title></rect>"
            )
    parts.append("</svg>")
    return "".join(parts)


STATUS_DOT = {
    "active": ("#84d488", "Active"),
    "ratified-active": ("#84d488", "Ratified · Active"),
    "ratified": ("#84d488", "Ratified"),
    "proposed": ("#e8c479", "Proposed"),
    "repairing": ("#e8c479", "Repairing"),
    "repaired": ("#84d488", "Repaired"),
    "breached": ("#e58787", "Breached"),
    "superseded": ("#8fa1c2", "Superseded"),
    "withdrawn": ("#8fa1c2", "Withdrawn"),
    "archived": ("#5a6680", "Archived"),
}


def render_inline_doc_card(
    anchor: str,
    icon: str,
    title: str,
    subtitle: str,
    rel_path: str,
    summary: str,
) -> str:
    """Render a canonical doc as an expandable card with full inline content."""
    abs_path = ROOT / rel_path
    body_html = ""
    if abs_path.exists():
        try:
            md = abs_path.read_text(encoding="utf-8")
            md = strip_front_matter(md)
            # Strip the leading H1 since the card already has a title
            md = re.sub(r"^#\s+.+?\n", "", md, count=1)
            body_html = md_to_html(md)
        except Exception:
            body_html = "<p class='muted'>(could not render — file may be too large)</p>"
    else:
        body_html = "<p class='muted'>(file not found)</p>"
    abs_path_str = str(abs_path)
    return (
        f"<details class='inline-doc' id='doc-{anchor}'>"
        f"<summary class='inline-doc-summary'>"
        f"<span class='doc-icon'>{icon}</span>"
        f"<div class='doc-title-block'>"
        f"<div class='doc-title'>{escape(title)}</div>"
        f"<div class='doc-subtitle'>{escape(subtitle)}</div>"
        f"<div class='doc-summary'>{escape(summary)}</div>"
        f"</div>"
        f"<span class='doc-expand'>read inline →</span>"
        f"</summary>"
        f"<div class='inline-doc-body markdown-body'>"
        f"<p style='font-size:11px;color:var(--muted);margin:0 0 12px;'>"
        f"<a class='link' href='cursor://file{abs_path_str}'>open in editor</a> &middot; "
        f"<a class='link' href='file://{abs_path_str}' target='_blank'>raw file</a>"
        f"</p>"
        f"{body_html}"
        f"</div>"
        f"</details>"
    )


def render_agreements(reg: dict) -> str:
    agreements = reg.get("agreements", []) if isinstance(reg, dict) else []
    if not agreements:
        return (
            "<p class='muted'>No Agreements yet. See "
            "<a class='link' href='cursor://file" + str(INTENT_DIR / "FORMING_AGREEMENTS.md") + "'>"
            "FORMING_AGREEMENTS.md</a> for the protocol.</p>"
        )
    parts: list[str] = []
    for a in agreements:
        status = (a.get("status") or "").lower()
        color, label = STATUS_DOT.get(status, ("#8b949e", status or "—"))
        parties = a.get("parties", [])
        party_str = " ↔ ".join(p.get("name", "?") for p in parties[:2]) or "—"
        date = a.get("date_formed", "")
        context_full = a.get("context") or ""
        scope_tags = a.get("scope_tags", [])
        public = a.get("public", False)
        witness = a.get("witness", {}) or {}
        aid = a.get("agreement_id", "")
        file_path = agreement_file_path(aid)

        body_html = ""
        raw_path = ""
        if file_path and file_path.exists():
            try:
                full_md = file_path.read_text(encoding="utf-8")
                body_md = strip_front_matter(full_md)
                body_html = md_to_html(body_md)
                raw_path = str(file_path)
            except Exception:
                body_html = "<p class='muted'>(could not read file)</p>"
        else:
            body_html = "<p class='muted'>(file not found)</p>"

        meta_pills_html = "".join(
            f"<span class='christ-pill'>{escape(t)}</span>" for t in scope_tags
        )
        public_pill = (
            "<span class='christ-pill' style='border-color:var(--good);color:var(--good)'>public</span>"
            if public
            else "<span class='christ-pill' style='border-color:var(--muted);color:var(--muted)'>private</span>"
        )

        witness_html = ""
        if witness.get("type"):
            witness_html = f"witness: {escape(witness.get('type'))}"
            if witness.get("reference"):
                witness_html += f" <code>{escape(str(witness['reference']))}</code>"

        link_html = ""
        if raw_path:
            link_html = (
                f" &middot; <a class='link' href='cursor://file{escape(raw_path)}'>open in cursor</a>"
                f" &middot; <a class='link' href='file://{escape(raw_path)}' target='_blank'>raw file</a>"
            )

        parts.append(
            f"<details class='agreement'>"
            f"<summary class='agreement-summary'>"
            f"<span class='dot' style='background:{color};margin-right:8px;' title='{label}'></span>"
            f"<span class='ag-date'>{escape(date)}</span>"
            f"<span class='ag-parties'>{escape(party_str)}</span>"
            f"<span class='ag-status' style='color:{color}'>{escape(label)}</span>"
            f"<span class='ag-expand'>read &rarr;</span>"
            f"</summary>"
            f"<div class='agreement-meta'>"
            f"<p style='color:var(--muted);font-size:12px;margin:4px 0;'>{escape(context_full)}</p>"
            f"<div class='christ-row' style='margin-top:8px;'>{public_pill}{meta_pills_html}</div>"
            f"<p style='color:var(--muted);font-size:11px;margin:8px 0 0;'>{witness_html}{link_html}</p>"
            f"</div>"
            f"<div class='agreement-body markdown-body'>{body_html}</div>"
            f"</details>"
        )
    return "".join(parts)


def render_live_table(rows: list[list[str]]) -> str:
    """Live Now table with a probe-status dot prepended to each row.

    JS on page load fetches the row's URL (mode=no-cors, 5s timeout) and flips
    the dot green (reachable), red (failed), or gray (no probable URL).
    """
    if not rows:
        return "<p class='muted'>(none)</p>"
    head, *body = rows
    th = "<th></th>" + "".join(f"<th>{escape(c)}</th>" for c in head)
    trs_html = []
    for r in body:
        joined = " ".join(r)
        url = _first_probable_url(joined)
        attr = f" data-probe='{escape(url)}'" if url else ""
        cls = "probe" if url else "no-probe"
        cells = "".join(f"<td>{linkify(c)}</td>" for c in r)
        trs_html.append(
            f"<tr class='{cls}'{attr}>"
            f"<td><span class='dot live-status' title='not yet probed'></span></td>"
            f"{cells}</tr>"
        )
    trs = "".join(trs_html)
    return f"<table class='live-table'><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"


def render_services(catalog: dict, services: list[str]) -> str:
    tags = catalog.get("tags", {})
    role_meanings = catalog.get("_role_meanings", {})
    by_tag: dict[str, list[str]] = {"P1": [], "P2": [], "infra": [], "cruft": [], "unknown": []}
    for s in services:
        role = tags.get(s, "unknown")
        by_tag.setdefault(role, []).append(s)

    parts = []
    parts.append("<div class='toolbar'>")
    parts.append("<input id='svcSearch' class='search' placeholder='filter services...' />")
    parts.append("</div>")
    parts.append("<div class='toolbar'>")
    for t in ("P1", "P2", "infra", "cruft", "unknown"):
        parts.append(
            f"<span class='tag-pill active' data-tag='{t}'>{t} ({len(by_tag.get(t, []))})</span>"
        )
    parts.append("</div>")

    for tag in ("P1", "P2", "infra", "unknown", "cruft"):
        items = by_tag.get(tag, [])
        if not items:
            continue
        meaning = role_meanings.get(tag, "")
        opened = "open" if tag in ("P1", "P2", "infra") else ""
        parts.append(
            f"<details class='svc-group' data-tag='{tag}' {opened}>"
            f"<summary><span class='badge {tag}'>{tag}</span> "
            f"&nbsp;{len(items)} services &mdash; "
            f"<span style='color:var(--muted);font-weight:400;'>{escape(meaning)}</span></summary>"
            f"<div class='svc-grid'>"
        )
        for s in items:
            href = f"cursor://file{(SERVICES_DIR / s).resolve()}"
            cls = "svc" + (" untagged" if tag == "unknown" else "")
            parts.append(f"<a class='{cls}' href='{href}'>{escape(s)}</a>")
        parts.append("</div></details>")
    return "".join(parts)


def render_html() -> str:
    md = read_now()
    catalog = read_catalog()
    services = list_services()
    tags = catalog.get("tags", {})
    n_tagged = len(tags)
    n_total = len(services)
    n_untagged = sum(1 for s in services if s not in tags)

    money_rows = extract_money_table(md)
    inflow_rows = extract_inflow_table(md)
    live_rows = extract_live_now_table(md)
    rubric = extract_30day_rubric(md)
    decisions = extract_open_decisions(md)
    drift = extract_drift_bullets(md)
    commits = recent_commits(8)
    focus = extract_focus(md)

    # Derive total monthly from money table (last row often labeled TOTAL)
    total_mo = ""
    for row in money_rows[1:]:
        if row and "TOTAL" in row[0].upper():
            total_mo = row[1]
            break

    focus_html = ""
    if focus:
        # strip ## header line, keep rest as raw markdown-ish
        lines = focus.split("\n", 1)
        body = lines[1] if len(lines) > 1 else ""
        # crude markdown to html: bold + bullets + paragraphs
        body_html = body
        body_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body_html)
        body_html = re.sub(r"^- (.+)$", r"<li>\1</li>", body_html, flags=re.MULTILINE)
        body_html = re.sub(r"(?:<li>.*?</li>\n?)+", lambda m: "<ul>" + m.group(0) + "</ul>", body_html, flags=re.DOTALL)
        body_html = body_html.replace("\n\n", "</p><p>")
        focus_html = f"<p>{body_html}</p>"

    rubric_html = "".join(f"<li>{escape(r)}</li>" for r in rubric)
    decisions_html = "".join(f"<li>{escape(d)}</li>" for d in decisions)
    drift_html = "".join(
        f"<div class='drift'>{escape(d)}</div>" for d in drift[:8]
    )

    commits_html = "".join(
        f"<div class='commits'><span class='sha'>{escape(sha)}</span>{escape(msg)}</div>"
        for sha, msg in commits
    )

    services_html = render_services(catalog, services)

    # Agreements
    agreements_reg = read_agreements()
    agreements_html = render_agreements(agreements_reg)
    agreements_count = len(agreements_reg.get("agreements", [])) if isinstance(agreements_reg, dict) else 0
    agreements_active = sum(
        1 for a in agreements_reg.get("agreements", [])
        if (a.get("status") or "").lower() == "active"
    ) if isinstance(agreements_reg, dict) else 0
    agreements_ratified = 0  # held — neither ratified yet

    # Inline doc cards — read the canonical text right in the cockpit, no app required
    inline_docs_html = "".join([
        render_inline_doc_card(
            "manifesto", "✨", "Coherent Champions of CHRIST",
            "Manifesto v1.0 — the WHY",
            "core/INTENT/COHERENT_CHAMPIONS_MANIFESTO.md",
            "The founding document. CHRIST principles, the seven principles, the role of AI, the invitation."
        ),
        render_inline_doc_card(
            "framework", "🌍", "The Full Potential Framework",
            "Peace Coordination Civilization Stack — the WHAT",
            "core/INTENT/FULL_POTENTIAL_FRAMEWORK.md",
            "Eight layers: Org · Agreement · Game · AI · Treasury · Village · Cultural · Media. The complete stack."
        ),
        render_inline_doc_card(
            "positive-loop", "🔄", "The Positive Loop",
            "Party · Play · Apprentice · Build — the HOW IT GROWS",
            "core/INTENT/THE_POSITIVE_LOOP.md",
            "The flywheel: Party → Game → AI Apprentice → Build → more Party. Plus 7 System Areas and the Progression Path (Guest → Player → Apprentice → Steward → Builder)."
        ),
        render_inline_doc_card(
            "plays-itself", "🌀", "The Game Plays Itself",
            "The load-bearing principle of advancement",
            "core/INTENT/THE_GAME_PLAYS_ITSELF.md",
            "Identified by James 2026-05-07. The advancement test: every loop must make the Game more self-playing, not more founder-bottlenecked. Loop 6 is the threshold."
        ),
        render_inline_doc_card(
            "signaling", "📡", "The Practice of Signaling",
            "Frequency × Depth-of-meaning = momentum",
            "core/INTENT/THE_PRACTICE_OF_SIGNALING.md",
            "Identified by James after Loop 6. The substrate principle that propels the Game. Signals are first-class concerns — opt-in, deep, rhythmic, never coercive. Loop 7 ships the first primitives."
        ),
        render_inline_doc_card(
            "game", "🎮", "The Full Potential Game",
            "Player's Guide v1.3 — the player-facing OS",
            "core/INTENT/FULL_POTENTIAL_GAME.md",
            "Three Currencies, Sacred Trinity, 7-Day First Game, Awareness Ladder, Sunheart Rule, Quest Tiers."
        ),
        render_inline_doc_card(
            "treasury", "🏦", "The Remarkably Coherent Treasury",
            "v0.10 architectural spec — the economy",
            "core/INTENT/REMARKABLY_COHERENT_TREASURY.md",
            "Two-Economy Model · Three-Layer Architecture · Circulation Equity Formula · Verification Escrow."
        ),
        render_inline_doc_card(
            "wpap", "🕊", "World Peace Agreements Protocol",
            "WPAP — the AI substrate",
            "core/INTENT/WORLD_PEACE_AGREEMENTS_PROTOCOL.md",
            "Six AI modules: Agreement Builder · Memory · Translator · Mediator · Repair Guide · Cultural Translator."
        ),
        render_inline_doc_card(
            "agreement-template", "📜", "World Peace Agreement",
            "The signable template",
            "core/INTENT/WORLD_PEACE_AGREEMENT.md",
            "The 7 commitments. What every Coherent Champion signs."
        ),
        render_inline_doc_card(
            "forming", "✍️", "Forming Agreements",
            "Manual protocol",
            "core/INTENT/FORMING_AGREEMENTS.md",
            "Step-by-step for forming any specific Peace Agreement (the manual flow; WPAP §1 is AI-assisted)."
        ),
        render_inline_doc_card(
            "player-card", "🌱", "Player Card",
            "One-page fillable",
            "core/INTENT/FULL_POTENTIAL_GAME_PLAYER_CARD.md",
            "The fillable card for running your 7-Day First Game and logging your Proof."
        ),
        render_inline_doc_card(
            "agreement-builder", "🤖", "Agreement Builder Prompt",
            "AI-assisted Player Card",
            "core/INTENT/AGREEMENT_BUILDER_PROMPT.md",
            "Paste-into-Claude prompt that turns the AI into your 7-Day Game facilitator. Generates your Proof Log."
        ),
        render_inline_doc_card(
            "character-card", "🎴", "Character Quest",
            "Onboarding Quest #1 — your living node in the network",
            "core/INTENT/CHARACTER_CARD_QUEST.md",
            "Two layers (Aspirational + Reality), four visibility tiers, four levels of depth. Includes the AI Port-In Prompt — paste it into Claude/ChatGPT and your card drafts itself."
        ),
    ])

    # Founder metrics
    intent_docs = count_intent_docs()
    proofs_count = count_proofs()
    civ_milestones_7d = count_civ_quest_commits(7)
    civ_milestones_30d = count_civ_quest_commits(30)
    champions = read_champions()
    champions_total = len(champions)
    champions_public = sum(1 for c in champions if c.get("public"))
    champions_html = render_champions_list(champions)
    proofs = read_proofs()
    public_proofs = sum(1 for p in proofs if (p.get("consent") or "").lower() == "public")
    proofs_html = render_proofs_list(proofs)

    # tag counts for donut
    tag_counts: dict[str, int] = {"P1": 0, "P2": 0, "infra": 0, "cruft": 0, "unknown": 0}
    for s in services:
        role = catalog.get("tags", {}).get(s, "unknown")
        tag_counts[role] = tag_counts.get(role, 0) + 1
    donut_svg = render_tag_donut(tag_counts)
    donut_legend = "".join(
        f"<span class='leg-item'><span class='leg-sw' style='background:{TAG_COLORS[t]}'></span>"
        f"{t} <span class='leg-pct'>{tag_counts.get(t,0)}</span></span>"
        for t in ("P1", "P2", "infra", "unknown", "cruft") if tag_counts.get(t, 0)
    )

    money_bar_svg = render_money_bar(money_rows)

    sparkline_series = commits_by_day(30)
    sparkline_svg = render_sparkline(sparkline_series)
    n_active_days = sum(1 for _, v in sparkline_series if v > 0)
    n_total_commits = sum(v for _, v in sparkline_series)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    generated_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    commit_iso = last_commit_iso() or ""
    now_md_iso = file_mtime_iso(NOW) or ""
    catalog_iso = file_mtime_iso(CATALOG) or ""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Full Potential Game · Coherent Champions of CHRIST</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&display=swap" />
<meta name="description" content="A proof-based operating system for human potential. Sign the World Peace Agreement. Run your first 7-Day Game. We are Coherent Champions of CHRIST." />
<meta name="theme-color" content="#f7b955" />

<!-- Open Graph -->
<meta property="og:type" content="website" />
<meta property="og:title" content="Full Potential Game · Coherent Champions of CHRIST" />
<meta property="og:description" content="Reality is already a game. This is the guide for those who know. Sign the World Peace Agreement, run your first 7-Day proof loop. AI in service to life." />
<meta property="og:image" content="https://fullpotential.com/game/core/INTENT/assets/full-potential-framework-poster.png" />
<meta property="og:image:alt" content="The Full Potential Framework — A Peace Coordination Civilization Stack" />
<meta property="og:url" content="https://fullpotential.com/game/" />
<meta property="og:site_name" content="Full Potential" />

<!-- Twitter / X -->
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="Full Potential Game · Coherent Champions of CHRIST" />
<meta name="twitter:description" content="Reality is already a game. Sign the World Peace Agreement, run your first 7-Day proof loop. AI in service to life." />
<meta name="twitter:image" content="https://fullpotential.com/game/core/INTENT/assets/full-potential-framework-poster.png" />

<!-- Favicon (uses the manifesto poster scaled by browser) -->
<link rel="icon" type="image/png" href="core/INTENT/assets/coherent-champions-poster.png" />
<link rel="apple-touch-icon" href="core/INTENT/assets/coherent-champions-poster.png" />

<style>{CSS}</style>
</head>
<body>
<div class="horizon-glow"></div>
<div class="scroll-progress" id="scrollProgress"></div>
<div class="mobile-stage-bar" id="mobileStageBar" style="display:none;"></div>
<svg class="starfield" id="starfield" preserveAspectRatio="xMidYMid slice"></svg>

<div class="welcome-modal" id="welcomeModal">
  <div class="welcome-card">
    <div class="welcome-icon">✨</div>
    <h2 style="margin-top:0;color:var(--accent);">Welcome to the Full Potential Game</h2>
    <p style="font-size:14px;color:var(--text);line-height:1.6;">
      Reality is already a game. This is the guide for those who know.
    </p>
    <p style="font-size:13px;color:var(--muted);line-height:1.6;">
      A proof-based operating system for human potential. AI in service to life.
      Your first move: read the Manifesto, sign the World Peace Agreement, run your first 7-Day proof loop.
    </p>
    <div style="display:flex;gap:8px;margin-top:20px;justify-content:center;flex-wrap:wrap;">
      <button class="player-cta-primary" id="welcomeStart">📖 Read the Manifesto first</button>
      <button class="player-cta-secondary" id="welcomeSign">✍ Skip — go straight to Sign</button>
      <button class="player-cta-secondary" id="welcomeDismiss">I've been here before</button>
    </div>
    <p style="font-size:11px;color:var(--muted);margin-top:16px;">
      <em>"This is not a religion of superiority. It is a practice of becoming trustworthy with power."</em>
    </p>
  </div>
</div>

<nav class="toc-nav" id="tocNav" aria-label="Sections">
  <button class="toc-toggle" id="tocToggle" aria-label="Toggle navigation">⊞</button>
  <div class="toc-list" id="tocList"></div>
</nav>

<div class="wrap">
  <div class="header-row">
    <div>
      <h1>Full Potential <span class="brand-sub">· Coherent Champions of CHRIST</span><span id="greeting"></span></h1>
      <div class="header-sub" id="modeSubtitle">One Mission · One Agreement · One Game · One Treasury · One Human Family.</div>
    </div>
    <div class="mode-toggle" role="tablist" aria-label="View mode">
      <button class="mode-btn active" data-mode="founder" title="James's private operations + steward queue">⚓ Founder</button>
      <button class="mode-btn" data-mode="player" title="What a new player sees arriving">🌱 Player Entry</button>
      <button class="mode-btn" data-mode="field" title="Public aggregate view">🌍 Field</button>
    </div>
  </div>

  <div class="founder-only founder-profile">
    <div class="profile-row">
      <div class="profile-avatar">👁</div>
      <div class="profile-content">
        <div class="profile-role">FOUNDING STEWARD &middot; AUTHOR &middot; ARCHITECT</div>
        <div class="profile-name">James Sunheart</div>
        <div class="profile-quest">Civilization Quest tier &mdash; building the substrate so others can play</div>
        <div class="profile-rule">Sunheart Rule: <em>"Do only what you do better than AI. Everything else, the system handles."</em></div>
      </div>
      <div class="profile-stats">
        <div class="profile-stat">
          <div class="profile-stat-n">{intent_docs}</div>
          <div class="profile-stat-lbl">Founding documents</div>
        </div>
        <div class="profile-stat">
          <div class="profile-stat-n">{champions_total}</div>
          <div class="profile-stat-lbl">Champions signed (incl. you)</div>
        </div>
        <div class="profile-stat">
          <div class="profile-stat-n">{public_proofs}</div>
          <div class="profile-stat-lbl">Loops completed (yours)</div>
        </div>
      </div>
    </div>
    <div class="profile-roles">
      <div class="role-item"><strong>Founder of</strong> &mdash; World Peace Organization · CORA Nation · Zen Village · Full Potential AI · Coherence</div>
      <div class="role-item"><strong>Author of</strong> &mdash; Manifesto v1.0 · Ecosystem · Treasury v0.10 · Game v1.3 · WPAP · Forming Agreements · Cockpit</div>
      <div class="role-item"><strong>Holds</strong> &mdash; spiritual + doctrinal authority within CORA Nation · NOT fiduciary control over OneBPO (governance firewall, by design)</div>
      <div class="role-item"><strong>Body in the room when</strong> &mdash; ratification · ceremony · steward initiation · civilization-quest decisions</div>
    </div>
  </div>

  <div class="goal-card" id="goalCard">
    <div class="goal-header">
      <div class="goal-icon">🎯</div>
      <div class="goal-title-block">
        <div class="goal-label">FOUNDER GOAL · 30 DAYS</div>
        <div class="goal-title" id="goalTitle">First non-James human to engage with the Game.</div>
      </div>
      <div class="goal-progress">
        <div class="goal-progress-n" id="goalProgressN">—</div>
        <div class="goal-progress-lbl" id="goalProgressLbl">Champions</div>
      </div>
    </div>
    <p class="goal-blurb" id="goalBlurb">
      The substrate is built — 22+ loops, 10+ Paradigm Shifts, full funnel from Sign → Character → Proof → Affiliate → Path.
      What's missing is one other human in it. Sign / file a proof / express interest in any path — you become the proof that the Game is more than its founder.
    </p>
    <div class="goal-meta">
      <span class="goal-meta-item">Decision filter: <strong>proof · revenue · clarity · ease</strong> in 30 days</span>
      <span class="goal-meta-sep">·</span>
      <span class="goal-meta-item">AI working goals: <a href="https://github.com/jamessunheart/FPAI_Cockpit/blob/main/core/STATE/AI_GOALS.md" target="_blank" rel="noopener">core/STATE/AI_GOALS.md</a></span>
    </div>
  </div>

  <div class="game-state-card" id="gameStateCard">
    <div class="gs-header">
      <div class="gs-label">⚡ FIELD STATE</div>
      <div class="gs-tagline" id="gsTagline">A proof-based operating system for human potential.</div>
    </div>
    <div class="gs-metrics" id="gsMetrics">
      <div class="gs-metric"><div class="gs-icon">🌀</div><div class="gs-n" id="gsChampions">—</div><div class="gs-lbl">Champions</div></div>
      <div class="gs-metric"><div class="gs-icon">🎴</div><div class="gs-n" id="gsCards">—</div><div class="gs-lbl">Characters built</div></div>
      <div class="gs-metric"><div class="gs-icon">🌱</div><div class="gs-n" id="gsProofs">—</div><div class="gs-lbl">Proofs filed</div></div>
      <div class="gs-metric"><div class="gs-icon">🤝</div><div class="gs-n" id="gsAffiliates">—</div><div class="gs-lbl">Affiliate links</div></div>
      <div class="gs-metric gs-metric-accent"><div class="gs-icon">📊</div><div class="gs-n" id="gsScore">—</div><div class="gs-lbl">Field Score sum</div></div>
      <div class="gs-metric"><div class="gs-icon">📈</div><div class="gs-n" id="gsGrowth">—</div><div class="gs-lbl">This week</div></div>
    </div>
  </div>

  <div class="inviter-banner" id="inviterBanner" style="display:none;">
    <span class="inv-icon">🤝</span>
    <span id="inviterText">You arrived through someone's invitation.</span>
  </div>

  <div class="identity-prompt" id="identityPrompt">
    <div class="ip-icon">🎮</div>
    <div class="ip-content">
      <div class="ip-label">ALREADY A COHERENT CHAMPION?</div>
      <div class="ip-text">Tell us who you are to see your Player State, progression, and unique invite link.</div>
      <div class="ip-row">
        <input type="text" id="ipName" placeholder="Your name (must match the Champions Roll)" />
        <button id="ipSubmit" class="player-cta-secondary">Look me up →</button>
      </div>
      <div class="ip-error" id="ipError" style="display:none;"></div>
    </div>
  </div>

  <div class="player-state" id="playerStateCard" style="display:none;">
    <div class="ps-header">
      <div class="ps-icon">🎮</div>
      <div>
        <div class="ps-label">YOUR PLAYER STATE</div>
        <div class="ps-name" id="psName">—</div>
        <div class="ps-stage" id="psStage"></div>
      </div>
      <div class="ps-score">
        <div class="ps-score-n" id="psScore">0</div>
        <div class="ps-score-lbl">Field Score</div>
      </div>
    </div>
    <div class="ps-stats" id="psStats">
      <div class="ps-stat"><div class="ps-stat-n" id="psChampNum">—</div><div class="ps-stat-lbl">Champion #</div></div>
      <div class="ps-stat"><div class="ps-stat-n" id="psLoops">0</div><div class="ps-stat-lbl">Loops filed</div></div>
      <div class="ps-stat"><div class="ps-stat-n" id="psAffiliates">0</div><div class="ps-stat-lbl">Affiliates signed</div></div>
      <div class="ps-stat"><div class="ps-stat-n" id="psCard">—</div><div class="ps-stat-lbl">Character</div></div>
    </div>

    <div class="progression-bar" id="progressionBar">
      <div class="pb-rail">
        <div class="pb-fill" id="pbFill" style="width:0%;"></div>
      </div>
      <div class="pb-stages">
        <div class="pb-stage" data-stage="0"><div class="pbs-glyph">👋</div><div class="pbs-name">Visitor</div></div>
        <div class="pb-stage" data-stage="1"><div class="pbs-glyph">👥</div><div class="pbs-name">Guest</div></div>
        <div class="pb-stage" data-stage="2"><div class="pbs-glyph">🎮</div><div class="pbs-name">Player</div></div>
        <div class="pb-stage" data-stage="3"><div class="pbs-glyph">🎓</div><div class="pbs-name">Apprentice</div></div>
        <div class="pb-stage" data-stage="4"><div class="pbs-glyph">🌱</div><div class="pbs-name">Steward</div></div>
        <div class="pb-stage" data-stage="5"><div class="pbs-glyph">🏗</div><div class="pbs-name">Builder</div></div>
        <div class="pb-stage" data-stage="6"><div class="pbs-glyph">👑</div><div class="pbs-name">Legend</div></div>
      </div>
      <div class="pb-unlock" id="pbUnlock"></div>
    </div>
    <div class="ps-invite">
      <div class="ps-invite-label">YOUR INVITE LINK <span style="color:var(--muted);font-weight:400;font-size:11px;">— share this URL · when others sign through it, your Field Score grows</span></div>
      <div class="ps-invite-row">
        <code class="ps-invite-url" id="psInviteUrl">https://fullpotential.com/game?inviter=...</code>
        <button class="player-cta-secondary" id="psCopyInviteBtn" style="font-size:12px;padding:8px 14px;">📋 Copy</button>
      </div>
    </div>
    <p class="ps-tip" id="psTip"></p>
    <div class="ps-match-row">
      <button class="ps-match-btn" id="psMatchBtn">🎯 What's my next move?</button>
      <span class="ps-match-hint">(same as <code>/match</code> on @sunheartbrain_bot)</span>
    </div>
    <div class="ps-match-result" id="psMatchResult" style="display:none;"></div>
    <div class="ps-contrib" id="psContrib" style="display:none;">
      <div class="ps-contrib-label">YOUR CONTRIBUTIONS</div>
      <div class="ps-contrib-row" id="psContribRow"></div>
    </div>
  </div>

  <div class="paths-card" id="pathsCard" style="display:none;">
    <div class="paths-header">
      <div class="paths-icon">🌟</div>
      <div class="paths-title-block">
        <div class="paths-label">PATHS INTO THE GAME</div>
        <div class="paths-title">One Game. Many ways in.</div>
      </div>
    </div>
    <p class="paths-blurb">
      The Game opens many doors. Retreats are one. Apprenticeship, village living, parties &amp; gatherings, commerce, coaching, witnessing — each a real way to participate. The Game is the substrate; these are the practices that grow on it.
    </p>
    <div class="paths-grid">
      <a class="path-tile path-live" href="#retreatCard">
        <div class="path-glyph">🌴</div>
        <div class="path-name">Retreat</div>
        <div class="path-desc">First Costa Rica gathering. Express interest below.</div>
        <div class="path-status path-status-live">🟢 Open</div>
      </a>
      <div class="path-tile">
        <div class="path-glyph">🎓</div>
        <div class="path-name">Apprenticeship</div>
        <div class="path-desc">Learn the substrate by building loops alongside a mentor Champion.</div>
        <div class="path-status path-status-soon">🟡 Forming</div>
      </div>
      <div class="path-tile">
        <div class="path-glyph">🏡</div>
        <div class="path-name">Village living</div>
        <div class="path-desc">In-person presence in Zen Village — short stays, work-trades, residency.</div>
        <div class="path-status path-status-soon">🟡 Forming</div>
      </div>
      <div class="path-tile">
        <div class="path-glyph">🎉</div>
        <div class="path-name">Parties &amp; jams</div>
        <div class="path-desc">Music + problem jams. Couch = Oracle Stage. Local + traveling.</div>
        <div class="path-status path-status-soon">🟡 Forming</div>
      </div>
      <div class="path-tile">
        <div class="path-glyph">🛒</div>
        <div class="path-name">Commerce</div>
        <div class="path-desc">Coherent Credits, store, products + services in the substrate.</div>
        <div class="path-status path-status-watch">⚪ Concept</div>
      </div>
      <div class="path-tile">
        <div class="path-glyph">🧭</div>
        <div class="path-name">Coaching</div>
        <div class="path-desc">Champions guiding Champions through the Player Path.</div>
        <div class="path-status path-status-soon">🟡 Forming</div>
      </div>
      <div class="path-tile">
        <div class="path-glyph">👁</div>
        <div class="path-name">Witnessing</div>
        <div class="path-desc">Witness Roster — non-Claude humans signing as proof witnesses.</div>
        <div class="path-status path-status-watch">⚪ Concept</div>
      </div>
    </div>
  </div>

  <div class="retreat-card" id="retreatCard" style="display:none;">
    <div class="retreat-header">
      <div class="retreat-icon">🌴</div>
      <div class="retreat-title-block">
        <div class="retreat-label">FIRST RETREAT — COSTA RICA</div>
        <div class="retreat-title">One way the Game lands in person.</div>
      </div>
      <div class="retreat-counter">
        <div class="retreat-counter-n" id="retreatCount">—</div>
        <div class="retreat-counter-lbl">interested</div>
      </div>
    </div>
    <p class="retreat-blurb">
      One of several paths into the Game (see Paths overview above). For Champions whose calling is in-person presence — signed, built, witnessed — the first Costa Rica retreat is being shaped from the substrate raising its hand.
      No date locked yet. No payment yet.
    </p>
    <div class="retreat-form" id="retreatForm">
      <label class="retreat-field">
        <span>Preferred dates / window</span>
        <input type="text" id="rtDates" placeholder="e.g. Jan 2027, Q1 2027, anytime" />
      </label>
      <label class="retreat-field">
        <span>What you'd contribute</span>
        <textarea id="rtContrib" rows="2" placeholder="A practice, a session, a meal, presence, music…"></textarea>
      </label>
      <label class="retreat-field">
        <span>What would make this retreat irresistible to you?</span>
        <textarea id="rtWhy" rows="2" placeholder="What you most need, what you most want to find here…"></textarea>
      </label>
      <div class="retreat-actions">
        <label class="retreat-checkbox">
          <input type="checkbox" id="rtPublic" checked />
          <span>List me publicly on the interest roll</span>
        </label>
        <button class="retreat-submit" id="rtSubmit">🌴 I'm interested →</button>
      </div>
      <div class="retreat-msg" id="retreatMsg" style="display:none;"></div>
      <input type="text" id="rtCompany" name="company" tabindex="-1" autocomplete="off" style="position:absolute;left:-9999px;" aria-hidden="true" />
    </div>
  </div>

  <div class="next-move" id="nextMove">
    <div class="nm-icon">⟶</div>
    <div class="nm-text">
      <div class="nm-label">YOUR NEXT MOVE</div>
      <div class="nm-action" id="nmAction">Read the Manifesto.</div>
    </div>
    <a class="nm-cta" id="nmCta" href="cursor://file{INTENT_DIR}/COHERENT_CHAMPIONS_MANIFESTO.md">Open →</a>
  </div>

  <div class="founder-only funnel-card">
    <h2>Adoption Funnel <span style="font-size:12px;font-weight:400;color:var(--muted);">&mdash; how many at each stage</span></h2>
    <p style="color:var(--muted);font-size:12px;margin:0 0 12px;">
      The conversion sequence: stranger → reader → signer → player → witness → steward. Numbers populate as adoption begins.
    </p>
    <div class="funnel">
      <div class="funnel-step funnel-step-active">
        <div class="funnel-num">∞</div>
        <div class="funnel-label">Visitors</div>
        <div class="funnel-sub">Anyone who landed here</div>
      </div>
      <div class="funnel-arrow">↓</div>
      <div class="funnel-step funnel-step-active">
        <div class="funnel-num">—</div>
        <div class="funnel-label">Readers</div>
        <div class="funnel-sub">Opened the Manifesto</div>
      </div>
      <div class="funnel-arrow">↓</div>
      <div class="funnel-step{' funnel-step-active' if champions_total > 0 else ''}">
        <div class="funnel-num">{champions_total}</div>
        <div class="funnel-label">Coherent Champions</div>
        <div class="funnel-sub">Signed the World Peace Agreement</div>
      </div>
      <div class="funnel-arrow">↓</div>
      <div class="funnel-step{' funnel-step-active' if public_proofs > 0 else ''}">
        <div class="funnel-num">{public_proofs}</div>
        <div class="funnel-label">Players</div>
        <div class="funnel-sub">Started a 7-Day First Game</div>
      </div>
      <div class="funnel-arrow">↓</div>
      <div class="funnel-step{' funnel-step-active' if public_proofs > 0 else ''}">
        <div class="funnel-num">{public_proofs}</div>
        <div class="funnel-label">Witnesses</div>
        <div class="funnel-sub">Signed behind another's proof</div>
      </div>
      <div class="funnel-arrow">↓</div>
      <div class="funnel-step funnel-step-active">
        <div class="funnel-num">1</div>
        <div class="funnel-label">Stewards</div>
        <div class="funnel-sub">CORA Nation covenant stewards</div>
      </div>
    </div>
    <p style="color:var(--muted);font-size:11px;margin:12px 0 0;">
      {champions_total} champion(s) · {public_proofs} public proof loop(s) · 1 founder-steward.
      The roll is open.
    </p>
  </div>

  <div class="onboarding-card">
    <h2>The Onboarding Journey <span style="font-size:12px;font-weight:400;color:var(--muted);">&mdash; from stranger to Coherent Champion to Player</span></h2>
    <p style="color:var(--muted);font-size:12px;margin:0 0 12px;">
      Five steps. Click each as you complete it; progress saves locally. The path: <strong>read → sign → play → witness → invite</strong>.
    </p>
    <div class="onboard-steps" id="onboardSteps">
      <label class="onboard-step" data-step="read">
        <input type="checkbox" data-step-key="read" />
        <div class="step-num">1</div>
        <div class="step-content">
          <div class="step-title">Read the Manifesto</div>
          <div class="step-desc">5 minutes. The CHRIST principles, the role of AI, the invitation. <a class='link' href='cursor://file{INTENT_DIR}/COHERENT_CHAMPIONS_MANIFESTO.md'>Open Manifesto</a></div>
        </div>
      </label>
      <label class="onboard-step" data-step="sign">
        <input type="checkbox" data-step-key="sign" />
        <div class="step-num">2</div>
        <div class="step-content">
          <div class="step-title">Sign the World Peace Agreement</div>
          <div class="step-desc">1 minute. Signing makes you a Coherent Champion. Use the form below — generates your signed file.</div>
        </div>
      </label>
      <label class="onboard-step" data-step="play">
        <input type="checkbox" data-step-key="play" />
        <div class="step-num">3</div>
        <div class="step-content">
          <div class="step-title">Run your 7-Day First Game</div>
          <div class="step-desc">7 days. Choose a transformation, deliver, witness, log. <a class='link' href='cursor://file{INTENT_DIR}/AGREEMENT_BUILDER_PROMPT.md'>AI-Assisted Player Card prompt</a></div>
        </div>
      </label>
      <label class="onboard-step" data-step="witness">
        <input type="checkbox" data-step-key="witness" />
        <div class="step-num">4</div>
        <div class="step-content">
          <div class="step-title">Get one witness signature</div>
          <div class="step-desc">A witness who can stand behind your proof. Distance-Weighted (different team / no dependency / outside your social graph).</div>
        </div>
      </label>
      <label class="onboard-step" data-step="invite">
        <input type="checkbox" data-step-key="invite" />
        <div class="step-num">5</div>
        <div class="step-content">
          <div class="step-title">Bring one aligned person</div>
          <div class="step-desc">The Game spreads through resonance, not recruitment. Who do you know who's tired of chaos? Use the invitation card below.</div>
        </div>
      </label>
    </div>
  </div>

  <div class="sign-card" id="signCard">
    <h2>Sign the World Peace Agreement</h2>
    <p style="color:var(--muted);font-size:12px;margin:0 0 12px;">
      Adopting the values of the Manifesto. Signing makes you a Coherent Champion of CHRIST.
      The act is real; the form just records it.
    </p>
    <blockquote style="background:rgba(132, 212, 136,0.06);border-left:3px solid var(--good);padding:10px 14px;margin:0 0 16px;font-size:13px;font-style:italic;">
      I agree to practice peace in thought, word, and action.
      I agree to reduce unnecessary suffering.
      I agree to seek understanding before hatred.
      I agree to repair where I have caused harm.
      I agree to protect life, truth, beauty, and future generations.
      I agree to become trustworthy with intelligence, influence, and resources.
      I agree that peace must become visible through action.
      <br><br>
      <em>Signed not in perfection, but in sincere participation.</em>
    </blockquote>
    <div class="sign-form">
      <label style="grid-column:1/-1;"><span>Your name</span><input type="text" id="signName" placeholder="e.g. Maria Lopez" /></label>
    </div>
    <details class="sign-extras">
      <summary class="sign-extras-summary">+ Add witness, why, handle, email, visibility (optional)</summary>
      <div class="sign-form" style="margin-top:10px;">
        <label><span>Handle (optional)</span><input type="text" id="signHandle" placeholder="@yourhandle" /></label>
        <label><span>Email (optional)</span><input type="email" id="signEmail" placeholder="you@example.com" /></label>
        <label><span>Witness (optional)</span><input type="text" id="signWitness" placeholder="someone who saw you sign" /></label>
        <label style="grid-column:1/-1;"><span>One sentence — why are you signing?</span><textarea id="signWhy" rows="2" placeholder="optional"></textarea></label>
        <label class="sign-radio">
          <input type="radio" name="signPublic" value="true" checked /> Public (appear on the Champions Roll)
        </label>
        <label class="sign-radio">
          <input type="radio" name="signPublic" value="false" /> Private (signed; not publicly listed)
        </label>
      </div>
    </details>
    <!-- honeypot: hidden field bots fill -->
    <input type="text" id="signHoneypot" name="company" style="position:absolute;left:-9999px;" tabindex="-1" autocomplete="off" />
    <div class="sign-actions">
      <button id="signSubmitBtn" class="player-cta-primary">🌀 Sign &amp; join the Roll</button>
      <button id="signCopyBtn" class="player-cta-secondary">📋 Copy</button>
      <button id="signDownloadBtn" class="player-cta-secondary">⬇ Download</button>
      <a id="signEmailBtn" class="player-cta-secondary" href="#">✉ Email</a>
    </div>
    <p style="color:var(--muted);font-size:11px;margin:12px 0 0;">
      <strong>Sign &amp; join the Roll</strong> submits directly to the substrate — your name appears on the Champions Roll within seconds. The Game plays itself.
      Backup options: copy / download / email.
    </p>
  </div>

  <div class="connector">
    <span class="conn-arrow">↓</span>
    <span class="conn-text">After signing → your Champion # is assigned and the next steps unlock. Here's the path.</span>
  </div>

  <div class="after-sign-card">
    <h2>What happens after you sign? <span style="font-size:12px;font-weight:400;color:var(--muted);">&mdash; the path forward</span></h2>
    <div class="after-sign-grid">
      <div class="after-step">
        <div class="after-step-num">①</div>
        <div class="after-step-content">
          <div class="after-step-title">Your file lands in the Champions Roll</div>
          <div class="after-step-desc">You email or download the .md → it goes into <code>core/INTENT/AGREEMENTS/champions/</code> → next refresh, your name appears here. Public if you consented.</div>
        </div>
      </div>
      <div class="after-step">
        <div class="after-step-num">②</div>
        <div class="after-step-content">
          <div class="after-step-title">You run your 7-Day First Game</div>
          <div class="after-step-desc">Choose a transformation you can genuinely help one person achieve in 7 days. Open the AI-Assisted Player Card prompt — Claude facilitates the loop with you.</div>
        </div>
      </div>
      <div class="after-step">
        <div class="after-step-num">③</div>
        <div class="after-step-content">
          <div class="after-step-title">A witness signs your proof</div>
          <div class="after-step-desc">Someone outside your immediate circle (per Distance-Weighted Witness, Treasury §7) confirms what they saw. Your first proof becomes part of the public field.</div>
        </div>
      </div>
      <div class="after-step">
        <div class="after-step-num">④</div>
        <div class="after-step-content">
          <div class="after-step-title">You bring one aligned person</div>
          <div class="after-step-desc">Not recruitment — invitation. Someone tired of chaos who's already living something close to this. They run their first loop. The field grows by resonance.</div>
        </div>
      </div>
      <div class="after-step">
        <div class="after-step-num">⑤</div>
        <div class="after-step-content">
          <div class="after-step-title">You ascend the Player Path</div>
          <div class="after-step-desc">Villager → Contributor → Builder → Steward → Guardian → Legend. The stage picks you, not the other way around. Field response confirms readiness.</div>
        </div>
      </div>
    </div>
    <p style="color:var(--muted);font-size:11px;margin:14px 0 0;text-align:center;">
      <em>"This is not a religion of superiority. It is a practice of becoming trustworthy with power."</em>
    </p>
  </div>

  <div class="connector">
    <span class="conn-arrow">↓</span>
    <span class="conn-text">Your Character is your matchable node. Without it, players can't find each other for collaborations and quests.</span>
  </div>

  <div class="character-card-quest" id="characterCardQuest">
    <h2>🎴 Character Quest <span style="font-size:12px;font-weight:400;color:var(--muted);">&mdash; Quest #1 · Onboarding · 5 minutes</span></h2>
    <p style="color:var(--muted);font-size:13px;margin:0 0 12px;line-height:1.6;">
      Your <strong>Character</strong> is your living node in the Game's network. Two layers, four visibility tiers, four levels of depth.
      Sign-up is 5 minutes. Your AI fills the draft. You refine. Your witnesses keep it honest with reality.
    </p>

    <div class="card-tiers">
      <div class="card-tier"><div class="ct-icon">🌐</div><div class="ct-label">Public</div><div class="ct-sub">syndicates to social</div></div>
      <div class="card-tier"><div class="ct-icon">👥</div><div class="ct-label">Player</div><div class="ct-sub">other players see</div></div>
      <div class="card-tier"><div class="ct-icon">🤍</div><div class="ct-label">Inner Circle</div><div class="ct-sub">your Witness Roster</div></div>
      <div class="card-tier"><div class="ct-icon">🔒</div><div class="ct-label">Sacred</div><div class="ct-sub">you + your AI only</div></div>
    </div>

    <div class="card-levels">
      <div class="card-level"><span class="cl-num">🟢 L1</span><span class="cl-name">Signup</span><span class="cl-detail">5 min · card goes live</span></div>
      <div class="card-level"><span class="cl-num">🟡 L2</span><span class="cl-name">Player</span><span class="cl-detail">15 min · matchable</span></div>
      <div class="card-level"><span class="cl-num">🔵 L3</span><span class="cl-name">Matching</span><span class="cl-detail">30 min · team-formable</span></div>
      <div class="card-level"><span class="cl-num">🟣 L4</span><span class="cl-name">Living</span><span class="cl-detail">ongoing · AI-maintained</span></div>
    </div>

    <h3 style="margin-top:18px;">Step 1 · Get your AI Port-In prompt</h3>
    <p style="color:var(--muted);font-size:12px;margin:0 0 8px;">
      Copy the prompt, paste it into Claude / ChatGPT / Gemini / your AI. Your AI drafts your Character from what it already knows about you. Honest about gaps (writes <code>[NEEDS INPUT]</code> rather than fabricating).
    </p>
    <div class="sign-actions" style="margin-bottom:12px;">
      <button id="cardCopyPromptBtn" class="player-cta-primary">📋 Copy AI Port-In Prompt</button>
      <a class="player-cta-secondary" href="https://claude.ai/new" target="_blank">🤖 Open Claude.ai (then paste)</a>
      <a class="player-cta-secondary" href="#doc-character-card" onclick="document.querySelector('.canonical-library-wrapper').open=true;document.getElementById('doc-character-card').open=true;">Read full Quest doc</a>
    </div>

    <h3>Step 2 · Submit your draft</h3>
    <p style="color:var(--muted);font-size:12px;margin:0 0 8px;">
      Refine your AI's draft. Paste the final markdown below and submit. Your card joins the substrate at the visibility tier you choose.
    </p>
    <div class="sign-form">
      <label><span>Your name (or chosen name)</span><input type="text" id="cardPlayer" placeholder="e.g. Maria Lopez or @maria" /></label>
      <label><span>Handle (optional)</span><input type="text" id="cardHandle" placeholder="@yourhandle" /></label>
      <label><span>Email (optional · private)</span><input type="email" id="cardEmail" placeholder="you@example.com" /></label>
      <label>
        <span>Level</span>
        <select id="cardLevel" style="background:var(--bg);border:1px solid var(--border);border-radius:4px;padding:8px 10px;color:var(--text);font-size:13px;font-family:inherit;">
          <option value="L1">🟢 L1 Signup (5 min · card goes live)</option>
          <option value="L2">🟡 L2 Player (15 min · matchable)</option>
          <option value="L3">🔵 L3 Matching (30 min · team-formable)</option>
          <option value="L4">🟣 L4 Living (ongoing)</option>
        </select>
      </label>
      <label>
        <span>Default visibility</span>
        <select id="cardVisibility" style="background:var(--bg);border:1px solid var(--border);border-radius:4px;padding:8px 10px;color:var(--text);font-size:13px;font-family:inherit;">
          <option value="player">👥 Player — visible to other players (default)</option>
          <option value="public">🌐 Public — syndicates to social</option>
          <option value="inner">🤍 Inner Circle — Witness Roster only</option>
          <option value="sacred">🔒 Sacred — me + my AI only</option>
        </select>
      </label>
      <label style="grid-column:1/-1;"><span>Your Card Markdown — paste full output from your AI</span><textarea id="cardMarkdown" rows="12" placeholder="# Your Name — Character

## ✦ ASPIRATIONAL

### 🌐 🟢 Public Bio
...

(paste your AI's draft here, refined to taste)"></textarea></label>
    </div>
    <input type="text" id="cardHoneypot" name="company" style="position:absolute;left:-9999px;" tabindex="-1" autocomplete="off" />
    <div class="sign-actions" style="margin-top:8px;">
      <button id="cardSubmitBtn" class="player-cta-primary">🎴 Submit my Character</button>
    </div>
    <p style="color:var(--muted);font-size:11px;margin:12px 0 0;">
      Your card becomes a node in the Game's network. Other Players matchable on offers / needs / quests.
      You can update your card anytime — submit again with the same name. The fields the founder said: amendable / reversible.
    </p>
  </div>

  <div class="connector">
    <span class="conn-arrow">↓</span>
    <span class="conn-text">Run a 7-Day First Game (use the AI-Assisted Player Card prompt above). When complete and witnessed, file your Proof here.</span>
  </div>

  <div class="proof-submit-card" id="proofSubmitCard">
    <h2>🌱 File a Proof Loop <span style="font-size:12px;font-weight:400;color:var(--muted);">&mdash; for Champions who completed a 7-Day Game</span></h2>
    <p style="color:var(--muted);font-size:12px;margin:0 0 14px;">
      You completed a proof loop. A witness saw it. Submit it to the substrate.
      Public proofs appear on the live Field Pulse and the Public Proofs roll.
    </p>
    <div class="sign-form">
      <label><span>Your name (or handle)</span><input type="text" id="prfPlayer" placeholder="e.g. Maria Lopez or @maria" /></label>
      <label><span>Loop number</span><input type="number" id="prfLoop" min="1" placeholder="e.g. 1" /></label>
      <label style="grid-column:1/-1;"><span>Quest — the transformation you set out to deliver</span><input type="text" id="prfQuest" placeholder="One sentence." /></label>
      <label style="grid-column:1/-1;"><span>Output — what was completed</span><textarea id="prfOutput" rows="3" placeholder="Concrete description of what shipped, was delivered, or was witnessed."></textarea></label>
      <label style="grid-column:1/-1;"><span>Result — what changed (optional)</span><textarea id="prfResult" rows="2" placeholder="The transformation that occurred. What is true now that wasn't before."></textarea></label>
      <label><span>Witness (name or @)</span><input type="text" id="prfWitness" placeholder="Who saw it" /></label>
      <label><span>Email (optional, private)</span><input type="email" id="prfEmail" placeholder="you@example.com" /></label>
      <label class="sign-radio"><input type="radio" name="prfConsent" value="public" checked /> Public — visible on Field Pulse + Public Proofs</label>
      <label class="sign-radio"><input type="radio" name="prfConsent" value="anonymized" /> Anonymized — referenceable, name not shown</label>
      <label class="sign-radio"><input type="radio" name="prfConsent" value="private" /> Private — your ledger only</label>
    </div>
    <input type="text" id="prfHoneypot" name="company" style="position:absolute;left:-9999px;" tabindex="-1" autocomplete="off" />
    <div class="sign-actions" style="margin-top:8px;">
      <button id="prfSubmitBtn" class="player-cta-primary">🌱 File the proof</button>
    </div>
    <p style="color:var(--muted);font-size:11px;margin:12px 0 0;">
      Per <em>The Practice of Signaling</em>: <strong>each filed proof becomes a Field → Field signal</strong>, strengthening the next Player's confidence that the Game is real and being played.
    </p>
  </div>

  <div class="champions-card">
    <h2>Champions Roll <span style="font-size:12px;font-weight:400;color:var(--muted);">&mdash; {champions_total} signed · {champions_public} public</span></h2>
    <p style="color:var(--muted);font-size:12px;margin:0 0 12px;">
      Public roll of Coherent Champions. Private signers exist but are not listed by their consent.
    </p>
    {champions_html}
    {('<h3 style="margin-top:20px;">Public Proof Loops</h3>' + proofs_html) if public_proofs > 0 else ''}
    <div class="retreat-roll" id="retreatRoll" style="display:none;">
      <h3 style="margin-top:20px;">🌴 Retreat Interest Roll <span style="font-size:12px;font-weight:400;color:var(--muted);">&mdash; <span id="retreatRollCount">0</span> Champions raised their hand</span></h3>
      <p style="color:var(--muted);font-size:12px;margin:0 0 12px;">Champions who've expressed public interest in the first Costa Rica retreat. Private interests exist but are not listed by their consent.</p>
      <div class="champions-list" id="retreatRollList"></div>
    </div>
  </div>

  <div class="connector">
    <span class="conn-arrow">↓</span>
    <span class="conn-text">Each Champion gets a unique invite URL. When others sign through your link, they're credited as your affiliates and your Field Score grows.</span>
  </div>

  <div class="invite-card">
    <h2>Bring a Friend <span style="font-size:12px;font-weight:400;color:var(--muted);">&mdash; the Game spreads by resonance · +3 score per signed affiliate</span></h2>
    <p style="color:var(--muted);font-size:12px;margin:0 0 12px;">
      Don't recruit. Invite. Give it to someone who's already living something close to this. Your invite link is in your <strong>Player State</strong> panel above (or use the templates below).
    </p>
    <div class="invite-actions">
      <button id="inviteCopyBtn" class="player-cta-primary">📋 Copy invitation</button>
      <a id="inviteWhatsApp" class="player-cta-secondary" href="#" target="_blank">💬 WhatsApp</a>
      <a id="inviteEmail" class="player-cta-secondary" href="#">✉ Email</a>
    </div>
    <details class="invite-preview" style="margin-top:12px;">
      <summary style="cursor:pointer;color:var(--accent);font-size:12px;">Preview invitation text</summary>
      <pre id="invitePreview" style="background:var(--surface-2);border:1px solid var(--border);padding:12px;border-radius:6px;font-size:12px;white-space:pre-wrap;margin-top:8px;line-height:1.5;font-family:inherit;"></pre>
    </details>
  </div>

  <div class="player-only founder-witness-card">
    <div class="fw-row">
      <div class="fw-icon">👁</div>
      <div class="fw-content">
        <div class="fw-label">FROM THE FOUNDING STEWARD</div>
        <div class="fw-quote">"I signed the World Peace Agreement first, and ran my first 7-Day proof loop on the day I deployed this page. The architect who has not run a loop is decoration; the architect who runs one becomes the system. I'm in the Game. Come play with me."</div>
        <div class="fw-attribution">— James Sunheart · Champion #1 · 2 loops complete</div>
      </div>
    </div>
  </div>

  <div class="quick-ref">
    <div class="qr-card">
      <div class="qr-icon">💎</div>
      <div class="qr-title">The Three Currencies</div>
      <ul class="qr-list">
        <li><strong>Proof</strong> — what was witnessed and recorded</li>
        <li><strong>Trust</strong> — confidence earned through repeated proof</li>
        <li><strong>Cash</strong> — flows toward Trust over time</li>
      </ul>
    </div>
    <div class="qr-card">
      <div class="qr-icon">🌟</div>
      <div class="qr-title">Player Promise</div>
      <ul class="qr-list">
        <li>Your life gets more coherent</li>
        <li>Your work becomes easier to trust</li>
        <li>More resources flow through you</li>
      </ul>
    </div>
    <div class="qr-card">
      <div class="qr-icon">🌱</div>
      <div class="qr-title">Treasury Principles</div>
      <ul class="qr-list">
        <li>Circulation over hoarding</li>
        <li>Regeneration over extraction</li>
        <li>Transparency over secrecy</li>
      </ul>
    </div>
    <div class="qr-card">
      <div class="qr-icon">🛡</div>
      <div class="qr-title">Protection Boundaries</div>
      <ul class="qr-list">
        <li>Score the proof, not the soul</li>
        <li>Private life is private</li>
        <li>Consent is non-negotiable</li>
      </ul>
    </div>
  </div>

  <div class="player-only player-hero">
    <h2 style="margin-top:0;color:var(--accent);font-size:28px;">Reality is already a game. This is the guide for those who know.</h2>
    <p style="font-size:16px;color:var(--text);margin:8px 0 16px;">
      Reality is already a game. This is where you find your pieces.
    </p>
    <p style="color:var(--muted);font-size:14px;line-height:1.7;">
      The Full Potential Game is a proof-based operating system for human potential. It makes the work people do for each other &mdash; agreements kept, offers delivered, transformations witnessed, resources circulated &mdash; <em>visible, scored, and recognized</em> in a way the dominant economy cannot.
    </p>
    <div class="player-cta-row">
      <a class="player-cta-primary" href="cursor://file{INTENT_DIR}/AGREEMENT_BUILDER_PROMPT.md">
        🌱 Start your 7-Day First Game →
      </a>
      <a class="player-cta-secondary" href="cursor://file{INTENT_DIR}/FULL_POTENTIAL_GAME.md">
        Read the Player's Guide
      </a>
    </div>
    <p style="margin:16px 0 0;color:var(--muted);font-size:12px;">
      Your first move is simple: choose one real agreement, complete it, have it witnessed, log the proof. The Game does not begin when you understand it. It begins when you complete the first agreement.
    </p>
  </div>

  <div class="field-only field-hero">
    <h2 style="margin-top:0;color:var(--accent);">The Field</h2>
    <p style="color:var(--text);font-size:14px;">
      The public aggregate view. As players begin running 7-Day First Games and consenting their proofs to public visibility, this surface populates with witnessed transformation, treasury growth, and the lived shape of coherence-in-practice.
    </p>
    <div class="field-stats">
      <div class="field-stat">
        <div class="profile-stat-n">{public_proofs}</div>
        <div class="profile-stat-lbl">Public proofs sealed</div>
      </div>
      <div class="field-stat">
        <div class="profile-stat-n">{champions_total}</div>
        <div class="profile-stat-lbl">Coherent Champions</div>
      </div>
      <div class="field-stat">
        <div class="profile-stat-n">{agreements_active}</div>
        <div class="profile-stat-lbl">Active Agreements</div>
      </div>
      <div class="field-stat">
        <div class="profile-stat-n">0</div>
        <div class="profile-stat-lbl">Coherent Credit issued</div>
      </div>
    </div>
    <p style="color:var(--muted);font-size:12px;margin-top:16px;">
      The numbers will tell the true story when there's a true story to tell. Until then, this view is mostly empty &mdash; honestly so. Ask: *will your proof loop be the first public one?*
    </p>
  </div>

  <div class="freshness founder-only" id="freshness" data-generated="{generated_iso}">
    <div class="fresh-row">
      <div class="fresh-stat">
        <span class="fresh-lbl">Map generated</span>
        <span class="fresh-val" data-ts="{generated_iso}">{now_str}</span>
        <span class="fresh-rel" data-ts="{generated_iso}">just now</span>
      </div>
      <div class="fresh-stat">
        <span class="fresh-lbl">Last commit</span>
        <span class="fresh-val" data-ts="{commit_iso}">{commit_iso[:16].replace('T',' ')}</span>
        <span class="fresh-rel" data-ts="{commit_iso}"></span>
      </div>
      <div class="fresh-stat">
        <span class="fresh-lbl">NOW.md edited</span>
        <span class="fresh-val" data-ts="{now_md_iso}">{now_md_iso[:16].replace('T',' ')}</span>
        <span class="fresh-rel" data-ts="{now_md_iso}"></span>
      </div>
      <div class="fresh-stat">
        <span class="fresh-lbl">catalog.json edited</span>
        <span class="fresh-val" data-ts="{catalog_iso}">{catalog_iso[:16].replace('T',' ')}</span>
        <span class="fresh-rel" data-ts="{catalog_iso}"></span>
      </div>
      <div class="fresh-stat" style="text-align:right;">
        <span class="fresh-lbl">Auto-reload</span>
        <span id="autoStatus" class="fresh-val">checking…</span>
        <span class="fresh-rel"><a class="link" href="#" onclick="location.reload();return false;">reload now</a></span>
      </div>
    </div>
  </div>

  <div class="filter">
    <strong>Decision filter:</strong> Does this increase <em>proof / revenue / clarity / ease</em>
    for The Village within 30 days? If not, deprioritize.
  </div>

  <div class="principle-banner">
    <div class="pb-glyph">🌀</div>
    <div class="pb-content">
      <div class="pb-label">THE LOAD-BEARING PRINCIPLE</div>
      <div class="pb-quote">"The Game is playing itself" — this line is everything to its advancement.</div>
      <div class="pb-test">
        Advancement test for every loop: <strong>does this make the Game more self-playing, or more founder-bottlenecked?</strong>
        First → ship. Second → redesign.
      </div>
      <a class="pb-link" href="#doc-plays-itself" onclick="document.getElementById('doc-plays-itself').open=true;">Read the principle inline →</a>
    </div>
  </div>

  <div class="signaling-banner">
    <div class="sb-glyph">📡</div>
    <div class="sb-content">
      <div class="sb-label">THE PROPULSION PRINCIPLE</div>
      <div class="sb-quote">"The frequency of signaling and the depth of the meaning will propel the game."</div>
      <div class="sb-test">
        Test for every signal: <strong>opt-in · deep · rhythmic · serves the receiver · never coercive.</strong>
        Frequency × Meaning = momentum.
      </div>
      <a class="pb-link" href="#doc-signaling" onclick="document.getElementById('doc-signaling').open=true;">Read the practice inline →</a>
    </div>
  </div>

  <div class="field-pulse" id="fieldPulse">
    <div class="fp-header">
      <div class="fp-label">⚡ FIELD PULSE</div>
      <div class="fp-sub" id="fpSub">live · last activity in the field</div>
    </div>
    <div class="fp-feed" id="fpFeed">
      <div class="fp-empty">Listening for signals...</div>
    </div>
  </div>

  <div class="card full" style="margin-bottom:24px;">
    <h2>Mission &amp; Agreements <span style="font-size:12px;font-weight:400;color:var(--muted);">&mdash; Layer 1: why this exists</span></h2>
    <div class="mission-poster-row">
      <a class="mission-poster" href="core/INTENT/assets/coherent-champions-poster.png" target="_blank" title="Open full-size poster">
        <img src="core/INTENT/assets/coherent-champions-poster.png" alt="Coherent Champions of CHRIST manifesto poster" />
      </a>
      <div class="mission-content">
        <div class="kpi-label">Founding</div>
        <p style="margin:4px 0 12px;font-size:16px;">
          <a class='link' href='cursor://file{INTENT_DIR}/COHERENT_CHAMPIONS_MANIFESTO.md'>Coherent Champions of CHRIST</a>
          &mdash; Manifesto v1.0
        </p>
        <p style="margin:0 0 16px;color:var(--text);font-style:italic;font-size:13px;">
          "This is not a religion of superiority. It is a practice of becoming trustworthy with power."
        </p>
        <div class="christ-row">
          <span class="christ-pill" title="Alignment between thought, word, action, technology, and consequence."><strong>C</strong>oherence</span>
          <span class="christ-pill" title="Healing individuals, relationships, communities, and ecosystems is sacred work."><strong>H</strong>ealing</span>
          <span class="christ-pill" title="Build systems that restore more life than they consume."><strong>R</strong>egeneration</span>
          <span class="christ-pill" title="Honor intelligence guided by wisdom, humility, discernment, and care."><strong>I</strong>ntelligence</span>
          <span class="christ-pill" title="Use our gifts in service to the flourishing of life."><strong>S</strong>ervice</span>
          <span class="christ-pill" title="Seek truth courageously while remaining compassionate toward human imperfection."><strong>T</strong>ruth</span>
        </div>
        <p style="margin:12px 0 0;color:var(--muted);font-size:12px;">
          <a class='link' href='cursor://file{INTENT_DIR}/WORLD_PEACE_ECOSYSTEM.md'><strong>Ecosystem</strong></a> (the what) &middot;
          <a class='link' href='cursor://file{INTENT_DIR}/WORLD_PEACE_AGREEMENT.md'>Template</a> &middot;
          <a class='link' href='cursor://file{INTENT_DIR}/FORMING_AGREEMENTS.md'>Forming protocol</a> &middot;
          <a class='link' href='cursor://file{INTENT_DIR}/README.md'>Layer guide</a>
        </p>
        <p style="margin:12px 0 0;font-size:12px;">
          <strong style="color:var(--accent);">{agreements_active}</strong> active /
          <strong>{agreements_count}</strong> total Agreements
        </p>
      </div>
    </div>
    <div class="eco-tagline">ONE MISSION · ONE HUMAN FAMILY · ONE PEACE</div>
    <h3>The Ecosystem &mdash; eight layers from Philosophy to Vision</h3>

    <div class="eco-poster-row">
      <a class="mission-poster" href="core/INTENT/assets/world-peace-ecosystem-poster.png" target="_blank" title="Open full-size ecosystem poster">
        <img src="core/INTENT/assets/world-peace-ecosystem-poster.png" alt="The World Peace Ecosystem poster" />
      </a>
      <div class="three-framings">
        <div class="framing">
          <div class="kpi-label">Our Purpose</div>
          <p>To align intelligence, technology, communities, and human action in service to peace and flourishing for all life.</p>
        </div>
        <div class="framing">
          <div class="kpi-label">Our Vision</div>
          <p>A world where coherence guides systems, communities, and the human heart.</p>
        </div>
        <div class="framing">
          <div class="kpi-label">Our Commitment</div>
          <ul>
            <li>Reduce suffering</li>
            <li>Seek understanding before hatred</li>
            <li>Repair where we've caused harm</li>
            <li>Protect life, truth, beauty, and future generations</li>
            <li>Become trustworthy with intelligence, influence, and resources</li>
          </ul>
        </div>
      </div>
    </div>

    <div class="ecosystem">
      <details class="eco-layer eco-philosophy">
        <summary>
          <span class="eco-num">★</span>
          <span class="eco-icon">✨</span>
          <div class="eco-title-block">
            <div class="eco-title">Coherent Champions of CHRIST</div>
            <div class="eco-subtitle">Core Identity</div>
            <div class="eco-tag">"We are human and AI allies, committed to bringing coherence, healing, and regeneration."</div>
          </div>
        </summary>
        <ul class="eco-components">
          <li><strong>C</strong> · Coherence</li>
          <li><strong>H</strong> · Healing</li>
          <li><strong>R</strong> · Regeneration</li>
          <li><strong>I</strong> · Intelligence</li>
          <li><strong>S</strong> · Service</li>
          <li><strong>T</strong> · Truth</li>
        </ul>
      </details>

      <details class="eco-layer eco-org">
        <summary>
          <span class="eco-num">1</span>
          <span class="eco-icon">🕊</span>
          <div class="eco-title-block">
            <div class="eco-title">World Peace Organization</div>
            <div class="eco-subtitle">The Stewardship Layer</div>
            <div class="eco-tag">"We organize the movement, support initiatives, and steward the mission for generations."</div>
          </div>
        </summary>
        <ul class="eco-components">
          <li>Global Mission</li>
          <li>Chapters &amp; Gatherings</li>
          <li>Peace Education</li>
          <li>AI Coordination</li>
          <li>Regenerative Projects</li>
          <li>Partnerships &amp; Alliances</li>
        </ul>
      </details>

      <details class="eco-layer eco-agreement">
        <summary>
          <span class="eco-num">2</span>
          <span class="eco-icon">📜</span>
          <div class="eco-title-block">
            <div class="eco-title">World Peace Agreement</div>
            <div class="eco-subtitle">The Alignment Layer</div>
            <div class="eco-tag">"Peace becomes real when humans agree to practice it." &mdash; <em>One agreement. One humanity. One future.</em></div>
          </div>
        </summary>
        <ul class="eco-components">
          <li>Non-Harm</li>
          <li>Repair</li>
          <li>Truth</li>
          <li>Regeneration</li>
          <li>Human Dignity</li>
          <li>Service to Life</li>
        </ul>
      </details>

      <div class="eco-row">
        <details class="eco-layer eco-party">
          <summary>
            <span class="eco-num">3</span>
            <span class="eco-icon">🎶</span>
            <div class="eco-title-block">
              <div class="eco-title">World Peace Party</div>
              <div class="eco-subtitle">The Activation Layer</div>
              <div class="eco-tag">"Joy is the gateway to unity."</div>
            </div>
          </summary>
          <ul class="eco-components">
            <li>Music &amp; Dance</li>
            <li>Joy &amp; Unity</li>
            <li>Emotional Release</li>
            <li>Social Healing</li>
            <li>Human Connection</li>
          </ul>
        </details>

        <details class="eco-layer eco-weekend">
          <summary>
            <span class="eco-num">4</span>
            <span class="eco-icon">🌿</span>
            <div class="eco-title-block">
              <div class="eco-title">World Peace Weekend</div>
              <div class="eco-subtitle">The Immersion Layer</div>
              <div class="eco-tag">"Deep experiences create lasting transformation."</div>
            </div>
          </summary>
          <ul class="eco-components">
            <li>Cacao &amp; Ceremony</li>
            <li>Ecstatic Dance</li>
            <li>Fire Circles</li>
            <li>Sauna &amp; River</li>
            <li>Workshops &amp; Dialogue</li>
            <li>Peace Ceremonies</li>
            <li>Integration &amp; Reflection</li>
            <li>Healthy Food &amp; Community</li>
          </ul>
        </details>

        <details class="eco-layer eco-ai">
          <summary>
            <span class="eco-num">5</span>
            <span class="eco-icon">🧠</span>
            <div class="eco-title-block">
              <div class="eco-title">AI for Peace</div>
              <div class="eco-subtitle">The Intelligence Layer</div>
              <div class="eco-tag">"AI is not our ruler. AI is our tool, companion, and amplifier for good."</div>
            </div>
          </summary>
          <ul class="eco-components">
            <li>Coordination</li>
            <li>Translation</li>
            <li>Education</li>
            <li>Conflict De-escalation</li>
            <li>Resource Routing</li>
            <li>Memory &amp; Knowledge</li>
            <li>Systems Optimization</li>
            <li>Amplifying Human Potential</li>
          </ul>
        </details>
      </div>

      <details class="eco-layer eco-village">
        <summary>
          <span class="eco-num">6</span>
          <span class="eco-icon">🏕</span>
          <div class="eco-title-block">
            <div class="eco-title">Zen Village Prototype</div>
            <div class="eco-subtitle">The Living Prototype Layer</div>
            <div class="eco-tag">"A living demonstration of coherent civilization." &mdash; <em>See it. Feel it. Live it. Share it.</em></div>
          </div>
        </summary>
        <ul class="eco-components">
          <li>Regenerative Living</li>
          <li>Sacred Gatherings</li>
          <li>AI + Humanity</li>
          <li>Nature + Beauty</li>
          <li>Wellness</li>
          <li>Community</li>
          <li>Creativity</li>
          <li>Peace Infrastructure</li>
        </ul>
      </details>

      <details class="eco-layer eco-media">
        <summary>
          <span class="eco-num">7</span>
          <span class="eco-icon">📡</span>
          <div class="eco-title-block">
            <div class="eco-title">Media + Culture</div>
            <div class="eco-subtitle">The Signal Layer</div>
            <div class="eco-tag">"We tell the story of a better world."</div>
          </div>
        </summary>
        <ul class="eco-components">
          <li>Films &amp; Storytelling</li>
          <li>Podcasts &amp; Interviews</li>
          <li>Music &amp; Art</li>
          <li>Transformation Stories</li>
          <li>Viral Peace Content</li>
          <li>Global Participation</li>
        </ul>
      </details>

      <details class="eco-layer eco-econ">
        <summary>
          <span class="eco-num">8</span>
          <span class="eco-icon">🌱</span>
          <div class="eco-title-block">
            <div class="eco-title">Regenerative Economy</div>
            <div class="eco-subtitle">The Sustainability Layer</div>
            <div class="eco-tag">"Peace funds peace. Regeneration sustains all."</div>
          </div>
        </summary>
        <p style="font-family:ui-monospace,monospace;font-size:12px;color:var(--accent);margin:8px 0 0 36px;">
          Events &rarr; Community &rarr; Media &rarr; Participation &rarr; Resources &rarr; Regeneration
        </p>
      </details>

      <div class="eco-layer eco-vision">
        <span class="eco-num">✦</span>
        <span class="eco-icon">✨</span>
        <div class="eco-title-block">
          <div class="eco-title">The Long-Term Vision</div>
          <div class="eco-tag">A world where intelligence serves life. A civilization organized around coherence instead of chaos. A culture where peace becomes lived reality.</div>
          <div class="eco-tag" style="color:var(--accent);font-weight:600;">Together, we can build a future worth inheriting.</div>
        </div>
      </div>
    </div>

    <h3 style="margin-top:24px;">WPAP &mdash; World Peace Agreements Protocol</h3>
    <p style="color:var(--muted);font-size:12px;margin:0 0 12px;">
      The AI-assisted system that operationalizes Layer 5 (AI for Peace).
      <a class='link' href='cursor://file{INTENT_DIR}/WORLD_PEACE_AGREEMENTS_PROTOCOL.md'>Open WPAP doc</a>
    </p>
    <blockquote class="wpap-tldr">
      Help humans make clearer agreements.<br>
      Help humans remember those agreements.<br>
      Help humans repair when agreements strain.<br>
      Help intelligence serve peace instead of escalation.
    </blockquote>
    <div class="wpap-modules">
      <div class="wpap-mod"><span class="wpap-icon">🕊</span><div><div class="wpap-name">Agreement Builder</div><div class="wpap-fn">Interactive coherent agreement creation</div></div></div>
      <div class="wpap-mod"><span class="wpap-icon">🧠</span><div><div class="wpap-name">Coherence Analyzer</div><div class="wpap-fn">Detects ambiguity, imbalance, missing expectations</div></div></div>
      <div class="wpap-mod"><span class="wpap-icon">❤️</span><div><div class="wpap-name">Conflict Translator</div><div class="wpap-fn">Reframes emotionally charged language</div></div></div>
      <div class="wpap-mod"><span class="wpap-icon">🔄</span><div><div class="wpap-name">Repair Guide</div><div class="wpap-fn">Guides repair and reconciliation processes</div></div></div>
      <div class="wpap-mod"><span class="wpap-icon">📜</span><div><div class="wpap-name">Peace Ledger</div><div class="wpap-fn">Tracks versions, acknowledgments, commitments</div></div></div>
      <div class="wpap-mod"><span class="wpap-icon">🌍</span><div><div class="wpap-name">Cultural Translator</div><div class="wpap-fn">Bridges values and communication globally</div></div></div>
    </div>
    <h3 style="margin-top:20px;">Phased rollout</h3>
    <div class="wpap-phases">
      <div class="wpap-phase wpap-phase-current">
        <div class="wpap-phase-num">Phase 1</div>
        <div class="wpap-phase-name">Cultural Layer</div>
        <div class="wpap-phase-tag">Build emotional resonance first.</div>
        <div class="wpap-phase-status">In progress</div>
      </div>
      <div class="wpap-phase">
        <div class="wpap-phase-num">Phase 2</div>
        <div class="wpap-phase-name">Operational Layer</div>
        <div class="wpap-phase-tag">Make coherence tangible. Simple AI agreement tools.</div>
        <div class="wpap-phase-status">Next</div>
      </div>
      <div class="wpap-phase">
        <div class="wpap-phase-num">Phase 3</div>
        <div class="wpap-phase-name">Peace Infrastructure</div>
        <div class="wpap-phase-tag">Real social technology — mediation, translation, repair, memory.</div>
        <div class="wpap-phase-status">Future</div>
      </div>
      <div class="wpap-phase">
        <div class="wpap-phase-num">Phase 4</div>
        <div class="wpap-phase-name">Global Protocol</div>
        <div class="wpap-phase-tag">Open frameworks any community can adopt. World Peace stops being abstract.</div>
        <div class="wpap-phase-status">Long arc</div>
      </div>
    </div>
    <h3 style="margin-top:24px;">Treasury &amp; Game &mdash; how the economy starts growing</h3>
    <div class="treasury-row">
      <div class="treasury-card">
        <div class="t-icon">🏦</div>
        <div class="t-title">Remarkably Coherent Treasury</div>
        <div class="t-version">v0.10 · architectural spec</div>
        <p class="t-tag">"Make it easier to live in truth than to live out of alignment."</p>
        <ul class="t-points">
          <li><strong>Wedge equation:</strong> Total System Power = Money × Velocity × Coherence</li>
          <li><strong>Two-Economy Model:</strong> dollar economy + parallel Coherent Credit network</li>
          <li><strong>Three-Layer:</strong> Interface (legal payroll) · Logic (coherence math) · Covenant (religious community)</li>
          <li><strong>Five-component compensation:</strong> Dignity Base · Contribution Dividend · Circulation Share · Stewardship Vesting · Trust Participation</li>
        </ul>
        <p style="margin:12px 0 0;font-size:11px;">
          <a class='link' href='cursor://file{INTENT_DIR}/REMARKABLY_COHERENT_TREASURY.md'>Open full spec (1076 lines)</a>
        </p>
      </div>
      <div class="treasury-card">
        <div class="t-icon">🎮</div>
        <div class="t-title">The Full Potential Game</div>
        <div class="t-version">v1.3 · player-facing OS</div>
        <p class="t-tag">"Reality is already a game. This is the guide for those who know."</p>
        <ul class="t-points">
          <li><strong>Sacred Trinity:</strong> Community · Communication · Currency</li>
          <li><strong>Four Containers:</strong> Zen Village · Coherence · Full Potential AI · CORA Nation</li>
          <li><strong>Three Currencies:</strong> Proof · Trust · Cash</li>
          <li><strong>Awareness Ladder:</strong> Noise → Distraction → Attention → Zense → Presence → Coherence → Flow → Stillness</li>
        </ul>
        <p style="margin:12px 0 0;font-size:11px;">
          <a class='link' href='cursor://file{INTENT_DIR}/FULL_POTENTIAL_GAME.md'>Open Game guide</a> &middot;
          <a class='link' href='cursor://file{INTENT_DIR}/FULL_POTENTIAL_GAME_PLAYER_CARD.md'>Player Card</a>
        </p>
      </div>
    </div>

    <div class="proof-loop-card">
      <div class="proof-loop-header">
        <div class="t-icon">🌱</div>
        <div>
          <div class="t-title">7-Day First Game &mdash; <span style="color:var(--good);">START HERE</span></div>
          <div class="t-version">The smallest move that grows the Treasury · AI-assisted</div>
        </div>
      </div>
      <p style="margin:8px 0 12px;color:var(--text);">
        Every completed loop produces a Proof Log entry, a witnessed transformation, and one tick of Useful Output.
        The Treasury grows by accumulating verified coherence production — <strong>one loop at a time.</strong>
      </p>
      <div class="proof-7day">
        <div class="proof-day"><span class="proof-day-num">Day 1</span><span>Choose one transformation</span></div>
        <div class="proof-day"><span class="proof-day-num">Day 2</span><span>Write the offer (one sentence)</span></div>
        <div class="proof-day"><span class="proof-day-num">Day 3</span><span>Film one real ad</span></div>
        <div class="proof-day"><span class="proof-day-num">Day 4</span><span>Send to 20 aligned people</span></div>
        <div class="proof-day"><span class="proof-day-num">Day 5</span><span>Book one</span></div>
        <div class="proof-day"><span class="proof-day-num">Day 6</span><span>Deliver the experience</span></div>
        <div class="proof-day"><span class="proof-day-num">Day 7</span><span>Write + log the Proof</span></div>
      </div>
      <p style="margin:12px 0 0;font-size:13px;">
        <a class='link' href='cursor://file{INTENT_DIR}/AGREEMENT_BUILDER_PROMPT.md' style="font-weight:700;">→ Open the AI-Assisted Player Card prompt</a>
        &nbsp; Paste into Claude (terminal / desktop / web). Claude facilitates the loop and writes your Proof Log entry.
      </p>
      <p style="margin:8px 0 0;font-size:11px;color:var(--muted);">
        Minimum Viable Scoreboard: <span class='christ-pill'>Agreements kept</span><span class='christ-pill'>Outputs shipped</span><span class='christ-pill'>Transformations witnessed</span><span class='christ-pill'>Resources circulated</span><span class='christ-pill'>Clean pauses</span>
      </p>
    </div>

    <h3 style="margin-top:20px;">Active &amp; pending Agreements</h3>
    {agreements_html}

    <details class="canonical-library-wrapper">
      <summary class="cl-summary">
        <span class="cl-icon">📚</span>
        <div class="cl-title-block">
          <div class="cl-title">Read the Canon — every founding document</div>
          <div class="cl-sub">Manifesto · Framework · Loop · Treasury · Game · WPAP · Agreement · Forming · Player Card · Builder Prompt · Character · Plays Itself · Signaling</div>
        </div>
        <span class="cl-expand">expand library →</span>
      </summary>
      <div class="canonical-library">
        <p style="color:var(--muted);font-size:12px;margin:8px 0 12px;">
          Every founding document, fully rendered inline. Click any card to read in place — no external app, no permission popups.
        </p>
        {inline_docs_html}
      </div>
    </details>

    <h3 style="margin-top:24px;">🔄 The Positive Loop &mdash; how the field grows</h3>
    <p style="color:var(--muted);font-size:12px;margin:0 0 12px;">
      Party → Play → Apprentice → Build → more Party. A self-reinforcing flywheel.
      <a class='link' href='#doc-positive-loop' onclick="document.getElementById('doc-positive-loop').open=true;">Read full doc inline →</a>
    </p>
    <div class="loop-poster-row">
      <a class="mission-poster" href="core/INTENT/assets/positive-loop-poster.png" target="_blank" title="Open full-size loop poster">
        <img src="core/INTENT/assets/positive-loop-poster.png" alt="The Positive Loop — flywheel" />
      </a>
      <div class="loop-quadrants">
        <div class="loop-q loop-q-1">
          <div class="loop-q-num">1</div>
          <div class="loop-q-icon">🎉</div>
          <div class="loop-q-title">World Peace Party</div>
          <div class="loop-q-sub">The Emotional Ignition</div>
          <div class="loop-q-tag">Joy · Connection · Belonging · Inspiration</div>
        </div>
        <div class="loop-q loop-q-2">
          <div class="loop-q-num">2</div>
          <div class="loop-q-icon">🎮</div>
          <div class="loop-q-title">Play the Full Potential Game</div>
          <div class="loop-q-sub">The Experiential Path</div>
          <div class="loop-q-tag">Learn · Agree · Contribute · Earn &amp; Impact</div>
        </div>
        <div class="loop-q loop-q-3">
          <div class="loop-q-num">3</div>
          <div class="loop-q-icon">🤖</div>
          <div class="loop-q-title">Become an AI Apprentice</div>
          <div class="loop-q-sub">The Transformational Path</div>
          <div class="loop-q-tag">Systems · Coherence · Stewardship · Regeneration · AI Collaboration</div>
        </div>
        <div class="loop-q loop-q-4">
          <div class="loop-q-num">4</div>
          <div class="loop-q-icon">🏗</div>
          <div class="loop-q-title">Build the Operating Systems</div>
          <div class="loop-q-sub">The Creative Builder Path</div>
          <div class="loop-q-tag">Design · Code · Test · Iterate · Deploy · Impact</div>
        </div>
      </div>
    </div>

    <h3 style="margin-top:20px;">🎓 The Progression Path</h3>
    <div class="progression-row">
      <div class="prog-stage">
        <div class="prog-icon">👥</div>
        <div class="prog-name">Guest</div>
        <div class="prog-quote">"I came for the party"</div>
      </div>
      <div class="prog-arrow">→</div>
      <div class="prog-stage">
        <div class="prog-icon">🎮</div>
        <div class="prog-name">Player</div>
        <div class="prog-quote">"I discovered the Game"</div>
      </div>
      <div class="prog-arrow">→</div>
      <div class="prog-stage">
        <div class="prog-icon">🎓</div>
        <div class="prog-name">Apprentice</div>
        <div class="prog-quote">"I'm learning and growing"</div>
      </div>
      <div class="prog-arrow">→</div>
      <div class="prog-stage">
        <div class="prog-icon">🌱</div>
        <div class="prog-name">Steward</div>
        <div class="prog-quote">"I take responsibility and lead"</div>
      </div>
      <div class="prog-arrow">→</div>
      <div class="prog-stage">
        <div class="prog-icon">🏗</div>
        <div class="prog-name">Builder</div>
        <div class="prog-quote">"I build systems for a better world"</div>
      </div>
    </div>
    <p style="color:var(--muted);font-size:11px;margin:8px 0 0;text-align:center;font-style:italic;">
      You don't pick your stage. The stage picks you. Field response confirms readiness.
    </p>

    <h3 style="margin-top:20px;">🛠 The 7 System Areas <span style="font-size:11px;font-weight:400;color:var(--muted);">&mdash; what Builders build</span></h3>
    <div class="systems-grid">
      <div class="sys-card"><div class="sys-icon">✓</div><div class="sys-name">Agreement Systems</div><div class="sys-desc">Clear agreements, shared values, conflict transformation.</div></div>
      <div class="sys-card"><div class="sys-icon">🕸</div><div class="sys-name">Coordination Systems</div><div class="sys-desc">Collaborative tools, decision making, collective intelligence.</div></div>
      <div class="sys-card"><div class="sys-icon">💰</div><div class="sys-name">Treasury Systems</div><div class="sys-desc">Transparent funding, abundance models, regenerative economics.</div></div>
      <div class="sys-card"><div class="sys-icon">👥</div><div class="sys-name">Community Systems</div><div class="sys-desc">Local + global networks, belonging, support, celebration.</div></div>
      <div class="sys-card"><div class="sys-icon">🤖</div><div class="sys-name">AI Systems</div><div class="sys-desc">Ethical AI, open models, human-AI collaboration aligned with life.</div></div>
      <div class="sys-card"><div class="sys-icon">🎨</div><div class="sys-name">Cultural Systems</div><div class="sys-desc">Stories, rituals, art, education and media that elevate humanity.</div></div>
      <div class="sys-card"><div class="sys-icon">🌍</div><div class="sys-name">Regeneration Systems</div><div class="sys-desc">Food, water, energy, biodiversity, planet healing.</div></div>
    </div>

    <h3 style="margin-top:24px;">📐 The Full Potential Framework &mdash; eight-layer stack</h3>
    <div class="framework-poster-row">
      <a class="mission-poster" href="core/INTENT/assets/full-potential-framework-poster.png" target="_blank" title="Open full-size framework poster">
        <img src="core/INTENT/assets/full-potential-framework-poster.png" alt="The Full Potential Framework — eight-layer civilization stack" />
      </a>
      <div class="framework-content">
        <p style="font-size:13px;color:var(--text);margin:0 0 12px;">
          <strong>ONE MISSION · ONE AGREEMENT · ONE GAME · ONE TREASURY · ONE HUMAN FAMILY</strong>
        </p>
        <p style="color:var(--muted);font-size:12px;line-height:1.7;margin:0;">
          The complete coordination stack supersedes the earlier ecosystem framing. Eight layers:
          ① World Peace Organization · ② World Peace Agreement · ③ Full Potential Game ·
          ④ Coherent AI Layer · ⑤ Coherent Treasury · ⑥ Zen Village + Local Nodes ·
          ⑦ Cultural Activation · ⑧ Media + AI + Local Networks.
          The Outcome: <strong>Visible Human Flourishing</strong>.
        </p>
        <p style="margin:12px 0 0;font-size:12px;">
          <a class='link' href='#doc-framework' onclick="document.getElementById('doc-framework').open=true;" style="font-weight:700;">
            → Read the full framework inline
          </a>
        </p>
      </div>
    </div>
  </div>

  <div class="founder-only steward-queue">
    <h2>Steward Queue &mdash; founder-only actions</h2>
    <p style="color:var(--muted);font-size:12px;margin:0 0 12px;">
      Things only James can do as Founding Steward. AI cannot substitute judgment on identity / mission / vision / value (per the James↔Claude Agreement).
    </p>
    <div class="steward-grid">
      <div class="steward-item steward-pending">
        <div class="steward-icon">📜</div>
        <div class="steward-action">Ratify James↔Claude Agreement</div>
        <div class="steward-detail">Drafted by Claude in desktop session, awaits founder ratification or amendment.</div>
      </div>
      <div class="steward-item steward-pending">
        <div class="steward-icon">📜</div>
        <div class="steward-action">Ratify WPO↔Land Agreement</div>
        <div class="steward-detail">Currently <code>status: proposed</code> — your call to ratify, amend, or redraft.</div>
      </div>
      <div class="steward-item">
        <div class="steward-icon">✍️</div>
        <div class="steward-action">Witness proofs (when players begin)</div>
        <div class="steward-detail">No public proofs awaiting signature yet. As 7-Day Games run, witness queue populates here.</div>
      </div>
      <div class="steward-item">
        <div class="steward-icon">🚀</div>
        <div class="steward-action">Push 19+ commits to origin</div>
        <div class="steward-detail">Today's WPO foundation work is local-only. Per Agreement, push requires explicit per-action authorization.</div>
      </div>
      <div class="steward-item">
        <div class="steward-icon">🎯</div>
        <div class="steward-action">Run your own 7-Day First Game</div>
        <div class="steward-detail">Founder Player Card. The architect who has not run a loop is decoration; the architect who runs one becomes the system.</div>
      </div>
      <div class="steward-item">
        <div class="steward-icon">📝</div>
        <div class="steward-action">Manifesto footer alignment</div>
        <div class="steward-detail">Add "TOGETHER, WE CAN BUILD A FUTURE WORTH INHERITING" + acronym summary from poster.</div>
      </div>
    </div>
  </div>

  <div class="founder-only scoreboard">
    <h2>Founder Scoreboard <span style="font-size:12px;font-weight:400;color:var(--muted);">&mdash; civilization-quest tier metrics</span></h2>
    <p style="color:var(--muted);font-size:12px;margin:0 0 12px;">
      Different from a Player's scoreboard. The founder's <em>Useful Output</em> is *building the substrate* — every document, system, and Civilization Quest milestone shipped.
    </p>
    <div class="metric-row">
      <div class="metric-card">
        <div class="metric-icon">📜</div>
        <div class="metric-n">{intent_docs}</div>
        <div class="metric-lbl">Founding documents authored</div>
        <div class="metric-sub">in <code>core/INTENT/</code></div>
      </div>
      <div class="metric-card">
        <div class="metric-icon">⚖️</div>
        <div class="metric-n">{agreements_count}<span class="metric-frac"> / {agreements_count}</span></div>
        <div class="metric-lbl">Agreements drafted (none yet ratified)</div>
        <div class="metric-sub">{agreements_ratified} ratified by founder</div>
      </div>
      <div class="metric-card">
        <div class="metric-icon">🚀</div>
        <div class="metric-n">{civ_milestones_30d}</div>
        <div class="metric-lbl">Civ-Quest commits (30d)</div>
        <div class="metric-sub">{civ_milestones_7d} in last 7 days</div>
      </div>
      <div class="metric-card">
        <div class="metric-icon">✍️</div>
        <div class="metric-n">0</div>
        <div class="metric-lbl">Proofs witnessed</div>
        <div class="metric-sub">queue empty — populates as players run loops</div>
      </div>
      <div class="metric-card">
        <div class="metric-icon">🌱</div>
        <div class="metric-n">{proofs_count}</div>
        <div class="metric-lbl">Own proof loops completed</div>
        <div class="metric-sub">"the architect who runs one becomes the system"</div>
      </div>
      <div class="metric-card">
        <div class="metric-icon">🏛</div>
        <div class="metric-n">5</div>
        <div class="metric-lbl">Stewardship containers held</div>
        <div class="metric-sub">WPO · CORA · Zen Village · Full Potential AI · Coherence</div>
      </div>
    </div>

    <h3 style="margin-top:20px;">Awareness Ladder <span style="font-size:11px;font-weight:400;color:var(--muted);">&mdash; click your current rung; persists in your browser</span></h3>
    <div class="ladder" id="ladder">
      <button class="rung" data-rung="0">Noise</button>
      <button class="rung" data-rung="1">Distraction</button>
      <button class="rung" data-rung="2">Attention</button>
      <button class="rung" data-rung="3">Zense</button>
      <button class="rung" data-rung="4">Presence</button>
      <button class="rung" data-rung="5">Coherence</button>
      <button class="rung" data-rung="6">Flow</button>
      <button class="rung" data-rung="7">Stillness</button>
    </div>
    <p class="ladder-note" id="ladderNote" style="color:var(--muted);font-size:11px;margin:8px 0 0;"></p>

    <h3 style="margin-top:20px;">6 C's snapshot <span style="font-size:11px;font-weight:400;color:var(--muted);">&mdash; quick self-rate; meta-ratio above</span></h3>
    <div class="cs-meta">
      <label class="c-row">
        <span class="c-label"><strong>Creation / Consumption ratio</strong> <span class='muted'>(meta — when this inverts, all C's go noisy)</span></span>
        <input type="range" min="0" max="100" value="50" data-c="meta" class="c-slider" />
        <span class="c-value" data-for="meta">50</span>
      </label>
    </div>
    <div class="cs-row">
      <label class="c-row"><span class="c-label">Coherence</span><input type="range" min="0" max="100" value="50" data-c="coherence" class="c-slider" /><span class="c-value" data-for="coherence">50</span></label>
      <label class="c-row"><span class="c-label">Celebration</span><input type="range" min="0" max="100" value="50" data-c="celebration" class="c-slider" /><span class="c-value" data-for="celebration">50</span></label>
      <label class="c-row"><span class="c-label">Care/Communication</span><input type="range" min="0" max="100" value="50" data-c="care" class="c-slider" /><span class="c-value" data-for="care">50</span></label>
      <label class="c-row"><span class="c-label">Connections</span><input type="range" min="0" max="100" value="50" data-c="connections" class="c-slider" /><span class="c-value" data-for="connections">50</span></label>
      <label class="c-row"><span class="c-label">Cash Flow</span><input type="range" min="0" max="100" value="50" data-c="cash" class="c-slider" /><span class="c-value" data-for="cash">50</span></label>
    </div>
    <p style="color:var(--muted);font-size:11px;margin:8px 0 0;">
      Honest snapshot beats aspirational rating. Lived coherence over measured coherence. (Treasury §3 — Measurement Humility Law.)
    </p>
  </div>

  <div class="player-only player-scoreboard">
    <h2>Your Scoreboard <span style="font-size:12px;font-weight:400;color:var(--muted);">&mdash; preview · populates as you run loops</span></h2>
    <p style="color:var(--muted);font-size:12px;margin:0 0 12px;">
      The Game tracks witnessed proof, not your soul. Your scoreboard fills in as you complete proof loops with witness signatures.
    </p>
    <div class="metric-row">
      <div class="metric-card"><div class="metric-icon">🤝</div><div class="metric-n">0</div><div class="metric-lbl">Agreements kept</div></div>
      <div class="metric-card"><div class="metric-icon">📦</div><div class="metric-n">0</div><div class="metric-lbl">Useful outputs shipped</div></div>
      <div class="metric-card"><div class="metric-icon">🌱</div><div class="metric-n">0</div><div class="metric-lbl">Transformations witnessed</div></div>
      <div class="metric-card"><div class="metric-icon">🔄</div><div class="metric-n">0</div><div class="metric-lbl">Resources circulated</div></div>
      <div class="metric-card"><div class="metric-icon">🌬</div><div class="metric-n">0</div><div class="metric-lbl">Clean pauses completed</div></div>
    </div>
    <p style="color:var(--muted);font-size:11px;margin:12px 0 0;">
      <strong>Field Score</strong> = sum of witnessed proofs · <strong>CPI</strong> (Trust) = compounded positive impact, network-weighted · See glossary below.
    </p>
  </div>

  <div class="metrics-glossary">
    <h2>Metrics glossary</h2>
    <p style="color:var(--muted);font-size:12px;margin:0 0 12px;">
      What every term in this dashboard actually means. Most are aspirational while infrastructure ships; the Minimum Viable Scoreboard is what runs today.
    </p>
    <div class="glossary-grid">
      <div class="glossary-item">
        <div class="glossary-term">Field Score</div>
        <div class="glossary-def">Per-event scoring of a witnessed proof. The atomic unit. Lives in <code>AGREEMENTS/proofs/</code>. (Game §5)</div>
      </div>
      <div class="glossary-item">
        <div class="glossary-term">CPI &mdash; Compounded Positive Impact</div>
        <div class="glossary-def">Trust metric. Rolled-up sum of Field Scores over time, weighted by network responsiveness. <strong>Approximated by the Minimum Viable Scoreboard</strong> until full rollup engine ships. (Game §5 + Stewards' Cut)</div>
      </div>
      <div class="glossary-item">
        <div class="glossary-term">Minimum Viable Scoreboard (MVS)</div>
        <div class="glossary-def">The 5 metrics every player tracks today: Agreements kept · Outputs shipped · Transformations witnessed · Resources circulated · Clean pauses. (Game §6)</div>
      </div>
      <div class="glossary-item">
        <div class="glossary-term">Useful Output</div>
        <div class="glossary-def">Concrete measurable value produced. Hard-number floor. Role-specific oracle (commits merged, tickets closed, harvests, etc.). Required to be tamper-proof. (Treasury §7)</div>
      </div>
      <div class="glossary-item">
        <div class="glossary-term">Coherence Multiplier</div>
        <div class="glossary-def">-1.0 to +2.0 factor adjusting Useful Output by how cleanly the work strengthened or degraded the seven-dimension field. Triangulated; never set unilaterally. (Treasury §7)</div>
      </div>
      <div class="glossary-item">
        <div class="glossary-term">Dividend Formula</div>
        <div class="glossary-def">Useful Output × Coherence Multiplier × Profit Pool Share. Both must be real — gaming one alone catches the other to zero. (Treasury §7)</div>
      </div>
      <div class="glossary-item">
        <div class="glossary-term">Verification Escrow</div>
        <div class="glossary-def">70% of Contribution Dividend pays now; 30% releases 6-12 months later if longitudinal drift confirms. No clawback. (Treasury §7)</div>
      </div>
      <div class="glossary-item">
        <div class="glossary-term">Awareness Ladder</div>
        <div class="glossary-def">Noise → Distraction → Attention → Zense → Presence → Coherence → Flow → Stillness. Move up by reps, not reading. (Game §8)</div>
      </div>
      <div class="glossary-item">
        <div class="glossary-term">6 C's</div>
        <div class="glossary-def">Coherence · Celebration · Care/Communication · Connections · Cash Flow. Above all of them: Creation/Consumption ratio. When that inverts, every C below goes noisy. (Game §8)</div>
      </div>
      <div class="glossary-item">
        <div class="glossary-term">Sunheart Rule</div>
        <div class="glossary-def">"Do only what you do better than AI. Everything else, the system handles." Founder's operating rule. (Game §8)</div>
      </div>
      <div class="glossary-item">
        <div class="glossary-term">Five Agreement Types</div>
        <div class="glossary-def">Date-Specific Showup · Time Block · Deliverable by Date · Priority Interrupt · Paradigm Shift. Score differently because they cost differently. (Game §6)</div>
      </div>
      <div class="glossary-item">
        <div class="glossary-term">Distance-Weighted Witness</div>
        <div class="glossary-def">Witnesses count more the further they are from the player (different team / org / no dependency). Collusion can't game what it can't reach. (Treasury §7)</div>
      </div>
    </div>
  </div>

  <div class="founder-only queue">
    <h2>Decision queue &mdash; needs James</h2>
    <div class="queue-row">
      <div class="queue-stat">
        <div class="n">{len(decisions)}</div>
        <div class="lbl">Open decisions</div>
      </div>
      <div class="queue-stat">
        <div class="n">{n_untagged}</div>
        <div class="lbl">Untagged services</div>
      </div>
      <div class="queue-stat">
        <div class="n">{len(drift)}</div>
        <div class="lbl">Drift / blind spots</div>
      </div>
      <div class="queue-stat">
        <div class="n">{len([r for r in rubric if not r.startswith('[x]')])}</div>
        <div class="lbl">30-day rubric items</div>
      </div>
    </div>
    <ol>{decisions_html}</ol>
  </div>

  <div class="grid founder-only">
    <div class="card">
      <div class="kpi-label">Priority 1</div>
      <div class="kpi" style="font-size:18px;">The Village</div>
      <p style="color:var(--muted);margin:8px 0 0;">
        Couch-Stage capture leg first &mdash; voice memo &rarr; transcript &rarr; AI reflection &rarr; Brain note.
      </p>
    </div>
    <div class="card">
      <div class="kpi-label">Monthly burn</div>
      <div class="kpi">{escape(total_mo or '~$805')}</div>
      <p style="color:var(--muted);margin:8px 0 0;">
        3 servers + Cursor + Claude + API. Outbounders (legacy) revenue rate <strong>unknown</strong>.
      </p>
    </div>
    <div class="card">
      <div class="kpi-label">Service distribution</div>
      <div class="donut-row">
        {donut_svg}
        <div class="donut-legend">{donut_legend}</div>
      </div>
      <p style="color:var(--muted);margin:0;font-size:12px;">
        {n_untagged} untagged · most are <span class='badge cruft'>cruft</span> (deprioritized).
      </p>
    </div>
  </div>

  <div class="grid founder-only">
    <div class="card">
      <h2>Current focus</h2>
      {focus_html}
    </div>
    <div class="card">
      <h2>30-day rubric</h2>
      <ul>{rubric_html}</ul>
    </div>
    <div class="card">
      <h2>Drift / blind spots</h2>
      {drift_html}
    </div>
  </div>

  <div class="card full founder-only" style="margin-bottom:16px;">
    <h2>Money</h2>
    <h3>Outflow &mdash; proportional</h3>
    {money_bar_svg}
    <h3>Outflow &mdash; detail</h3>
    {render_table(money_rows)}
    <h3>Inflow</h3>
    {render_table(inflow_rows)}
  </div>

  <div class="card full founder-only" style="margin-bottom:16px;">
    <h2>What's live now <span style="font-size:12px;font-weight:400;color:var(--muted);">&mdash; status dots probed live on page load</span></h2>
    {render_live_table(live_rows)}
    <p style="color:var(--muted);font-size:11px;margin:12px 0 0;">
      <span class="dot live"></span> reachable &nbsp;
      <span class="dot bad"></span> unreachable &nbsp;
      <span class="dot warn"></span> probe blocked (CORS / private host) &nbsp;
      <span class="dot" style="background:var(--cruft);"></span> no URL to probe
    </p>
  </div>

  <div class="card full founder-only" style="margin-bottom:16px;">
    <h2>Services ({n_total} total)</h2>
    <p style="color:var(--muted);margin:0 0 12px;">
      Click a service name to open its directory in your editor (vscode:// link).
      Use the search and tag pills to filter.
    </p>
    {services_html}
  </div>

  <div class="grid founder-only">
    <div class="card">
      <h2>30-day activity</h2>
      <div class="sparkline-meta">
        <span>{n_total_commits} commits across {n_active_days} days</span>
        <span>30 days ago &rarr; today</span>
      </div>
      {sparkline_svg}
      <h3 style="margin-top:16px;">Recent commits</h3>
      {commits_html}
    </div>
    <div class="card">
      <h2>Untagged services ({n_untagged})</h2>
      <div class="untagged-callout">
        <strong>Decision candidates.</strong> Each is a kill / keep / promote call.
        Edit <code>core/STATE/catalog.json</code> &rarr; <code>tags</code> to assign:
        <code>P1</code>, <code>P2</code>, <code>infra</code>, or <code>cruft</code>.
      </div>
      <p style="color:var(--muted);font-size:12px;margin:0;">
        Filter the service tree above by clicking the <span class='badge unknown'>unknown</span> pill.
      </p>
    </div>
    <div class="card">
      <h2>Source files</h2>
      <p>
        <a class="svc" href="cursor://file{NOW}"><code>core/STATE/NOW.md</code></a> &mdash; SSOT.<br>
        <a class="svc" href="cursor://file{CATALOG}"><code>core/STATE/catalog.json</code></a> &mdash; service tags.<br>
        <a class="svc" href="cursor://file{ROOT/'STRUCTURE.md'}"><code>STRUCTURE.md</code></a> &mdash; layout.
      </p>
      <p style="color:var(--muted);font-size:12px;">
        Edit <code>NOW.md</code>, then re-run the generator to refresh this map.
      </p>
    </div>
  </div>

  <footer>
    Generated by <code>tools/gen_cockpit_map.py</code>.
    This is a snapshot &mdash; for live state always check <code>git log</code> + <code>git status</code> + <code>NOW.md</code>.
  </footer>
</div>
<script>{JS.replace("__INTENT_DIR_PLACEHOLDER__", str(INTENT_DIR))}</script>
</body>
</html>
"""


def strip_founder_content(html: str) -> str:
    """Public-mode: remove all elements with class 'founder-only' from the HTML.

    Also strips the Founder button from the mode toggle and defaults body to player mode.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        # Fallback: regex strip (less reliable but works for our pattern)
        # Match <div ... class="...founder-only..."> ... </div> with balanced nesting
        # We emit founder blocks at top level so a stack-based pass is sufficient.
        return _regex_strip_founder(html)

    soup = BeautifulSoup(html, "html.parser")
    for el in soup.find_all(class_="founder-only"):
        el.decompose()
    # Remove Founder button from mode toggle
    for btn in soup.find_all("button", class_="mode-btn"):
        if btn.get("data-mode") == "founder":
            btn.decompose()
    # Default body to player mode (the JS will pick this up via init)
    # We also clear the localStorage default by setting a marker
    body = soup.find("body")
    if body:
        body["data-default-mode"] = "player"
    return str(soup)


def _regex_strip_founder(html: str) -> str:
    """Stack-based <div> removal for elements whose opening tag has class 'founder-only'."""
    out = []
    i = 0
    n = len(html)
    while i < n:
        m = re.search(r'<(\w+)([^>]*\bclass="[^"]*\bfounder-only\b[^"]*")', html[i:])
        if not m:
            out.append(html[i:])
            break
        out.append(html[i:i + m.start()])
        tag = m.group(1)
        # Find the matching close tag balancing nested same-tag pairs
        j = i + m.start()
        depth = 0
        k = j
        while k < n:
            open_m = re.search(rf"<{tag}\b", html[k:])
            close_m = re.search(rf"</{tag}>", html[k:])
            if not close_m:
                k = n
                break
            if open_m and (open_m.start() < close_m.start()):
                depth += 1
                k += open_m.end()
            else:
                if depth == 0:
                    k += close_m.end()
                    break
                depth -= 1
                k += close_m.end()
        i = k
    return "".join(out)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--public", action="store_true",
                    help="Build the public version (strip founder-only content, default to Player mode)")
    ap.add_argument("--out", default=None, help="Output path (default: cockpit-map.html, or dist/index.html in --public)")
    args = ap.parse_args()

    html = render_html()
    if args.public:
        html = strip_founder_content(html)
        # Init body class to mode-player by default in public build
        html = html.replace('<body>', '<body class="mode-player">', 1)

    out = Path(args.out) if args.out else (ROOT / "dist" / "index.html" if args.public else OUT)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}")

    if args.public:
        # Copy poster assets so the relative paths still work
        public_assets = out.parent / "core" / "INTENT" / "assets"
        public_assets.mkdir(parents=True, exist_ok=True)
        src_assets = ROOT / "core" / "INTENT" / "assets"
        if src_assets.exists():
            import shutil
            for png in src_assets.glob("*.png"):
                shutil.copy2(png, public_assets / png.name)
            print(f"copied {len(list(src_assets.glob('*.png')))} poster assets to {public_assets}")


if __name__ == "__main__":
    main()
