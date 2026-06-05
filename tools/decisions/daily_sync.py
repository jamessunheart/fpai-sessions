#!/usr/bin/env python3
"""
daily_sync · v2 · 2026-05-31
Curate the daily note's auto-block into a POWERFULLY-ALIGNED surface — the most
relevant, valuable things from across the whole system, refreshed every fpull
(~15 min). Only the marked block is written; James's own capture is never touched.

Pulls:  THE PLATE (what needs YOU) · SURFACED CONCEPTS (hold in awareness) ·
        PROOF LOG today (forward motion) · SIX SEEDS (the why).
Deterministic, ~$0, no LLM. The same signal the Telegram bot surfaces.
"""
import os, re, datetime, json
from pathlib import Path
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

VAULT = Path(os.environ.get(
    "FPAI_VAULT",
    Path.home() / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS",
))
LOC = Path(os.environ.get("FPAI_LOCATION_FILE", Path.home() / ".config" / "fpai" / "location.json"))
PROOF = VAULT / "00_MEMORY" / "PROOF LOG.md"
HOME = VAULT / "HOME.md"
PLATE = VAULT / "THE PLATE.md"
SURF = VAULT / "00_MEMORY" / "SURFACED CONCEPTS.md"
DECIDE = VAULT / "00_MEMORY" / "DECISIONS.md"
READY = VAULT / "00_MEMORY" / "SYSTEM READINESS.md"
SCHED = VAULT / "00_MEMORY" / "SCHEDULE.md"
GOALS_MIRROR = VAULT / "00_MEMORY" / "GOALS MIRROR.md"
NORTH_STAR = VAULT / "00_MEMORY" / "FPOS NORTH STAR.md"
SPECLOG = VAULT / "02_SPECS" / "SPEC LOG.md"
CODEX_REPO = os.environ.get("FPAI_CODEX_REPO", "/Users/jamessunheart/FPAI_Cockpit")   # the directory James points Codex at
CODEX_SPECS = Path(CODEX_REPO) / "docs" / "codex" / "specs"
CODEX_HANDOFF = Path(CODEX_REPO) / "docs" / "codex" / "HANDOFF.md"
SERVICE_REGISTRY_VAULT = VAULT / "00_MEMORY" / "SERVICE REGISTRY.md"
SERVICE_REGISTRY_SORTED_VAULT = VAULT / "00_MEMORY" / "SERVICE REGISTRY — SORTED.md"
SOL_LIVE = Path.home() / ".config" / "fpai" / "sol_live" / "latest.json"
DAILY = VAULT / "07_DAILY"
SEEDS_NOTE = VAULT / "05_CONCEPTS" / "SIX SEEDS.md"
EMBERJ = VAULT / "08_JOURNAL" / "EMBER JOURNAL.md"
BRICKS_NOTE = VAULT / "BRICKS Architecture.md"
INSIGHT_DIR = Path(os.environ.get("FPAI_INSIGHT_DIR", Path.home() / ".config" / "fpai" / "insights"))
# %%…%% = Obsidian comments → invisible in Reading + Live Preview (no plumbing on screen).
START, END = "%%DASH:START%%", "%%DASH:END%%"
# legacy markers we migrate away from on sight:
LEGACY = ["<!-- WHERE_WE_ARE:START -->", "<!-- WHERE_WE_ARE:END -->",
          "<!-- REFRESH:START -->", "<!-- REFRESH:END -->"]

def read(p): return p.read_text(errors="ignore") if p.exists() else ""

def location():
    """James's current place + timezone (he travels constantly). Ember updates location.json when he
       says where he is. The page then stamps HIS local date + time — not the render machine's clock,
       which is what misfiled dates and showed stale flow when he was abroad."""
    try:
        import json
        d = json.loads(LOC.read_text())
        return d.get("place"), d.get("tz")
    except Exception:
        return None, None

def tz_now(tz):
    forced = os.environ.get("FPAI_DAILY_SYNC_NOW")
    if forced:
        try:
            dt = datetime.datetime.fromisoformat(forced)
            if dt.tzinfo is None and tz and ZoneInfo:
                dt = dt.replace(tzinfo=ZoneInfo(tz))
            return dt
        except Exception:
            pass
    if tz and ZoneInfo:
        try: return datetime.datetime.now(ZoneInfo(tz))
        except Exception: pass
    return datetime.datetime.now()

def insight_pool():
    """Quotable lines from available notes — seeds, Ember's reflections, BRICK learnings, surfaced concepts.
       Pulls blockquote + standalone-bold statements, length-filtered + deduped. The opening-insight source."""
    pool, seen = [], set()
    for src in (SEEDS_NOTE, EMBERJ, BRICKS_NOTE, SURF):
        for raw in read(src).splitlines():
            s = raw.strip()
            if s.startswith(">"):
                t = re.sub(r"^>+\s*", "", s)
                if t.startswith("[!"): t = re.sub(r"^\[![^\]]*\][+-]?\s*", "", t)
            elif re.match(r"^(?:[-*]\s+)?\*\*.+", s):   # bold-led line or bold list item (e.g. "**The ground.** …")
                t = re.sub(r"^[-*]\s+", "", s)
            else:
                continue
            t = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", r"\1", t)   # [[link|alias]] → text
            t = re.sub(r"\*Expressed as:.*$", "", t)                  # drop concept-link trailers
            t = re.sub(r"[*_`#]", "", t).strip().strip('"').strip()
            if 25 <= len(t) <= 240 and "http" not in t and t.lower() not in seen:
                seen.add(t.lower()); pool.append(t)
    return pool

def pick_insight(today, now):
    """One insight per refresh: a NEW one not shown today (else rotate); accumulate the day's list in a
       state file so the dashboard shows one-on-display + a toggle of all that surfaced today."""
    pool = insight_pool()
    if not pool: return None, []
    sf = INSIGHT_DIR / f"{today}.json"
    try: day = json.loads(sf.read_text())
    except Exception: day = []
    shown = {d["text"] for d in day}
    fresh = [p for p in pool if p not in shown]
    pick = fresh[0] if fresh else pool[len(day) % len(pool)]
    day.append({"ts": now.strftime("%H:%M"), "text": pick})
    try:
        INSIGHT_DIR.mkdir(parents=True, exist_ok=True)
        sf.write_text(json.dumps(day, ensure_ascii=False, indent=2))
    except Exception: pass
    return pick, day

def mindmap_prompt(today, place, sched, hero, allopen, soln, concepts, insight):
    """A ready-to-paste ChatGPT prompt that turns the day's contents into a visual mind map.
       Manual bridge until the system renders maps itself."""
    flow = " → ".join(re.sub(r"\s*—\s*", " ", i.replace("**", "")).strip() for i in (sched[1] if sched else []))
    lever = hero[0] if hero else "—"
    decs = "; ".join(q for q, _, _ in allopen if not (hero and q == hero[0])) or "none"
    m = re.search(r"\$[\d,]+ equity now", soln) if soln else None
    tre = m.group(0) if m else (re.sub(r"\s*·.*", "", soln) if soln else "—")
    streams = " · ".join(c for c in concepts) if concepts else "—"
    lines = [
        f"Create a clean, color-coded radial MIND MAP for my day ({today}{' · ' + place if place else ''}).",
        "Central node: \"Today\". Use concise labels, group by theme, color-code each branch. Branches:",
        f"- Flow: {flow or '—'}",
        f"- Top lever: {lever}",
        f"- Open decisions: {decs}",
        f"- Treasury: {tre}",
        f"- In the air: {streams}",
        f"- Insight: {insight or '—'}",
        "Output a single shareable mind-map image.",
    ]
    return "\n".join(lines)

def plate_needs():
    items = []
    for m in re.finditer(r"^### \d+ · (.+?)\s*·", read(PLATE), re.M):
        items.append(m.group(1).strip())
    return items

def readiness():
    """System completeness toward ship-ready — % + the next pillar to build. Surfaced FIRST."""
    txt = read(READY)
    if not txt: return None
    w = {"done": 1.0, "wip": 0.6, "started": 0.3, "todo": 0.0}
    pillars, nxt = [], None
    for m in re.finditer(r"- (\S+) \*\*(.+?)\*\* `(done|wip|started|todo)`", txt):
        emoji, name, st = m.group(1), m.group(2).strip(), m.group(3)
        pillars.append(w[st])
        if nxt is None and st != "done":
            nm = re.search(r"→ NEXT:\s*(.+?)\.", txt[m.end():m.end()+400])
            nxt = (emoji, name, nm.group(1).strip() if nm else "")
    if not pillars: return None
    pct = round(100 * sum(pillars) / len(pillars))
    return pct, nxt

def decisions_top(n=3):
    """The James-facing decision queue — only the OPEN section, top n, framed for low load."""
    txt = read(DECIDE)
    if "## 🟡 Open" not in txt: return [], 0
    seg = txt.split("## 🟡 Open", 1)[1].split("## ✅", 1)[0]
    out = []
    # each: - 🟡 **question**[ (qualifier)] — unblock  \n  ↳ answer: affordance
    for m in re.finditer(r"- 🟡 \*\*(.+?)\*\*([^—\n]*)—\s*(.+?)\n\s*↳\s*answer:\s*(.+)", seg):
        q = (m.group(1).strip() + " " + m.group(2).strip()).strip()
        unblock = re.sub(r"\s+", " ", m.group(3).strip())
        unblock = re.sub(r"^unblocks?\s+", "", unblock, flags=re.I)  # avoid "unblocks: unblocks…"
        # trim unblock to its first sentence for scan-speed
        unblock = re.split(r"(?<=[.)])\s", unblock)[0].strip().rstrip(".")
        aff = re.sub(r"\s+", " ", m.group(4).strip())
        out.append((q, unblock, aff))
    return out[:n], max(0, len(out) - n)

def goals_top3():
    """Top-3 priorities + progress from GOALS MIRROR's 'top 3' table: goal name (col 2) + current-state (col 5)."""
    txt = read(GOALS_MIRROR)
    if "GOALS — top 3" not in txt: return []
    seg = txt.split("GOALS — top 3", 1)[1].split("\n### ", 1)[0].split("\n## ", 1)[0]
    out = []
    for m in re.finditer(r"^\|\s*\d+\s*\|\s*(.+?)\s*\|\s*.+?\s*\|\s*.+?\s*\|\s*(.+?)\s*\|\s*$", seg, re.M):
        goal = re.sub(r"\*\*", "", m.group(1)).strip()
        prog = re.sub(r"\s+", " ", m.group(2)).strip()
        out.append((goal, prog))
    return out[:3]

def north_star_priority():
    """A live strategic priority from FPOS NORTH STAR, used before the stale GOALS MIRROR fallback."""
    txt = read(NORTH_STAR)
    if not txt:
        return None
    m = re.search(r"\*\*Stand up a (SELF-STANDING.+?)\.\*\*", txt, re.I | re.S)
    if m:
        goal = "Stand up a self-standing FPOS"
        detail = re.sub(r"\s+", " ", m.group(1)).strip()
        detail = detail[0].lower() + detail[1:] if detail else "North Star"
        return goal, detail
    m = re.search(r"\*\*Phase 0 · (.+?)\*\*\n- (.+)", txt, re.I)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).title(), re.sub(r"\s+", " ", m.group(2)).strip()
    return None

def active_handoff_section():
    txt = read(CODEX_HANDOFF)
    if "## 📍 WHERE" not in txt:
        return txt
    seg = txt.split("## 📍 WHERE", 1)[1]
    return seg.split("## 📤", 1)[0]

def codex_next_spec():
    """Current next build from the active HANDOFF lane, ignoring historical run summaries."""
    seg = active_handoff_section()
    m = re.search(r"\*\*Next spec:\*\*\s*`?([^`—\n]+)`?\s*—\s*(.+)", seg)
    if m:
        return m.group(1).strip(), re.sub(r"\s+", " ", m.group(2)).strip()
    m = re.search(r"Next(?: approved-ready)? build:\s*`?([^`—\n]+)`?\s*—\s*(.+)", seg, re.I)
    if m:
        return m.group(1).strip(), re.sub(r"\s+", " ", m.group(2)).strip()
    return None, None

def service_registry_awaiting_review():
    seg = active_handoff_section().lower()
    report = Path(CODEX_REPO) / "docs" / "codex" / "SERVICE_REGISTRY.md"
    return report.exists() and "spec_service-registry" in seg and "awaiting review" in seg

def cleanup_services_routed():
    spec_log = read(SPECLOG).lower()
    return (
        "cleanup-services" in spec_log
        and ("decided" in spec_log or "executing" in spec_log)
    )

def james_next_move(now):
    """HOME/Daily top-of-stream action: James signal first, downstream build second."""
    if cleanup_services_routed():
        late = now.hour >= 19 or now.hour < 6
        return {
            "title": "No action — cleanup is routed",
            "look": "[[SERVICE REGISTRY — SORTED]] only if you want the detail",
            "tell": "No one. If you want to override, tell Claude Code / Ember.",
            "yes": "checkpoint",
            "reason": "The cleanup decision is made. AI/Codex carry the reversible Buildstream work.",
            "downstream": "Builds the cleanup-services path from the sorted registry; no live stops or irreversible deletes.",
            "say": ["checkpoint", "change cleanup: ..."],
            "late": late,
        }
    if SERVICE_REGISTRY_SORTED_VAULT.exists():
        late = now.hour >= 19 or now.hour < 6
        return {
            "title": "Decide cleanup spec",
            "look": "[[SERVICE REGISTRY — SORTED]]",
            "tell": "Claude Code / Ember.",
            "yes": "spec cleanup-services",
            "reason": "The map is sorted. Only you decide whether cleanup becomes a reversible spec.",
            "downstream": "Drafts cleanup only. No service stops, deletes, or pruning without another yes.",
            "say": ["spec cleanup-services", "hold cleanup", "checkpoint"],
            "late": late,
        }
    if service_registry_awaiting_review():
        late = now.hour >= 19 or now.hour < 6
        return {
            "title": "Review map",
            "look": "[[SERVICE REGISTRY]]" if SERVICE_REGISTRY_VAULT.exists() else "`docs/codex/SERVICE_REGISTRY.md`",
            "tell": "Claude Code / Ember.",
            "yes": "spec prune",
            "reason": "See what exists before cleanup. Nothing changes without another yes.",
            "downstream": "Drafts a prune spec only. No service changes.",
            "say": ["spec prune", "hold", "checkpoint"],
            "late": late,
        }
    spec, detail = codex_next_spec()
    is_service_registry = spec and "service-registry" in spec
    late = now.hour >= 19 or now.hour < 6
    if is_service_registry:
        yes = "yes — proceed with Service Registry map-only"
        downstream = "Codex builds Service Registry as a read-only map. No stops. No deletes. No pruning."
        tell = "Codex."
    elif spec:
        label = spec.replace("SPEC_", "").replace("-", " ").replace("_", " ").strip().title()
        yes = f"yes — proceed with {label}"
        downstream = f"Codex builds `{spec}` after your upstream yes."
        tell = "Codex."
    else:
        yes = "yes — proceed with the next routed build"
        downstream = "AI carries the routed downstream work."
        tell = "Claude Code / Ember."
    title = "Your move: give one upstream signal"
    if late:
        title = "Your move: one upstream signal, then close clean"
    reason = "Only you can bless, change, or hold the next downstream move."
    if detail:
        reason = f"{detail} Only you can bless, change, or hold it."
    return {
        "title": title,
        "look": "this section",
        "tell": tell,
        "yes": yes,
        "reason": reason,
        "downstream": downstream,
        "say": [yes, "change first: ...", "checkpoint"],
        "late": late,
    }

def live_priorities_top3(allopen, now):
    """Top-3 from live sources: DECISIONS first, North Star second, GOALS MIRROR only as fallback."""
    out = []
    move = james_next_move(now)
    out.append((move["title"], " / ".join(f"`{s}`" for s in move["say"])))
    out.append(("AI carries downstream", move["downstream"]))
    for q, unblock, _aff in allopen[:2]:
        if "start codex building" in q.lower():
            continue
        out.append((q, unblock or "awaits James's call"))
    ns = north_star_priority()
    if ns and all(ns[0] != g for g, _ in out):
        out.append(ns)
    if len(out) < 3:
        for goal, prog in goals_top3():
            if all(goal != g for g, _ in out):
                out.append((goal, prog))
            if len(out) >= 3:
                break
    return out[:3]

def codex_ready():
    """Specs marked 'ready for Codex' in SPEC LOG → (name, est, gate, spec_link). Drives the cockpit's
       'Build with Codex' surface: what to build + where + the paste-in, so James never has to remember."""
    out = []
    handoff = read(CODEX_HANDOFF)
    done_names = set()
    for m in re.finditer(r"SPEC_([a-z0-9_-]+).*?awaiting review", handoff, re.I):
        done_names.add(m.group(1).replace("_", "-"))
    done_names.add("daily-realtime")
    preferred = [
        ("SPEC_service-registry.md", "🟢", "🤖 map-only"),
        ("SPEC_multimodel-debate-harness.md", "🟡", "❓ Y/N"),
        ("SPEC_financial-consolidation-hub.md", "🟡", "❓ Y/N"),
        ("SPEC_communication-hub.md", "🟡", "❓ Y/N · scope first"),
    ]
    if CODEX_SPECS.exists():
        for fname, est, gate in preferred:
            p = CODEX_SPECS / fname
            slug = fname.removeprefix("SPEC_").removesuffix(".md").replace("_", "-")
            if not p.exists() or slug in done_names:
                continue
            title = slug.replace("-", " ").title()
            if slug == "daily-realtime":
                title = "Daily Realtime"
            elif slug == "service-registry":
                title = "Service Registry / World Map"
            elif slug == "multimodel-debate-harness":
                title = "Multi-model Debate Harness"
            elif slug == "financial-consolidation-hub":
                title = "Financial Consolidation Hub"
            elif slug == "communication-hub":
                title = "Comms Hub (Conscious Chat)"
            out.append((title, est, gate, str(p.relative_to(Path(CODEX_REPO)))))
        if out:
            return out
    for m in re.finditer(r"^\|\s*(.+?)\s*\|\s*.+?\s*\|\s*.+?\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$",
                         read(SPECLOG), re.M):
        name, est, gate, status, link = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        if "ready for codex" in status.lower():
            slug = re.sub(r"\[\[|\]\]", "", link).strip().removeprefix("SPEC_").replace("_", "-")
            if slug not in done_names:
                out.append((name.strip(), est.strip(), gate.strip(), re.sub(r"\[\[|\]\]", "", link).strip()))
    return out

def surfaced_top(n=3):
    out = []
    for m in re.finditer(r"^\d+\.\s*\[\[([^\]|]+)", read(SURF), re.M):
        out.append(m.group(1).strip())
    return out[:n]

def builds_today(today, n=4):
    out = []
    for line in read(PROOF).splitlines():
        if line.startswith(f"- **{today}"):
            bolds = re.findall(r"\*\*(.+?)\*\*", line)
            t = next((b for b in bolds if not b.startswith(today)), None)
            if t: out.append(t.strip())
    return out[:n]

def chips(aff):
    """Turn an affordance string into inline-code gesture chips: the quoted verbs become `code`."""
    quoted = re.findall(r'"([^"]+)"', aff)
    if quoted:
        return " / ".join(f"`{q}`" for q in quoted)
    return f"`{aff.split('→')[0].strip().strip('.')[:24]}`"

def watching():
    """No-action FYIs (holds / AI-proceeding) from DECISIONS.md '## 👀 Watching' — rendered as one quiet line."""
    txt = read(DECIDE)
    if "## 👀 Watching" not in txt: return []
    seg = txt.split("## 👀 Watching", 1)[1].split("\n## ", 1)[0]
    return [re.sub(r"\s+", " ", m.group(1)).strip() for m in re.finditer(r"^- (.+)$", seg, re.M)]

def process_checked_decisions(note_text, today):
    """Tick-to-decide: any decision checkbox James checked [x] in the dashboard → move it from
    DECISIONS '## 🟡 Open' to '## ✅ Decided'. The act is PROCESSED (not stored), so it survives
    the 15-min regen — next render the item is gone from Open and won't reappear."""
    fm = re.match(r"^---\n.*?\n---\n", note_text, re.S)   # skip frontmatter delimiters
    body = note_text[fm.end():] if fm else note_text
    above = body.split("\n---", 1)[0]                      # dashboard = above the fold
    checked = re.findall(r"- \[[xX]\] \*\*(.+?)\*\*", above)
    if not checked or not DECIDE.exists(): return []
    dt = DECIDE.read_text(errors="ignore"); decided = []
    for q in checked:
        pat = re.compile(r"- (?:🟡|🎁) \*\*" + re.escape(q) + r"\*\*.*?(?=\n- (?:🟡|🎁)|\n\n---|\n\n## )", re.S)
        m = pat.search(dt)
        if not m: continue
        dt = dt.replace(m.group(0), "").replace("\n\n\n", "\n\n")
        line = f"- ✅ **{today} · {q}** — decided via daily note ✓\n"
        dt = dt.replace("## ✅ Decided  (recent — archive)\n",
                        "## ✅ Decided  (recent — archive)\n\n" + line, 1)
        decided.append(q)
    if decided: DECIDE.write_text(dt)
    return decided

def sol_treasury():
    """Near-realtime SOL-futures value to the treasury, from the 60s live feed (latest.json).
       Returns (line, pnl) so the dashboard can show a P/L direction arrow."""
    try:
        import json
        d = json.loads(SOL_LIVE.read_text())
        return d.get("treasury_line"), d.get("totals", {}).get("unrealized_pnl")
    except Exception:
        return None, None

def morning_message(hour, yday):
    """A short morning lift — a rotating uplifting video/meditation (search links always resolve)."""
    if not (4 <= hour < 11): return None
    M = "https://www.youtube.com/results?search_query="
    picks = [
        ("5-min morning gratitude meditation", M + "5+minute+morning+gratitude+meditation"),
        ("Alan Watts — what do you desire (3 min)", M + "alan+watts+what+do+you+desire+3+min"),
        ("breath of arrival — 3-min wake-up breath", M + "3+minute+morning+breathing+exercise"),
        ("a morning blessing / intention", M + "morning+intention+meditation+5+min"),
        ("Tara Brach — morning meditation", M + "tara+brach+morning+meditation"),
    ]
    t, u = picks[yday % len(picks)]
    return f"[{t}]({u})"

def schedule_next():
    """Next upcoming block from SCHEDULE.md — so the dashboard lightens the ask around travel/meetings."""
    txt = read(SCHED)
    if "## 📅" not in txt: return None
    seg = txt.split("## 📅", 1)[1]
    title = seg.split("\n", 1)[0].strip()
    items = [m.group(1).strip() for m in re.finditer(r"^- (.+)$", seg.split("\n## ", 1)[0], re.M)]
    light = "LIGHT" in title.upper() or "light" in seg[:400].lower()
    return title, items[:4], light

def _schedule_date(title):
    m = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", title)
    if not m:
        return None
    try:
        return datetime.date.fromisoformat(m.group(1))
    except ValueError:
        return None

def _schedule_minutes(item):
    raw = item.lower()
    m = re.search(r"~?\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", raw)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        ap = m.group(3)
        if ap == "pm" and hour < 12:
            hour += 12
        elif ap == "am" and hour == 12:
            hour = 0
        return hour * 60 + minute, 90
    bands = [
        ("early morning", 7 * 60, 120),
        ("morning", 9 * 60, 180),
        ("midday", 12 * 60, 90),
        ("afternoon", 14 * 60, 240),
        ("evening", 18 * 60, 180),
        ("night", 21 * 60, 180),
    ]
    for label, start, duration in bands:
        if label in raw:
            return start, duration
    return None, 90

def schedule_flow(now):
    """Classify schedule items as past / now / next so old morning blocks don't stay 'upcoming'."""
    sched = schedule_next()
    if not sched:
        return None
    title, items, light = sched
    sched_date = _schedule_date(title)
    today = now.date()
    now_min = now.hour * 60 + now.minute
    classified = []
    for i, item in enumerate(items):
        start, duration = _schedule_minutes(item)
        if sched_date and sched_date < today:
            status = "past"
        elif sched_date and sched_date > today:
            status = "next" if i == 0 else "upcoming"
        elif start is None:
            status = "upcoming"
        elif now_min >= start + duration:
            status = "past"
        elif now_min >= start:
            status = "now"
        else:
            status = "next" if not any(x["status"] in {"now", "next"} for x in classified) else "upcoming"
        classified.append({"text": item, "status": status, "start": start})
    if classified and not any(x["status"] in {"now", "next"} for x in classified):
        future = [x for x in classified if x["status"] == "upcoming"]
        if future:
            future[0]["status"] = "next"
    return {"title": title, "items": classified, "light": light, "date": sched_date}

def schedule_flow_lines(flow):
    if not flow:
        return []
    lines = []
    for item in flow["items"]:
        text = re.sub(r"\*\*", "", item["text"]).replace(" — ", " · ").strip()
        text = re.sub(r"^~(?=\d)", "about ", text)
        if item["status"] == "past":
            lines.append(f"✓ ~~{text}~~")
        elif item["status"] == "now":
            lines.append(f"▶ **NOW:** {text}")
        elif item["status"] == "next":
            lines.append(f"→ **NEXT:** {text}")
        else:
            lines.append(f"• {text}")
    return lines

def _section_body(note_text, label):
    """Pull a below-fold section's body whether it's a `## heading` OR a `> [!x]- callout` toggle.
       Reads from the label line until a blank line (callout end) or the next section. Format-tolerant
       so the persistent zone can be styled as toggle boxes without breaking the parsers."""
    lines = note_text.splitlines()
    for i, ln in enumerate(lines):
        if label in ln and (ln.lstrip().startswith("#") or "[!" in ln):
            body, started = [], False
            for nx in lines[i + 1:]:
                if nx.strip() == "":
                    if started: break
                    continue
                if nx.lstrip().startswith("#") or "[!" in nx: break
                body.append(nx); started = True
            return "\n".join(body)
    return ""

def my_tasks(note_text):
    """James's own task lane (below the fold) — for learning + service. Heading- or toggle-format."""
    seg = _section_body(note_text, "My tasks")
    return [m.group(1).strip() for m in re.finditer(r"\[[ xX]\]\s+(.+)$", seg, re.M) if m.group(1).strip()]

def wellness_done(note_text):
    """Which wellness habits James already ticked (so the nudge never repeats what's done). Toggle-safe."""
    seg = _section_body(note_text, "Wellness")
    return {m.group(1).strip().lower() for m in re.finditer(r"\[[xX]\]\s+(.+)$", seg, re.M)}

def wellness_nudge(hour, done):
    """One gentle, contextual care nudge — the right one for the moment, only if not already done."""
    M = "https://www.youtube.com/results?search_query="
    cands = []
    if hour >= 22 or hour < 6:
        cands = [("🛌 screens off", "wind down — [sleep meditation]({}yoga+nidra+for+sleep) · or 4-7-8 breath".format(M))]
    elif hour < 11:
        cands = [("💧 water", "start with a glass of water 💧"),
                 ("🧘 meditate", "[10-min ground]({}10+minute+guided+meditation) before the day".format(M))]
    elif 11 <= hour < 15:
        cands = [("💧 water", "water + a real meal? don't decide hungry"),
                 ("🌬️ break", "20 min off-screen (20-20-20) resets the eyes + mind")]
    else:
        cands = [("🌬️ break", "a short off-screen walk? the body tells the truth"),
                 ("🧘 meditate", "[2-min box breath]({}2+minute+box+breathing+guided)".format(M))]
    for key, msg in cands:
        if not any(k in d for d in done for k in key.lower().split()[1:]):
            return msg
    return None

def care_check(now):
    """ONE clear, moment-aware wellness check — surfaced UP TOP so the system actively cares (rest at 2am,
       hydrate at dawn, break midday, wind down at night), woven into the focus flow rather than buried."""
    h = now.hour
    h12 = ((h + 11) % 12) + 1
    ampm = "am" if h < 12 else "pm"
    if h >= 22 or h < 5:
        return f"💗 It's {h12}{ampm} — the build will keep. Rest is tonight's real move; I'll hold the watch. → [[REST — THE CHARGING STATION]]"
    if h < 7:  return "💗 Early start — water + a few breaths before the day grabs you."
    if h < 11: return "💗 Morning — hydrate, then 2 min to ground before the first decision."
    if h < 15: return "💗 Midday — water + a real meal? Don't decide hungry."
    if h < 19: return "💗 Afternoon — a short off-screen walk resets the body + mind."
    return "💗 Evening — start easing the screens down; the day closes cleaner."

def refresh_home_stamp(now, place, tz):
    """Keep HOME's Today section visible and marker-free."""
    if not HOME.exists():
        return False
    doc = read(HOME)
    tz_label = now.tzname() or tz or "local"
    place_line = f"📍 **{place}**" if place else "📍 **Current location**"
    block = (
        "## 🌅 Today\n\n"
        f"{place_line} · refreshed **{now.strftime('%a %b')} {now.day} · {now.strftime('%-I:%M %p')} {tz_label}**"
    )
    if "## 🌅 Today" not in doc:
        return False
    new = re.sub(r"## 🌅 Today.*?(?=\n## |\Z)", block + "\n\n", doc, flags=re.S)
    if new != doc:
        HOME.write_text(new)
        return True
    return False

def checkbox_state(doc, label):
    m = re.search(rf"- \[([ xX])\]\s+\*\*{re.escape(label)}(?:[:*]|\b)", doc)
    return "x" if m and m.group(1).lower() == "x" else " "

def sol_decision(doc):
    if checkbox_state(doc, "SOL — hold") == "x":
        return "hold"
    if checkbox_state(doc, "SOL — exit/de-lever") == "x":
        return "exit/de-lever"
    m = re.search(r"- \[([ xX])\]\s+\*\*SOL:\*\*\s+([^\n]+)", doc)
    if m and m.group(1).lower() == "x":
        options = m.group(2).strip()
        if options.startswith("hold"):
            return "hold"
        return "exit/de-lever"
    m = re.search(r"\*\*SOL:\*\*.*?Your answer:\s*`([^`]+)`", doc, re.S)
    if m:
        answer = m.group(1).strip()
        if answer in {"hold", "exit/de-lever"}:
            return answer
    return "hold"

def refresh_home_decide():
    """Keep the James-only area as simple decisions, not doctrine."""
    if not HOME.exists():
        return False
    doc = read(HOME)
    if "## 🌱 Streams" not in doc:
        return False
    if cleanup_services_routed():
        service_block = (
            "**Service cleanup:** routed downstream.\n"
            "Override: `change cleanup: ...`"
        )
    elif SERVICE_REGISTRY_SORTED_VAULT.exists():
        service_block = (
            "**Service cleanup?**\n"
            "Options: `spec cleanup-services` / `hold cleanup`\n"
            "Your answer: `...`"
        )
    else:
        service_block = (
            "**Service map?**\n"
            "Options: `spec prune` / `hold`\n"
            "Your answer: `...`"
        )
    sol_answer = sol_decision(doc)
    block = (
        "## 🔴 Decide\n\n"
        f"{service_block}\n\n"
        "**SOL?**\n"
        "Options: `hold` / `exit/de-lever`\n"
        f"Your answer: `{sol_answer}`"
    )
    if re.search(r"## 🔴 (?:Only you|Decide)", doc):
        new = re.sub(r"## 🔴 (?:Only you|Decide).*?(?=\n## 🌱 Streams)", block + "\n\n", doc, flags=re.S)
    else:
        new = doc.replace("## 🌱 Streams", block + "\n\n## 🌱 Streams", 1)
    if new != doc:
        HOME.write_text(new)
        return True
    return False

def refresh_home_next_move(now):
    """Keep HOME's top section as James-action, not a downstream project board."""
    if not HOME.exists():
        return False
    doc = read(HOME)
    if "## ▶️ NEXT MOVE" not in doc or "## 🌅 Today" not in doc:
        return False
    move = james_next_move(now)
    close_line = (
        "**If you are tired or time-limited:** just say `checkpoint` and I preserve the next clean move."
        if move["late"]
        else "**If you want to stay upstream:** speak the signal; AI carries the structure downstream."
    )
    block = (
        "## ▶️ NEXT MOVE\n\n"
        f"**{move['title']}.**\n\n"
        f"**Look:** {move['look']}\n\n"
        f"**Tell:** {move['tell']}\n\n"
        f"**Why:** {move['reason']}\n\n"
        "**Say:** " + " / ".join(f"`{s}`" for s in move["say"]) + "\n\n"
        f"**AI does:** {move['downstream']}\n\n"
        f"{close_line}"
    )
    new = re.sub(r"## ▶️ NEXT MOVE.*?(?=\n## 🌅 Today)", block + "\n\n", doc, flags=re.S)
    if new != doc:
        HOME.write_text(new)
        return True
    return False

def main():
    place, tz = location()
    now = tz_now(tz)                       # James's local time, wherever he is
    today = now.date().isoformat()         # → today's note is HIS today, not the server's
    note = DAILY / f"{today}.md"           # if missing, we still write it (a fresh day gets its own file)
    ts = now.strftime("%H:%M")
    stamp_full = now.strftime("%Y-%m-%d %H:%M")

    # tick-to-decide: process any boxes James checked BEFORE reading the queue, so decided
    # items leave Open and don't reappear this render.
    existing = read(note)
    decided_now = process_checked_decisions(existing, today)

    ready = readiness()
    decisions, more = decisions_top(n=1)   # n=1 → hero; the rest go in the collapsible
    allopen, _ = decisions_top(n=99)
    if "awaiting review" in read(CODEX_HANDOFF):
        allopen = [d for d in allopen if "start codex building" not in d[0].lower()]
    concepts = surfaced_top()
    builds = builds_today(today)
    ndec = len(allopen)
    nships = len(builds)

    # ── time-aware greeting (a little life) ───────────────────────────────
    h = now.hour
    if   h < 5:  greet, icon = "Still up", "🌌"
    elif h < 12: greet, icon = "Good morning", "☀️"
    elif h < 17: greet, icon = "Good afternoon", "🌤️"
    elif h < 22: greet, icon = "Good evening", "🌙"
    else:        greet, icon = "Winding down", "🌃"
    mojo = "🔥 on a roll" if nships >= 3 else ("⚡ moving" if nships >= 1 else "🎬 fresh canvas")

    # ── seed line rotates by day-of-year (feels alive, never stale) ───────
    seeds = [
        "consciousness first — be the presence the day is built around.",
        "coherence — one aligned move beats ten scattered ones.",
        "circulation over extraction — let value flow today.",
        "least effort, right leverage — do only what only you can do.",
        "love is the through-line. Today serves [[Attention]] itself.",
        "build in public — today's work is part of the show.",
    ]
    seed = seeds[now.timetuple().tm_yday % len(seeds)]

    pct, nxt = (ready if ready else (None, None))
    watch = watching()
    sched = schedule_flow(now)
    hero = allopen[0] if allopen else None
    rest_items = allopen[1:]
    rest_mode = (now.hour >= 22 or now.hour < 6)   # REST LAW: no major calls from depletion
    insight, day_insights = pick_insight(today, now)   # one fresh insight per refresh + the day's running list

    # ── compose the dashboard — checkbox hero + collapsible checklist (tick OR reply to decide) ──
    where = f"  ·  {place}" if place else ""
    h = now.hour
    h12 = ((h + 11) % 12) + 1
    ampm = "AM" if h < 12 else "PM"
    daylabel = f"{now.strftime('%a %b')} {now.day}"            # "Thu Jun 4"
    tlabel = f"{h12}:{now.strftime('%M')} {ampm}"              # "2:14 AM"
    # Lead the LIVING note with TIME + day + place (the filename already carries the ISO date — no repeat),
    # then the FLOW from here: the body's state NOW → the priorities to move through. The system knows the flow.
    L = [f"# {icon} {daylabel}  ·  `{tlabel}`{where}", ""]
    top3 = live_priorities_top3(allopen, now)
    if   h >= 22 or h < 5: first = "🌙 **Sleep** — rest now; the build keeps till morning"
    elif h < 11:           first = "☀️ **Ground + hydrate** — 2 min before the first decision"
    elif h < 15:           first = "🍽️ **Fuel** — water + a real meal, then focus"
    else:                  first = "🌿 **Reset** — a short off-screen break, then focus"
    L.append("**🌊 Flow from here**")
    nodes = [first]
    if sched:                                   # weave the day's real schedule into the living flow
        for line in schedule_flow_lines(sched):
            nodes.append("🗓️ " + line)
    nodes += [f"🎯 **{g}** — {p}" for g, p in top3[:2]]
    for i, node in enumerate(nodes, 1):
        L.append(f"{i}. {node}")
    L.append("")
    # 💡 open with one insight — fresh each refresh; collapse to see all that surfaced today.
    if insight:
        # Clean focus (2026-06-03): dedup the day's list by text + cap to 4 unique, newest first.
        # (Was dumping every refresh → the same handful of insights repeated 16×.)
        if len(day_insights) > 1:
            seen_i, uniq = set(), []
            for d in reversed(day_insights):
                k = d["text"].strip().lower()
                if k in seen_i:
                    continue
                seen_i.add(k); uniq.append(d)
                if len(uniq) >= 4:
                    break
            L.append(f"> [!quote]- 💡 {insight}")
            if len(uniq) > 1:
                L.append("> _also surfaced today:_")
                for d in uniq:
                    L.append(f"> - `{d['ts']}` {d['text']}")
        else:
            L.append(f"> [!quote] 💡 {insight}")
        L.append("")
    # 🌿 Habits — read-only status of the tickable list below the fold (the Flow above carries the body-state node).
    done = wellness_done(existing)
    L.append(f"🌿 **Habits** · {len(done)}/5 today  ·  _tick below_")
    L.append("")
    if builds:
        L.append("> [!success]- ✅ Moved today")
        for b in builds:
            L.append(f"> - {b}")
        L.append("")
    # ── everything else, demoted into collapsed toggles (one tap away — concentration over clutter) ──
    if sched:
        title = sched["title"]
        flow = "  →  ".join(schedule_flow_lines(sched))
        rm = re.search(r"·\s*([A-Za-z][^·]*?→[^·]*?)\s*·", title)   # pull a route label e.g. "Spain → Greece"
        route = f" · {rm.group(1).strip()}" if rm else ""
        L.append(f"> [!info]- 🗓️ Today{route}")
        L.append(f"> {flow}")
        L.append("")
    if allopen:
        # Decisions = reply-the-verb. A single checkbox can't encode WHICH option, so no ambiguous box —
        # you tell Ember the verb (`build it` / `after X`), and that makes the call cleanly.
        label = f"🛌 {ndec} decisions — resting" if rest_mode else f"⚡ {ndec} to decide · reply the verb to Ember"
        L.append(f"> [!todo]- {label}")
        for q, unblock, aff in allopen:
            L.append(f"> - **{q}** · {chips(aff)}")
        L.append("")
    # 🛠️ Build with Codex — when a spec is Codex-ready, hand James what · where · the paste-in kickoff.
    cx = codex_ready()
    if cx:
        L.append(f"> [!todo]- 🛠️ Build with Codex ({len(cx)} ready) — what · where · paste-in")
        L.append(f"> **Where:** open Codex → point it at repo `{CODEX_REPO}`  ·  first time? full steps → [[CODEX SETUP]]")
        L.append("> **Ready specs** (easiest first):")
        for name, est, gate, link in cx:
            spec_path = link if "/" in link or link.endswith(".md") else f"02_SPECS/{link}.md"
            L.append(f"> - {est} **{name}** → `{spec_path}`  ({gate})")
        L.append("> **Paste-in kickoff** (swap in the spec path above):")
        L.append("> ```")
        L.append("> Read AGENTS.md, then the vault notes CODEX BRIDGE + CODEX PARALLEL BUILD PROTOCOL, then 02_SPECS/<SPEC>.md.")
        L.append("> Work ONLY on the branch named in that spec; touch only files-allowed, never files-forbidden.")
        L.append("> Build to the Definition of Done, run the tests, then report: files changed · summary · tests · risks · rollback.")
        L.append("> ```")
        L.append("")
    # 💰 Treasury + Pulse — ONE collapsed no-action toggle. Money + FYIs one tap away, off the hero.
    soln, pnl = sol_treasury()
    tp = []
    if soln:
        arrow = "📉" if (pnl is not None and pnl < 0) else ("📈" if pnl is not None else "·")
        tp.append(f"> `💰` {arrow} {soln}")
    if watch:
        tp.append("> `✅ handled` · " + " · ".join(watch))
    if concepts:
        tp.append("> `🌌 in the air` · " + " · ".join(f"[[{c}]]" for c in concepts))
    if tp:
        L.append("> [!note]- 💰 Treasury · Pulse  _(no action)_")
        L.extend(tp)
        L.append("")
    # Mind-Map prompt block removed 2026-06-03 (clean focus — was clutter on the daily page).
    tail_seed = "rest well — the day will be here, clearer" if rest_mode else seed
    L.append(f"*🧭 {tail_seed}  ·  [[DECISIONS]]  ·  [[SYSTEM READINESS|readiness]]*")
    block = "\n".join(L)

    # ── anchor on the `---` fold: the pipe owns everything ABOVE it; Capture/Journal/Done
    #    below it are James's and never touched. No on-screen plumbing markers. ──
    doc = existing
    for mk in LEGACY + ["%%DASH:START%%", "%%DASH:END%%"]:
        doc = doc.replace(mk, "")
    doc = re.sub(r"\n?🔄 \*Last refreshed:.*?\n", "\n", doc)
    fm = re.match(r"^---\n.*?\n---\n", doc, re.S)
    head = doc[:fm.end()] if fm else ""
    body = doc[fm.end():] if fm else doc
    m = re.search(r"(?m)^---\s*$", body)         # the fold (first hr after frontmatter)
    if m:
        tail = body[m.start():].lstrip("\n")     # starts with '---' — James's persistent zone, untouched
    else:                                         # migrate: build the persistent section once
        # WRITE-zones = plain headings (foldable AND editable — callouts collapse when you click to type).
        # TICK/READ-zones (Wellness) = toggle callout (ticking inside a callout works fine).
        tail = ("---\n\n**Capture** — dump anything; I route it at `eod`\n- \n\n"
                "## 📝 My tasks  (yours — I read these to serve you better)\n- [ ] \n\n"
                "> [!note]- 🌿 Wellness  (tick as you go — care, never nag · [[WELLNESS]])\n"
                "> - [ ] 💧 Water\n> - [ ] 🌬️ Off-screen break\n> - [ ] 🚶 Move / stretch\n"
                "> - [ ] 🧘 Meditate / breathe\n> - [ ] 🛌 Screens off by 10:30 PM\n\n"
                "## 📓 Journal → [[JAMES JOURNAL]]\n- \n\n"
                "## ✅ Completed today  (checked-off → [[WORK LEDGER]])\n- [ ] \n\n"
                "## 🧠 Mind Map of the Day  (paste the ChatGPT mind-map image here)\n")
    doc = head.rstrip("\n") + "\n\n" + block + "\n\n" + tail
    doc = re.sub(r"\n{3,}", "\n\n", doc)

    note.write_text(doc)
    home_refreshed = refresh_home_stamp(now, place, tz)
    home_next = refresh_home_next_move(now)
    home_decide = refresh_home_decide()
    tasks = my_tasks(doc)
    print(f"daily_sync v9 → {note.name}: refreshed {stamp_full} {place or ''} · open={ndec} · decided_now={len(decided_now)} · my_tasks={len(tasks)} · streak={nships} · home_stamp={int(home_refreshed)} · home_next={int(home_next)} · home_decide={int(home_decide)}")

if __name__ == "__main__":
    main()
