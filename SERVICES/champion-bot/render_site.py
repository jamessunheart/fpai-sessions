#!/usr/bin/env python3
"""render_site.py — render a Champion's landing page from their yaml config.

Usage:
  python3 render_site.py <slug>
  # reads core/CHAMPIONS/<slug>.yaml
  # writes sites/<slug>/index.html

Or:
  python3 render_site.py <slug> --out /tmp/foo.html

The renderer is pure Python — no template files. The "template" is this
script. Edit the HTML below to change the design for ALL Champions at once;
edit the yaml to change one Champion.
"""
from __future__ import annotations

import argparse
import sys
from html import escape
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CHAMPIONS_DIR = REPO_ROOT / "core" / "CHAMPIONS"
SITES_DIR = REPO_ROOT / "sites"


def e(s) -> str:
    """HTML-escape a string. None → empty."""
    if s is None:
        return ""
    return escape(str(s), quote=True)


def has_todos(text: str) -> bool:
    return "TODO" in text


def render(cfg: dict) -> str:
    slug = cfg["slug"]
    name = cfg["name"]
    short = cfg.get("short_name", name.split()[0])
    brand_first = cfg.get("brand_first", short)
    brand_second = cfg.get("brand_second", "")
    domain = cfg.get("domain", f"{slug}.com")
    title = cfg.get("title", name)
    description = cfg.get("description", "")

    bot_username = cfg.get("bot_username", "")
    bot_persona = cfg.get("bot_persona_name", short)

    theme = cfg.get("theme") or {}
    ink = theme.get("ink", "#0b0a1a")
    accent = theme.get("accent", "#3b5bdb")
    accent_soft = theme.get("accent_soft", "#6f8cf0")
    gold = theme.get("gold", "#c89b3c")
    gold_soft = theme.get("gold_soft", "#e8c87a")

    tagline = cfg.get("tagline", "")
    hero_headline_html = cfg.get("hero_headline_html", "")
    hero_lede = cfg.get("hero_lede", "")
    hero_cta_label = cfg.get("hero_cta_label", f"Talk to {bot_persona}")

    philosophy_quote = cfg.get("philosophy_quote", "")

    method_name = cfg.get("method_name", "")
    method_lede = cfg.get("method_lede", "")
    pillars = cfg.get("pillars") or []

    offerings_lede = cfg.get("offerings_lede", "")
    offerings = cfg.get("offerings") or []

    about_eyebrow = cfg.get("about_eyebrow", "about")
    about_headline_html = cfg.get("about_headline_html", "")
    about_paragraphs = cfg.get("about_paragraphs") or []
    about_signature = cfg.get("about_signature", f"— {short}")
    about_portrait_image = cfg.get("about_portrait_image", "img/accent-1.jpg")

    lineage_filled = cfg.get("lineage_filled", False)
    lineage_intro = cfg.get("lineage_intro", "")
    lineage_paragraphs = cfg.get("lineage_paragraphs") or []

    process_steps = cfg.get("process_steps") or []
    testimonials = cfg.get("testimonials") or []
    faq = cfg.get("faq") or []

    closing_headline_html = cfg.get("closing_headline_html", "")
    closing_body = cfg.get("closing_body", "")

    instagram_handle = cfg.get("instagram_handle", "")
    footer_attr = cfg.get("footer_attribution", f"© {name}")

    # Bot deep-link
    bot_url = f"https://t.me/{bot_username}" if bot_username else "#"

    # Pillars HTML
    pillars_html = "\n".join(
        f"""<div class="pillar">
          <div class="symbol">{e(p.get('num', ''))}</div>
          <h4>{e(p.get('title', ''))}</h4>
          <p>{e(p.get('body', ''))}</p>
        </div>"""
        for p in pillars
    ) or '<p style="color:var(--muted);text-align:center;">Methodology pending.</p>'

    # Offerings HTML
    offering_blocks = []
    for o in offerings:
        feats = "\n".join(f"<li>{e(f)}</li>" for f in (o.get("features") or []))
        intent = o.get("bot_intent", "")
        offer_url = f"{bot_url}?start={intent}" if intent and bot_username else bot_url
        offering_blocks.append(f"""
        <article class="offering">
          <div class="img">
            <img src="{e(o.get('image', 'img/offering.jpg'))}" alt="" loading="lazy" width="1000" height="750" />
          </div>
          <div class="body">
            <span class="tag">{e(o.get('tag', ''))}</span>
            <h3>{e(o.get('title', ''))}</h3>
            <span class="selectivity">{e(o.get('selectivity', ''))}</span>
            <p class="price">{e(o.get('price', ''))}</p>
            <p>{e(o.get('description', ''))}</p>
            <ul class="features">{feats}</ul>
            <a class="cta-link" href="{e(offer_url)}" target="_blank" rel="noopener">{e(o.get('cta_label', f'Inquire via {bot_persona}'))} →</a>
          </div>
        </article>""")
    offerings_html = "\n".join(offering_blocks) or '<p style="color:var(--muted);text-align:center;">Offerings pending.</p>'

    # About paragraphs
    about_paras_html = "\n".join(f"<p>{e(p)}</p>" for p in about_paragraphs)

    # Lineage HTML — either filled-in paragraphs or placeholder
    if lineage_filled and lineage_paragraphs:
        lineage_body = "\n".join(f"<p>{e(p)}</p>" for p in lineage_paragraphs)
    else:
        lineage_body = f"""<p>{e(lineage_intro) or 'Lineage to be named.'}</p>
        <div class="placeholder">
          ✦ Editorial placeholder — fill in with {e(short)}'s actual training:<br />
          • Primary teacher(s) and tradition(s) held<br />
          • Years of practice + years teaching<br />
          • Notable retreats / certifications / initiations<br />
          • One sentence on what they carry from each lineage forward
        </div>"""

    # Process steps
    process_html = "\n".join(f"""
        <div class="step">
          <div class="num">{e(s.get('num', ''))}</div>
          <h4>{e(s.get('title', ''))}</h4>
          <p>{e(s.get('body', ''))}</p>
        </div>""" for s in process_steps) or ""

    # Testimonials
    testimonials_html = "\n".join(f"""
        <div class="testimonial">
          <blockquote>{e(t.get('quote', ''))}</blockquote>
          <cite>{e(t.get('attribution', ''))}</cite>
        </div>""" for t in testimonials) or ""

    # FAQ
    faq_html = "\n".join(f"""
        <details>
          <summary>{e(f.get('q', ''))}</summary>
          <p>{e(f.get('a', ''))}</p>
        </details>""" for f in faq) or ""

    # Footer instagram link (only if handle filled)
    ig_html = (
        f'<a href="https://www.instagram.com/{e(instagram_handle)}/" target="_blank" rel="noopener">Instagram</a>'
        if instagram_handle and not has_todos(instagram_handle)
        else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover" />
<title>{e(title)}</title>
<meta name="description" content="{e(description)}" />
<meta name="theme-color" content="{e(ink)}" />

<meta property="og:title" content="{e(title)}" />
<meta property="og:description" content="{e(description)}" />
<meta property="og:type" content="website" />
<meta property="og:url" content="https://{e(domain)}" />

<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet" />

<style>
  :root {{
    --ink: {e(ink)};
    --ink-soft: #16142a;
    --ink-line: rgba(255,255,255,.08);
    --paper: #f6f1ea;
    --accent: {e(accent)};
    --accent-soft: {e(accent_soft)};
    --accent-glow: rgba(111,140,240,.22);
    --gold: {e(gold)};
    --gold-soft: {e(gold_soft)};
    --muted: rgba(246,241,234,.7);
    --muted-2: rgba(246,241,234,.5);
  }}
  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; color: var(--paper); background: var(--ink); line-height: 1.65; -webkit-font-smoothing: antialiased; overflow-x: hidden; font-size: 17px; }}
  body::before {{ content: ""; position: fixed; inset: 0; background: radial-gradient(900px 700px at 85% -10%, rgba(59,91,219,.18), transparent 65%), radial-gradient(800px 700px at -10% 40%, rgba(200,155,60,.10), transparent 60%), radial-gradient(600px 500px at 50% 110%, rgba(217,122,142,.10), transparent 60%); pointer-events: none; z-index: 0; }}
  body::after {{ content: ""; position: fixed; inset: 0; background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0.04 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>"); pointer-events: none; mix-blend-mode: screen; opacity: .6; z-index: 0; }}
  main, header, footer {{ position: relative; z-index: 1; }}
  .container {{ max-width: 980px; margin: 0 auto; padding: 0 24px; }}

  .topbar {{ padding: 18px 24px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--ink-line); backdrop-filter: blur(6px); background: rgba(11,10,26,.6); position: sticky; top: 0; z-index: 10; }}
  .brand {{ display: inline-flex; align-items: center; gap: 10px; font-family: 'Cormorant Garamond', serif; font-size: 22px; letter-spacing: .04em; color: var(--paper); text-decoration: none; font-weight: 500; }}
  .brand img {{ height: 36px; width: auto; filter: brightness(0) invert(1); opacity: .9; }}
  .brand em {{ color: var(--accent-soft); font-style: normal; }}
  .topbar nav {{ display: flex; gap: 24px; align-items: center; }}
  .topbar nav a {{ color: var(--muted); text-decoration: none; font-size: 14px; letter-spacing: .04em; transition: color .2s; }}
  .topbar nav a:hover {{ color: var(--paper); }}
  .topbar .cta {{ background: var(--accent); color: white; padding: 9px 16px; border-radius: 999px; font-weight: 500; font-size: 14px; border: 1px solid var(--accent-soft); transition: transform .15s, box-shadow .15s; }}
  .topbar .cta:hover {{ color: white; transform: translateY(-1px); box-shadow: 0 8px 24px var(--accent-glow); }}
  @media (max-width: 720px) {{ .topbar nav a:not(.cta) {{ display: none; }} }}

  .hero {{ position: relative; min-height: 88vh; display: flex; align-items: center; justify-content: center; padding: 120px 24px 80px; overflow: hidden; text-align: center; }}
  .hero-bg {{ position: absolute; inset: 0; z-index: 0; }}
  .hero-bg img {{ width: 100%; height: 100%; object-fit: cover; object-position: center 25%; filter: saturate(1.05) contrast(1.05); }}
  .hero-bg::after {{ content: ""; position: absolute; inset: 0; background: linear-gradient(180deg, rgba(11,10,26,.55) 0%, rgba(11,10,26,.35) 40%, rgba(11,10,26,.92) 100%), radial-gradient(800px 600px at 70% 30%, rgba(59,91,219,.18), transparent 60%); }}
  .hero .container {{ position: relative; z-index: 1; }}
  .hero .eyebrow {{ font-family: 'Cormorant Garamond', serif; font-style: italic; font-size: 18px; color: var(--accent-soft); letter-spacing: .12em; margin-bottom: 18px; text-transform: lowercase; text-shadow: 0 2px 12px rgba(11,10,26,.6); }}
  .hero h1 {{ font-family: 'Cormorant Garamond', serif; font-weight: 400; font-size: clamp(40px, 7vw, 78px); line-height: 1.05; margin: 0 0 24px; letter-spacing: -.01em; text-shadow: 0 4px 24px rgba(11,10,26,.6); }}
  .hero h1 em {{ font-style: italic; color: var(--gold-soft); }}
  .hero p.lede {{ font-size: clamp(17px, 2vw, 20px); color: var(--paper); max-width: 620px; margin: 0 auto 36px; text-shadow: 0 2px 12px rgba(11,10,26,.6); }}

  .cta-row {{ display: flex; gap: 14px; justify-content: center; flex-wrap: wrap; margin-top: 8px; }}
  .btn {{ display: inline-flex; align-items: center; gap: 10px; padding: 14px 26px; border-radius: 999px; text-decoration: none; font-weight: 500; font-size: 15px; letter-spacing: .02em; border: 1px solid transparent; transition: transform .15s, box-shadow .2s, background .2s; }}
  .btn-primary {{ background: var(--accent); color: white; border-color: var(--accent-soft); box-shadow: 0 12px 32px var(--accent-glow); }}
  .btn-primary:hover {{ transform: translateY(-1px); box-shadow: 0 16px 40px var(--accent-glow); }}
  .btn-ghost {{ background: transparent; color: var(--paper); border-color: rgba(246,241,234,.25); }}
  .btn-ghost:hover {{ background: rgba(246,241,234,.06); border-color: rgba(246,241,234,.45); }}
  .btn .arrow {{ transition: transform .15s; }}
  .btn:hover .arrow {{ transform: translateX(3px); }}

  .bot-note {{ margin-top: 22px; font-size: 13px; color: var(--muted-2); font-style: italic; }}
  .bot-note strong {{ color: var(--gold-soft); font-style: normal; font-weight: 500; }}

  section.block {{ padding: 72px 24px; }}
  section.block.tight {{ padding: 48px 24px; }}
  .section-eyebrow {{ font-family: 'Cormorant Garamond', serif; font-style: italic; font-size: 16px; color: var(--accent-soft); letter-spacing: .12em; text-align: center; margin-bottom: 12px; }}
  h2 {{ font-family: 'Cormorant Garamond', serif; font-weight: 400; font-size: clamp(30px, 4.5vw, 44px); line-height: 1.1; text-align: center; margin: 0 0 18px; letter-spacing: -.005em; }}
  h2 em {{ font-style: italic; color: var(--gold-soft); }}
  .section-lede {{ text-align: center; color: var(--muted); max-width: 640px; margin: 0 auto 48px; font-size: 17px; }}

  .philosophy p {{ font-family: 'Cormorant Garamond', serif; font-size: clamp(20px, 2.4vw, 26px); font-weight: 300; line-height: 1.45; color: var(--paper); text-align: center; max-width: 760px; margin: 0 auto; font-style: italic; }}
  .philosophy p::before, .philosophy p::after {{ content: "✦"; color: var(--gold); margin: 0 14px; font-style: normal; font-size: .7em; vertical-align: middle; }}

  .pillars {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-top: 16px; }}
  @media (max-width: 720px) {{ .pillars {{ grid-template-columns: 1fr; }} }}
  .pillar {{ border: 1px solid var(--ink-line); border-radius: 14px; padding: 32px 26px; background: linear-gradient(180deg, rgba(255,255,255,.025), rgba(255,255,255,.005)); text-align: left; position: relative; }}
  .pillar .symbol {{ font-family: 'Cormorant Garamond', serif; font-style: italic; color: var(--gold-soft); font-size: 18px; letter-spacing: .15em; margin-bottom: 8px; text-transform: uppercase; }}
  .pillar h4 {{ font-family: 'Cormorant Garamond', serif; font-weight: 500; font-size: 32px; margin: 0 0 14px; color: var(--paper); }}
  .pillar p {{ color: var(--muted); font-size: 15px; margin: 0; line-height: 1.65; }}

  .selectivity {{ display: inline-block; margin-top: 8px; margin-bottom: 14px; padding: 4px 12px; border: 1px solid rgba(200,155,60,.35); border-radius: 999px; font-size: 11px; color: var(--gold-soft); letter-spacing: .12em; text-transform: uppercase; }}

  .lineage {{ max-width: 780px; margin: 0 auto; text-align: center; }}
  .lineage p {{ color: var(--muted); font-size: 17px; margin: 0 0 14px; }}
  .lineage .placeholder {{ border: 1px dashed rgba(200,155,60,.35); border-radius: 10px; padding: 22px 24px; margin-top: 24px; color: var(--gold-soft); font-size: 14px; font-style: italic; text-align: left; }}

  .offerings {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-top: 8px; }}
  .offering {{ background: linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,.01)); border: 1px solid var(--ink-line); border-radius: 18px; overflow: hidden; display: flex; flex-direction: column; transition: border-color .2s, transform .2s; }}
  .offering:hover {{ border-color: rgba(111,140,240,.35); transform: translateY(-2px); }}
  .offering .img {{ aspect-ratio: 4 / 3; width: 100%; overflow: hidden; position: relative; background: var(--ink-soft); }}
  .offering .img img {{ width: 100%; height: 100%; object-fit: cover; transition: transform .6s ease; }}
  .offering:hover .img img {{ transform: scale(1.04); }}
  .offering .img::after {{ content: ""; position: absolute; inset: 0; background: linear-gradient(180deg, transparent 50%, rgba(11,10,26,.55) 100%); }}
  .offering .body {{ padding: 26px 26px 28px; display: flex; flex-direction: column; flex: 1; }}
  .offering .tag {{ font-size: 11px; letter-spacing: .15em; color: var(--accent-soft); text-transform: uppercase; margin-bottom: 12px; }}
  .offering h3 {{ font-family: 'Cormorant Garamond', serif; font-weight: 500; font-size: 26px; margin: 0 0 8px; }}
  .offering .price {{ font-size: 14px; color: var(--gold-soft); margin-bottom: 14px; font-family: 'Cormorant Garamond', serif; font-style: italic; }}
  .offering p {{ color: var(--muted); font-size: 15px; margin: 0 0 16px; flex: 1; }}
  .offering .features {{ list-style: none; padding: 0; margin: 0 0 22px; }}
  .offering .features li {{ font-size: 14px; color: var(--muted); padding: 5px 0 5px 22px; position: relative; }}
  .offering .features li::before {{ content: "✦"; color: var(--gold); position: absolute; left: 0; top: 5px; font-size: 12px; }}
  .offering .cta-link {{ color: var(--accent-soft); text-decoration: none; font-size: 14px; font-weight: 500; margin-top: auto; align-self: flex-start; border-bottom: 1px solid transparent; transition: border-color .2s, color .2s; }}
  .offering .cta-link:hover {{ border-bottom-color: var(--accent-soft); color: var(--paper); }}

  .process {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 24px; margin-top: 16px; }}
  .step {{ text-align: center; padding: 28px 18px; }}
  .step .num {{ font-family: 'Cormorant Garamond', serif; font-style: italic; font-size: 36px; color: var(--gold-soft); margin-bottom: 10px; }}
  .step h4 {{ font-family: 'Cormorant Garamond', serif; font-weight: 500; font-size: 22px; margin: 0 0 10px; }}
  .step p {{ color: var(--muted); font-size: 15px; margin: 0; }}

  .about {{ display: grid; grid-template-columns: 1fr 1.2fr; gap: 56px; align-items: center; max-width: 940px; margin: 0 auto; }}
  .about .portrait {{ aspect-ratio: 4 / 5; overflow: hidden; border-radius: 12px; box-shadow: 0 30px 60px rgba(0,0,0,.4); }}
  .about .portrait img {{ width: 100%; height: 100%; object-fit: cover; }}
  .about h2 {{ text-align: left; margin-top: 0; }}
  .about p {{ color: var(--muted); margin: 0 0 18px; }}
  .about .signature {{ font-family: 'Cormorant Garamond', serif; font-style: italic; font-size: 22px; color: var(--gold-soft); margin-top: 24px; }}
  @media (max-width: 720px) {{ .about {{ grid-template-columns: 1fr; gap: 32px; }} .about h2 {{ text-align: center; }} }}

  .testimonials {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }}
  .testimonial {{ background: rgba(255,255,255,.025); border-left: 2px solid var(--gold); padding: 24px 26px; border-radius: 4px; }}
  .testimonial blockquote {{ margin: 0 0 14px; font-family: 'Cormorant Garamond', serif; font-style: italic; font-size: 18px; line-height: 1.5; color: var(--paper); }}
  .testimonial cite {{ color: var(--muted-2); font-size: 13px; font-style: normal; letter-spacing: .08em; text-transform: uppercase; }}

  .faq {{ max-width: 720px; margin: 0 auto; }}
  .faq details {{ border-bottom: 1px solid var(--ink-line); padding: 18px 0; }}
  .faq details summary {{ cursor: pointer; font-family: 'Cormorant Garamond', serif; font-size: 22px; font-weight: 500; list-style: none; display: flex; justify-content: space-between; align-items: center; color: var(--paper); }}
  .faq details summary::-webkit-details-marker {{ display: none; }}
  .faq details summary::after {{ content: "+"; font-size: 24px; color: var(--accent-soft); font-weight: 300; transition: transform .2s; }}
  .faq details[open] summary::after {{ transform: rotate(45deg); }}
  .faq details p {{ color: var(--muted); font-size: 16px; margin: 14px 0 4px; line-height: 1.65; }}

  .closing {{ text-align: center; padding: 96px 24px; background: radial-gradient(600px 400px at 50% 50%, rgba(59,91,219,.18), transparent 70%); }}
  .closing h2 {{ margin-bottom: 22px; }}
  .closing p {{ color: var(--muted); max-width: 540px; margin: 0 auto 32px; }}

  footer {{ padding: 36px 24px 48px; border-top: 1px solid var(--ink-line); text-align: center; color: var(--muted-2); font-size: 13px; }}
  footer .footer-links {{ display: flex; gap: 22px; justify-content: center; flex-wrap: wrap; margin-bottom: 14px; }}
  footer .footer-links a {{ color: var(--muted); text-decoration: none; transition: color .2s; }}
  footer .footer-links a:hover {{ color: var(--paper); }}

  .skip {{ position: absolute; left: -9999px; top: 0; }}
  .skip:focus {{ left: 16px; top: 16px; background: var(--paper); color: var(--ink); padding: 8px 14px; border-radius: 6px; z-index: 100; }}
</style>
</head>
<body>

<a href="#offerings" class="skip">Skip to offerings</a>

<header class="topbar">
  <a href="#" class="brand">
    <img src="img/logo.png" alt="" width="36" height="36" />
    {e(brand_first)} {f'<em>{e(brand_second)}</em>' if brand_second else ''}
  </a>
  <nav>
    <a href="#method">Method</a>
    <a href="#offerings">Offerings</a>
    <a href="#about">About</a>
    <a href="#faq">FAQ</a>
    <a class="cta" href="{e(bot_url)}" target="_blank" rel="noopener">{e(hero_cta_label)}</a>
  </nav>
</header>

<main>

  <section class="hero">
    <div class="hero-bg">
      <img src="img/hero.jpg" srcset="img/hero-small.jpg 750w, img/hero.jpg 1500w" sizes="100vw" alt="" fetchpriority="high" width="1500" height="2000" />
    </div>
    <div class="container">
      <p class="eyebrow">{e(tagline)}</p>
      <h1>{hero_headline_html}</h1>
      <p class="lede">{e(hero_lede)}</p>
      <div class="cta-row">
        <a class="btn btn-primary" href="{e(bot_url)}" target="_blank" rel="noopener">{e(hero_cta_label)} <span class="arrow">→</span></a>
        <a class="btn btn-ghost" href="#offerings">See offerings</a>
      </div>
      <p class="bot-note"><strong>{e(bot_persona)}</strong> is {e(short)}'s AI assistant on Telegram. Ask anything — pricing, fit, process — and she'll get back to you, or pass you to {e(short)}.</p>
    </div>
  </section>

  <section class="block philosophy" id="philosophy">
    <div class="container"><p>{e(philosophy_quote)}</p></div>
  </section>

  <section class="block tight" id="method">
    <div class="container">
      <p class="section-eyebrow">the method</p>
      <h2><em>{e(method_name)}</em>.</h2>
      <p class="section-lede">{e(method_lede)}</p>
      <div class="pillars">{pillars_html}</div>
    </div>
  </section>

  <section class="block" id="offerings">
    <div class="container">
      <p class="section-eyebrow">offerings</p>
      <h2>How to <em>begin</em>.</h2>
      <p class="section-lede">{e(offerings_lede)}</p>
      <div class="offerings">{offerings_html}</div>
    </div>
  </section>

  <section class="block tight" id="process">
    <div class="container">
      <p class="section-eyebrow">how it works</p>
      <h2>From <em>curiosity</em> to container.</h2>
      <div class="process">{process_html}</div>
    </div>
  </section>

  <section class="block tight" id="about">
    <div class="container">
      <div class="about">
        <div class="portrait"><img src="{e(about_portrait_image)}" alt="{e(name)}" loading="lazy" width="1500" height="1875" /></div>
        <div>
          <p class="section-eyebrow" style="text-align:left;">{e(about_eyebrow)}</p>
          <h2>{about_headline_html}</h2>
          {about_paras_html}
          <p class="signature">{e(about_signature)}</p>
        </div>
      </div>
    </div>
  </section>

  <section class="block tight" id="lineage">
    <div class="container">
      <p class="section-eyebrow">lineage</p>
      <h2>The hands that <em>shaped</em> mine.</h2>
      <div class="lineage">{lineage_body}</div>
    </div>
  </section>

  <section class="block" id="testimonials">
    <div class="container">
      <p class="section-eyebrow">witnessed</p>
      <h2>What clients <em>say</em>.</h2>
      <div class="testimonials">{testimonials_html}</div>
    </div>
  </section>

  <section class="block" id="faq">
    <div class="container">
      <p class="section-eyebrow">questions</p>
      <h2>What people <em>ask</em>.</h2>
      <div class="faq">{faq_html}</div>
    </div>
  </section>

  <section class="closing">
    <div class="container">
      <h2>{closing_headline_html}</h2>
      <p>{e(closing_body)}</p>
      <a class="btn btn-primary" href="{e(bot_url)}" target="_blank" rel="noopener">{e(hero_cta_label)} <span class="arrow">→</span></a>
    </div>
  </section>

</main>

<footer>
  <div class="footer-links">
    <a href="#method">Method</a>
    <a href="#offerings">Offerings</a>
    <a href="#about">About</a>
    <a href="#faq">FAQ</a>
    <a href="{e(bot_url)}" target="_blank" rel="noopener">Telegram</a>
    {ig_html}
  </div>
  <div>{e(footer_attr)}</div>
</footer>

</body>
</html>
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("slug", help="Champion slug (matches core/CHAMPIONS/<slug>.yaml)")
    p.add_argument("--out", help="Output HTML path (default: sites/<slug>/index.html)")
    args = p.parse_args()

    cfg_path = CHAMPIONS_DIR / f"{args.slug}.yaml"
    if not cfg_path.exists():
        print(f"error: {cfg_path} not found", file=sys.stderr)
        sys.exit(1)
    cfg = yaml.safe_load(cfg_path.read_text())
    if not cfg:
        print(f"error: {cfg_path} is empty", file=sys.stderr)
        sys.exit(1)

    html = render(cfg)

    out_path = Path(args.out) if args.out else SITES_DIR / args.slug / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)

    # Count remaining TODOs as a quality signal
    todos = html.count("TODO")
    print(f"✓ rendered {args.slug} → {out_path}", file=sys.stderr)
    if todos:
        print(f"  ⚠ {todos} TODO marker(s) remain in output — config needs filling", file=sys.stderr)


if __name__ == "__main__":
    main()
