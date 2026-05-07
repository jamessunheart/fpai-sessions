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

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

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
  <div class="subtitle">
    Generated {now_str} from <code>core/STATE/NOW.md</code> + <code>core/STATE/catalog.json</code>.
    Re-run <code>python3 tools/gen_cockpit_map.py</code> to refresh.
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
      <div class="kpi-label">Services tagged</div>
      <div class="kpi">{n_tagged}<span style="font-size:14px;color:var(--muted);"> / {n_total}</span></div>
      <p style="color:var(--muted);margin:8px 0 0;">
        {n_untagged} untagged (decision candidates). 138+ tagged <span class='badge cruft'>cruft</span>.
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
    <h3>Outflow</h3>
    {render_table(money_rows)}
    <h3>Inflow</h3>
    {render_table(inflow_rows)}
  </div>

  <div class="card full" style="margin-bottom:16px;">
    <h2>What's live now</h2>
    {render_table(live_rows)}
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
      <h2>Recent commits</h2>
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
