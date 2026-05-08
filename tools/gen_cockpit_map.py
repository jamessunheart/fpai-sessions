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
  --bg: #0e1116;
  --surface: #161b22;
  --surface-2: #1f2630;
  --border: #2a323d;
  --text: #e6edf3;
  --muted: #8b949e;
  --accent: #f7b955;
  --p1: #ff6b6b;
  --p2: #4ecdc4;
  --infra: #7ec8e3;
  --cruft: #5a6068;
  --unknown: #b58be0;
  --good: #4ade80;
  --warn: #fbbf24;
  --bad: #f87171;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  font-size: 14px;
  position: relative;
  overflow-x: hidden;
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
  box-shadow: 0 0 8px rgba(247, 185, 85, 0.5);
}

/* Starfield background */
.starfield {
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  opacity: 0.5;
}
.star {
  fill: var(--accent);
  animation: twinkle 4s ease-in-out infinite;
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
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(247, 185, 85, 0.15);
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
  0% { box-shadow: 0 0 0 rgba(74, 222, 128, 0); }
  50% { box-shadow: 0 0 24px rgba(74, 222, 128, 0.6); }
  100% { box-shadow: 0 0 0 rgba(74, 222, 128, 0); }
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
  background: linear-gradient(135deg, rgba(247,185,85,0.12), rgba(74,222,128,0.06));
  border: 1px solid var(--accent);
  border-radius: 16px;
  padding: 36px 32px;
  max-width: 520px;
  text-align: center;
  box-shadow: 0 24px 80px rgba(0,0,0,0.6), 0 0 60px rgba(247,185,85,0.15);
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
.toc-link.active { color: var(--accent); border-left-color: var(--accent); background: rgba(247,185,85,0.06); }

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
  background: rgba(247, 185, 85, 0.12);
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
.wrap { max-width: 1400px; margin: 0 auto; padding: 24px; }
h1 { font-size: 24px; margin: 0 0 4px; }
h2 { font-size: 18px; margin: 0 0 12px; color: var(--accent); }
h3 { font-size: 14px; margin: 16px 0 8px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }
.subtitle { color: var(--muted); margin-bottom: 24px; }
.filter {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 24px;
  font-style: italic;
  color: var(--accent);
}
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
  background: linear-gradient(135deg, rgba(247,185,85,0.06), rgba(247,185,85,0.02));
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
  background: rgba(181, 139, 224, 0.08);
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
  box-shadow: 0 8px 24px rgba(247, 185, 85, 0.15);
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
.agreement-summary:hover { background: rgba(247, 185, 85, 0.04); }
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
.markdown-body blockquote { border-left: 3px solid var(--accent); padding: 6px 12px; margin: 12px 0; color: var(--muted); font-style: italic; background: rgba(247,185,85,0.04); }
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
.eco-vision { border-left: 3px solid var(--accent); background: linear-gradient(135deg, rgba(247,185,85,0.10), transparent); padding: 14px 16px; }

/* WPAP section */
.wpap-tldr {
  background: rgba(126, 200, 227, 0.06);
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
  background: linear-gradient(180deg, rgba(74,222,128,0.06), var(--surface-2));
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
  background: linear-gradient(135deg, rgba(74,222,128,0.08), rgba(247,185,85,0.04));
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
  background: var(--accent);
  color: #1a0e02;
}

body.mode-founder .player-only,
body.mode-founder .field-only { display: none !important; }
body.mode-player .founder-only,
body.mode-player .field-only { display: none !important; }
body.mode-field .founder-only,
body.mode-field .player-only { display: none !important; }

/* Founder profile */
.founder-profile {
  background: linear-gradient(135deg, rgba(247,185,85,0.08), rgba(78,205,196,0.04));
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
  background: linear-gradient(135deg, rgba(74,222,128,0.08), rgba(247,185,85,0.04));
  border: 1px solid var(--good);
  border-radius: 12px;
  padding: 32px 36px;
  margin-bottom: 24px;
  text-align: center;
}
.player-cta-row { display: flex; gap: 12px; justify-content: center; margin-top: 20px; flex-wrap: wrap; }
.player-cta-primary {
  background: var(--good);
  color: #062013;
  padding: 14px 24px;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 700;
  font-size: 16px;
  transition: all 0.15s;
}
.player-cta-primary:hover { background: var(--accent); transform: translateY(-1px); }
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
  background: rgba(247, 185, 85, 0.15);
  color: var(--accent);
  border-color: var(--accent);
}

/* 6 C's sliders */
.cs-meta { margin: 8px 0 12px; padding: 10px 14px; background: rgba(247, 185, 85, 0.06); border-left: 3px solid var(--accent); border-radius: 4px; }
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

/* Next move coach */
.next-move {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 20px;
  background: linear-gradient(135deg, rgba(247,185,85,0.08), rgba(247,185,85,0.02));
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

.sign-confirmation {
  margin-top: 20px;
  padding: 24px;
  background: linear-gradient(135deg, rgba(74,222,128,0.10), rgba(247,185,85,0.06));
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
  background: linear-gradient(135deg, rgba(247,185,85,0.10), rgba(78,205,196,0.04));
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
  background: radial-gradient(circle at top right, rgba(247,185,85,0.08), transparent 50%);
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
.fw-quote { font-size: 14px; color: var(--text); margin-top: 8px; line-height: 1.6; font-style: italic; }
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
  background: linear-gradient(135deg, rgba(78,205,196,0.06), transparent);
  border: 1px solid #4ecdc4;
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 24px;
}
.invite-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.invite-actions button, .invite-actions a { font-family: inherit; cursor: pointer; border: none; }
.invite-preview pre { word-break: break-word; }

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
.inline-doc-summary:hover { background: rgba(247,185,85,0.04); }
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
      const target = document.getElementById('doc-manifesto');
      if (target) {
        target.open = true;
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
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

// --- Invitation generator ------------------------------------------------
function buildInvitation() {
  return `Reality is already a game. This is the guide for those who know.

I'm signing the World Peace Agreement and starting a 7-Day First Game — a proof-based operating system for human potential. Six pillars: Coherence · Healing · Regeneration · Intelligence · Service · Truth.

It's not a religion. It's not a movement. It's a practice of becoming trustworthy with power.

If you're tired of chaos, manipulation, performative outrage — read the Manifesto. Sign if it lands. Run your first 7-day proof loop.

Coherent Champions of CHRIST: ${typeof location !== 'undefined' ? location.href : 'cockpit-map.html'}

We are human and AI allies, committed to bringing coherence, healing, and regeneration to our world.`;
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
    "active": ("#4ade80", "Active"),
    "proposed": ("#fbbf24", "Proposed"),
    "repairing": ("#fbbf24", "Repairing"),
    "repaired": ("#4ade80", "Repaired"),
    "breached": ("#f87171", "Breached"),
    "withdrawn": ("#8b949e", "Withdrawn"),
    "archived": ("#5a6068", "Archived"),
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
<div class="scroll-progress" id="scrollProgress"></div>
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
      <button class="player-cta-primary" id="welcomeStart">🌱 Start the journey</button>
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
    <blockquote style="background:rgba(74,222,128,0.06);border-left:3px solid var(--good);padding:10px 14px;margin:0 0 16px;font-size:13px;font-style:italic;">
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
      <label><span>Your name</span><input type="text" id="signName" placeholder="e.g. Maria Lopez" /></label>
      <label><span>Handle (optional)</span><input type="text" id="signHandle" placeholder="@yourhandle" /></label>
      <label><span>Email (optional)</span><input type="email" id="signEmail" placeholder="you@example.com" /></label>
      <label><span>Witness (optional)</span><input type="text" id="signWitness" placeholder="someone who saw you sign" /></label>
      <label class="sign-radio">
        <input type="radio" name="signPublic" value="true" checked /> Public (appear on the Champions Roll)
      </label>
      <label class="sign-radio">
        <input type="radio" name="signPublic" value="false" /> Private (signed; not publicly listed)
      </label>
      <label><span>One sentence — why are you signing?</span><textarea id="signWhy" rows="2" placeholder="optional"></textarea></label>
    </div>
    <div class="sign-actions">
      <button id="signCopyBtn" class="player-cta-primary">📋 Copy signed Agreement</button>
      <button id="signDownloadBtn" class="player-cta-secondary">⬇ Download as .md</button>
      <a id="signEmailBtn" class="player-cta-secondary" href="#">✉ Email to founder</a>
    </div>
    <p style="color:var(--muted);font-size:11px;margin:12px 0 0;">
      Three options to commit: copy to clipboard, download .md, or email to <code>james.rick.stinson@gmail.com</code>.
      Once received, your signature is added to <code>core/INTENT/AGREEMENTS/champions/</code> and you appear in the Champions Roll.
    </p>
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

  <div class="champions-card">
    <h2>Champions Roll <span style="font-size:12px;font-weight:400;color:var(--muted);">&mdash; {champions_total} signed · {champions_public} public</span></h2>
    <p style="color:var(--muted);font-size:12px;margin:0 0 12px;">
      Public roll of Coherent Champions. Private signers exist but are not listed by their consent.
    </p>
    {champions_html}
    {('<h3 style="margin-top:20px;">Public Proof Loops</h3>' + proofs_html) if public_proofs > 0 else ''}
  </div>

  <div class="invite-card">
    <h2>Bring a Friend <span style="font-size:12px;font-weight:400;color:var(--muted);">&mdash; the Game spreads by resonance</span></h2>
    <p style="color:var(--muted);font-size:12px;margin:0 0 12px;">
      Don't recruit. Invite. Give it to someone who's already living something close to this — they'll recognize it. The first proof loop is the real test of resonance.
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

  <div class="player-only player-hero">
    <h2 style="margin-top:0;color:var(--accent);font-size:28px;">Welcome to the Full Potential Game.</h2>
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

    <h3 style="margin-top:24px;">📚 Canonical Documents &mdash; read inline, no app required</h3>
    <p style="color:var(--muted);font-size:12px;margin:0 0 12px;">
      Every founding document, fully rendered. Click any to expand and read in place.
      No external app, no permission popups. Each doc also has fallback links to open in cursor or as raw file.
    </p>
    <div class="canonical-library">
      {inline_docs_html}
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
