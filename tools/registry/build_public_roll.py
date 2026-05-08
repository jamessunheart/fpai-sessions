#!/usr/bin/env python3
"""
build_public_roll.py — Render the public-facing Roll of formed Agreements.

Reads core/INTENT/AGREEMENTS/registry.json and writes a static HTML page
at sites/zenvillage-peace/peace/registry/index.html showing all
Agreements with `public: true`.

Source of truth: registry.json (which is itself derived from individual
Agreement files via build_index.py — never hand-edit).

Usage:
  python tools/registry/build_public_roll.py
  python tools/registry/build_public_roll.py --check    # exit 1 if would change

Status filter: all `public: true` entries are included regardless of
status. Status is displayed visibly so visitors can see proposed vs
active vs repaired Agreements.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_JSON = REPO_ROOT / "core" / "INTENT" / "AGREEMENTS" / "registry.json"
OUTPUT_HTML = REPO_ROOT / "sites" / "zenvillage-peace" / "peace" / "registry" / "index.html"

STATUS_BADGES = {
    "proposed":  ("🟠", "Proposed", "var(--gold)"),
    "active":    ("🟢", "Active", "var(--leaf)"),
    "breached":  ("🔴", "Breached", "var(--rose)"),
    "repairing": ("🟡", "Repairing", "var(--gold)"),
    "repaired":  ("🟢", "Repaired", "var(--teal)"),
    "withdrawn": ("⚪", "Withdrawn", "var(--ink-soft)"),
    "archived":  ("⚫", "Archived", "var(--ink-soft)"),
}

PARTY_TYPE_LABELS = {
    "human":        "person",
    "ai":           "AI agent",
    "organization": "organization",
    "community":    "community",
    "land":         "land",
    "system":       "system",
}


def render_party(p: dict) -> str:
    name = html.escape(str(p.get("name", "—")))
    role = html.escape(str(p.get("role", "")))
    ptype = p.get("party_type", "")
    type_label = PARTY_TYPE_LABELS.get(ptype, ptype)
    type_html = f' <span class="party-type">({html.escape(type_label)})</span>' if type_label else ""
    role_html = f'<div class="party-role">{role}</div>' if role else ""
    return f'<div class="party"><div class="party-name">{name}{type_html}</div>{role_html}</div>'


def render_agreement(a: dict) -> str:
    parties = a.get("parties", [])
    parties_html = "".join(render_party(p) for p in parties) if isinstance(parties, list) else ""

    status = a.get("status", "active")
    emoji, label, color = STATUS_BADGES.get(status, ("•", status, "var(--ink-soft)"))

    date = html.escape(str(a.get("date_formed", "—")))
    context = html.escape(str(a.get("context", "")))
    tags = a.get("scope_tags", [])
    tags_html = ""
    if isinstance(tags, list) and tags:
        tags_html = '<div class="tags">' + "".join(
            f'<span class="tag">{html.escape(str(t))}</span>' for t in tags
        ) + "</div>"

    witness = a.get("witness", {})
    witness_html = ""
    if isinstance(witness, dict) and witness:
        wt = html.escape(str(witness.get("type", "")))
        wr = html.escape(str(witness.get("reference", "")))
        if wt or wr:
            witness_html = f'<div class="witness">witness: <code>{wt}</code> · <code>{wr}</code></div>'

    return f'''
    <article class="agreement">
      <header class="agreement-head">
        <time datetime="{date}">{date}</time>
        <span class="status" style="color: {color};">{emoji} {label}</span>
      </header>
      <div class="parties">{parties_html}</div>
      <p class="context">{context}</p>
      {tags_html}
      {witness_html}
    </article>'''


def build_html(public_agreements: list[dict], totals: dict) -> str:
    agreements_html = "\n".join(render_agreement(a) for a in public_agreements)
    if not public_agreements:
        agreements_html = '<p style="text-align:center;color:var(--ink-soft);font-style:italic;padding:32px;">No public Agreements formed yet. Be the first to sign.</p>'

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover" />
<title>The Roll · World Peace Agreement · Zen Village</title>
<meta name="description" content="The public roll of formed World Peace Agreements. A living index of cooperation between consenting parties under the Coherent Champions of CHRIST Manifesto." />
<meta name="theme-color" content="#1a1530" />

<meta property="og:title" content="The Roll · World Peace Agreement · Zen Village" />
<meta property="og:description" content="A living index of formed Peace Agreements between consenting parties. Coherent Champions of CHRIST." />
<meta property="og:type" content="website" />
<meta property="og:url" content="https://zenvillage.live/peace/registry/" />

<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,400&family=Caveat:wght@500;600&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet" />

<style>
  :root {{
    --ink: #1a1530;
    --ink-soft: #2d2547;
    --paper: #f6f1ea;
    --paper-warm: #efe6d8;
    --gold: #c89b3c;
    --gold-soft: #e8c87a;
    --rose: #d97a7a;
    --lilac: #9b7cc7;
    --lilac-soft: #c8b5e0;
    --teal: #4f9d94;
    --teal-soft: #9ec9c2;
    --leaf: #6b8e5a;
    --line: rgba(26,21,48,.12);
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--ink);
    background: var(--paper);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    overflow-x: hidden;
  }}
  body::before {{
    content:"";
    position: fixed; inset: 0;
    background:
      radial-gradient(1200px 800px at 90% -10%, rgba(155,124,199,.18), transparent 60%),
      radial-gradient(900px 700px at -10% 30%, rgba(79,157,148,.15), transparent 60%),
      radial-gradient(700px 600px at 50% 110%, rgba(217,122,122,.12), transparent 60%);
    pointer-events: none;
    z-index: 0;
  }}
  main {{ position: relative; z-index: 1; }}
  .container {{ max-width: 920px; margin: 0 auto; padding: 0 24px; }}

  .hero {{ padding: 72px 24px 32px; text-align: center; }}
  .eyebrow {{
    font-family: 'Cormorant Garamond', serif;
    font-style: italic;
    letter-spacing: .35em;
    text-transform: uppercase;
    font-size: 12px;
    color: var(--lilac);
    margin: 0 0 16px;
  }}
  h1 {{
    font-family: 'Cormorant Garamond', serif;
    font-weight: 400;
    font-style: italic;
    font-size: clamp(48px, 9vw, 96px);
    line-height: .95;
    letter-spacing: -.01em;
    margin: 0 0 14px;
    background: linear-gradient(120deg, #b56cc4 0%, #7e7ec4 35%, #4f9d94 70%, #6b8e5a 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }}
  .lede {{
    font-family: 'Cormorant Garamond', serif;
    font-style: italic;
    font-size: clamp(18px, 2.4vw, 22px);
    color: var(--ink-soft);
    max-width: 640px;
    margin: 0 auto;
  }}

  .stats {{
    display: flex; gap: 36px; flex-wrap: wrap; justify-content: center;
    padding: 24px 24px 16px;
    font-size: 14px;
    color: var(--ink-soft);
    letter-spacing: .15em;
    text-transform: uppercase;
  }}
  .stats strong {{ color: var(--ink); font-size: 22px; font-family: 'Cormorant Garamond', serif; font-weight: 500; }}
  .stat {{ display: flex; flex-direction: column; align-items: center; gap: 4px; }}

  .roll {{ padding: 48px 24px 80px; }}
  .roll-list {{ display: grid; gap: 24px; max-width: 720px; margin: 0 auto; }}

  .agreement {{
    background: rgba(255,255,255,.6);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    padding: 28px 28px 24px;
    border: 1px solid var(--line);
    box-shadow: 0 20px 40px -25px rgba(26,21,48,.18);
  }}
  .agreement-head {{
    display: flex; justify-content: space-between; align-items: baseline; gap: 16px;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px dashed var(--line);
  }}
  .agreement-head time {{
    font-family: 'Cormorant Garamond', serif;
    font-weight: 500;
    font-size: 18px;
    color: var(--ink);
  }}
  .agreement-head .status {{
    font-size: 13px;
    letter-spacing: .15em;
    text-transform: uppercase;
    font-weight: 500;
    white-space: nowrap;
  }}

  .parties {{ display: grid; gap: 12px; margin-bottom: 14px; }}
  .party {{
    padding: 12px 16px;
    background: rgba(255,255,255,.5);
    border-radius: 12px;
    border-left: 3px solid var(--gold);
  }}
  .party-name {{
    font-family: 'Cormorant Garamond', serif;
    font-size: 18px;
    font-weight: 500;
    color: var(--ink);
  }}
  .party-type {{
    font-size: 12px;
    color: var(--ink-soft);
    font-style: italic;
    font-family: 'Inter', sans-serif;
    font-weight: 400;
    letter-spacing: 0;
  }}
  .party-role {{ font-size: 13px; color: var(--ink-soft); margin-top: 2px; }}

  .context {{
    font-size: 14px;
    color: var(--ink-soft);
    margin: 8px 0 12px;
    font-family: 'Cormorant Garamond', serif;
    font-style: italic;
    font-size: 16px;
  }}

  .tags {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
  .tag {{
    font-size: 11px;
    letter-spacing: .12em;
    text-transform: uppercase;
    background: rgba(155,124,199,.15);
    color: var(--lilac);
    padding: 3px 10px;
    border-radius: 999px;
  }}

  .witness {{ font-size: 12px; color: var(--ink-soft); margin-top: 8px; opacity: .7; }}
  .witness code {{ background: rgba(0,0,0,.05); padding: 1px 6px; border-radius: 4px; font-size: 11px; }}

  .cta-back {{
    text-align: center;
    padding: 24px;
  }}
  .cta {{
    display: inline-flex; align-items: center; gap: 10px;
    padding: 14px 28px;
    background: var(--ink);
    color: var(--paper);
    text-decoration: none;
    border-radius: 999px;
    font-weight: 500;
    letter-spacing: .12em;
    text-transform: uppercase;
    font-size: 12px;
    transition: transform .2s ease, background .2s ease;
    box-shadow: 0 10px 30px -10px rgba(26,21,48,.5);
  }}
  .cta:hover {{ transform: translateY(-2px); background: var(--ink-soft); }}
  .cta.secondary {{
    background: transparent;
    color: var(--ink);
    border: 1px solid var(--ink);
    box-shadow: none;
    margin-left: 12px;
  }}
  .cta.secondary:hover {{ background: var(--ink); color: var(--paper); }}

  footer {{
    text-align: center;
    padding: 32px 24px 48px;
    font-size: 13px;
    color: var(--ink-soft);
    border-top: 1px solid var(--line);
    background: rgba(255,255,255,.4);
  }}
  footer a {{ color: var(--ink); text-decoration: none; border-bottom: 1px solid var(--gold); }}
  footer .also {{ font-family: 'Caveat', cursive; font-size: 18px; color: var(--lilac); margin-top: 6px; }}
</style>
</head>
<body>
<main>

  <section class="hero">
    <div class="container">
      <p class="eyebrow">Coherent Champions of CHRIST</p>
      <h1>The Roll</h1>
      <p class="lede">
        A living index of formed World Peace Agreements between consenting parties.<br/>
        Each Agreement is renewed by being lived, not by being re-signed.
      </p>
    </div>
  </section>

  <section class="stats">
    <div class="stat"><strong>{totals['total']}</strong>Total</div>
    <div class="stat"><strong>{totals['active']}</strong>Active</div>
    <div class="stat"><strong>{totals['proposed']}</strong>Proposed</div>
    <div class="stat"><strong>{totals['parties']}</strong>Parties</div>
  </section>

  <section class="roll">
    <div class="roll-list">
      {agreements_html}
    </div>
  </section>

  <div class="cta-back">
    <a class="cta" href="/peace/#manifesto">Read the Manifesto</a>
    <a class="cta secondary" href="/peace/">Back to Zen Village</a>
  </div>

</main>

<footer>
  <p>
    Coherent Champions of CHRIST · Zen Village · Costa Rica ·
    <a href="https://zenvillagecr.com" target="_blank" rel="noopener">zenvillagecr.com</a>
  </p>
  <p class="also">peace must become visible through action ✿</p>
</footer>
</body>
</html>
'''


def main() -> int:
    check_only = "--check" in sys.argv
    if not REGISTRY_JSON.exists():
        sys.stderr.write(f"ERROR: {REGISTRY_JSON} not found. Run build_index.py first.\n")
        return 2

    data = json.loads(REGISTRY_JSON.read_text(encoding="utf-8"))
    all_agreements = data.get("agreements", [])
    public_agreements = [a for a in all_agreements if a.get("public", False)]

    # Sort: active first, then proposed, then everything else; within each, most recent first
    status_order = {"active": 0, "proposed": 1, "repairing": 2, "repaired": 3, "breached": 4, "withdrawn": 5, "archived": 6}
    public_agreements.sort(key=lambda a: (status_order.get(a.get("status", "active"), 9), -ord_date(a.get("date_formed", ""))))

    # Stats
    parties = set()
    for a in public_agreements:
        for p in a.get("parties", []):
            if isinstance(p, dict):
                parties.add(p.get("name", ""))
    totals = {
        "total":    len(public_agreements),
        "active":   sum(1 for a in public_agreements if a.get("status") == "active"),
        "proposed": sum(1 for a in public_agreements if a.get("status") == "proposed"),
        "parties":  len(parties),
    }

    new_html = build_html(public_agreements, totals)

    if check_only:
        old_html = OUTPUT_HTML.read_text(encoding="utf-8") if OUTPUT_HTML.exists() else ""
        if old_html != new_html:
            sys.stderr.write("Public roll would change. Run without --check to update.\n")
            return 1
        return 0

    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(new_html, encoding="utf-8")
    print(f"Wrote {OUTPUT_HTML.relative_to(REPO_ROOT)}  ({len(public_agreements)} public agreements, {len(parties)} parties)")
    return 0


def ord_date(s: str) -> int:
    """Convert YYYY-MM-DD to int for sorting; bad input sorts last."""
    s = str(s)
    try:
        parts = s.split("-")
        if len(parts) == 3:
            return int(parts[0]) * 10000 + int(parts[1]) * 100 + int(parts[2])
    except (ValueError, IndexError):
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
