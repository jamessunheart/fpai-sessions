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
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  font-size: 14px;
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
            href = f"vscode://file{(SERVICES_DIR / s).resolve()}"
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
<title>FPAI Cockpit Map</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <h1>FPAI Cockpit &mdash; Big Picture</h1>
  <div class="freshness" id="freshness" data-generated="{generated_iso}">
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

  <div class="queue">
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

  <div class="grid">
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

  <div class="grid">
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

  <div class="card full" style="margin-bottom:16px;">
    <h2>Money</h2>
    <h3>Outflow &mdash; proportional</h3>
    {money_bar_svg}
    <h3>Outflow &mdash; detail</h3>
    {render_table(money_rows)}
    <h3>Inflow</h3>
    {render_table(inflow_rows)}
  </div>

  <div class="card full" style="margin-bottom:16px;">
    <h2>What's live now <span style="font-size:12px;font-weight:400;color:var(--muted);">&mdash; status dots probed live on page load</span></h2>
    {render_live_table(live_rows)}
    <p style="color:var(--muted);font-size:11px;margin:12px 0 0;">
      <span class="dot live"></span> reachable &nbsp;
      <span class="dot bad"></span> unreachable &nbsp;
      <span class="dot warn"></span> probe blocked (CORS / private host) &nbsp;
      <span class="dot" style="background:var(--cruft);"></span> no URL to probe
    </p>
  </div>

  <div class="card full" style="margin-bottom:16px;">
    <h2>Services ({n_total} total)</h2>
    <p style="color:var(--muted);margin:0 0 12px;">
      Click a service name to open its directory in your editor (vscode:// link).
      Use the search and tag pills to filter.
    </p>
    {services_html}
  </div>

  <div class="grid">
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
        <a class="svc" href="vscode://file{NOW}"><code>core/STATE/NOW.md</code></a> &mdash; SSOT.<br>
        <a class="svc" href="vscode://file{CATALOG}"><code>core/STATE/catalog.json</code></a> &mdash; service tags.<br>
        <a class="svc" href="vscode://file{ROOT/'STRUCTURE.md'}"><code>STRUCTURE.md</code></a> &mdash; layout.
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
<script>{JS}</script>
</body>
</html>
"""


def main() -> None:
    OUT.write_text(render_html(), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
