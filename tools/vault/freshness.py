#!/usr/bin/env python3
"""Vault freshness auditor.

Successor to the manual FRESHNESS CHECK of 2026-05-30, which caught real drift
once and then went stale itself — the lesson this tool encodes is that only
scheduled machinery stays honest. Read-only over the vault except for the one
report file it owns (00_MEMORY/FRESHNESS CHECK.md).

Two distinct staleness signals, per the original note's catch:
- file age (mtime) — did the machinery run?
- claimed age (a "Last updated/Snapshot: YYYY-MM-DD" line) — is the CONTENT
  old even if the file was recently rewritten? A fresh file is not fresh truth.
"""
from __future__ import annotations

import datetime as dt
import os
import re
from pathlib import Path

VAULT = Path(os.environ.get(
    "FPAI_VAULT",
    Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/FPOS/Full Potential OS",
))
REPORT_REL = Path("00_MEMORY/FRESHNESS CHECK.md")

AUTO_MARKERS = re.compile(r"auto-generated|self-refreshing|auto-refreshed|do not edit by hand", re.I)
AUTO_HEADER_LINES = 12  # the claim must be about THIS file (header zone), not doctrine discussing the pattern
EMBED_RE = re.compile(r"!\[\[([^\]#|]+)")
CLAIM_RE = re.compile(
    r"(?:Last updated|Last organized|Snapshot|Refreshed|Generated|Updated(?: By)?)\s*[:\s·*]+\s*(\d{4}-\d{2}-\d{2})",
    re.I,
)
# dated-by-design surfaces age on purpose; auditing them is noise
SKIP_DIRS = {"07_DAILY", "08_JOURNAL", "06_SHOW FRAMES"}
DATED_NAME = re.compile(r"\d{4}-\d{2}-\d{2}")

# days before a tier counts as stale
THRESHOLDS = {"auto": 1, "memory": 7, "other": 21}

# who owns the regeneration of each auto surface (vault-relative name → machinery)
MACHINERY = {
    "HOME.md": "tools/decisions/daily_sync.py (autoloop · 2h)",
    "00_MEMORY/NEXT MOVE DETAIL.md": "tools/decisions/daily_sync.py (autoloop · 2h)",
    "00_MEMORY/INDEX OF INDEXES.md": "tools/index/refresh.py (via daily_sync since 2026-06-10)",
    "00_MEMORY/DECISIONS.md": "tools/queue/build.py via daily_sync",
    "00_MEMORY/FRESHNESS CHECK.md": "tools/vault/freshness.py (via daily_sync since 2026-06-10)",
    "INTELLIGENCE HUB.md": "fpull component scripts (composite — freshness = its embedded sources)",
}

REPO_ROOT = Path(__file__).resolve().parents[2]
# --heal allowlist: 🔴 finding → generator scripts safe to re-run (idempotent, vault-writing only).
# NEVER daily_sync.py here — freshness runs inside it; that would recurse.
HEAL_COMMANDS = {
    "00_MEMORY/INDEX OF INDEXES.md": ["tools/index/refresh.py"],
    "INTELLIGENCE HUB.md": [
        "tools/decisions/mirror_pull.py",
        "tools/decisions/concept_surfacer.py",
        "tools/decisions/treasury_chart.py",
        "tools/decisions/hub_charts.py",
    ],
}


def file_tier(rel: Path, text: str) -> str:
    header = "\n".join(text.splitlines()[:AUTO_HEADER_LINES])
    if AUTO_MARKERS.search(header):
        return "auto"
    if rel.parts and rel.parts[0] == "00_MEMORY":
        return "memory"
    return "other"


def audit(vault: Path | str = VAULT, now: dt.datetime | None = None) -> dict:
    """Scan the vault; return findings grouped by tier. Never raises on a bad file."""
    vault = Path(vault)
    now = now or dt.datetime.now()
    findings = {"auto": [], "memory": [], "other": []}
    scanned = skipped = 0
    all_md = sorted(vault.rglob("*.md"))
    by_stem = {p.stem: p for p in all_md}
    for md in all_md:
        rel = md.relative_to(vault)
        if rel == REPORT_REL:
            continue  # the report doesn't audit itself
        if (rel.parts and rel.parts[0] in SKIP_DIRS) or DATED_NAME.search(md.stem):
            skipped += 1
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
            mtime_age = (now - dt.datetime.fromtimestamp(md.stat().st_mtime)).days
        except OSError:
            continue
        scanned += 1
        tier = file_tier(rel, text)
        claim = CLAIM_RE.search(text)
        claim_age = None
        if claim:
            try:
                claim_age = (now.date() - dt.date.fromisoformat(claim.group(1))).days
            except ValueError:
                pass
        stale_embed = None
        if tier == "auto":
            # composite surface: panels are live transclusions, so its own mtime lies —
            # freshness is the age of the OLDEST embedded source that still exists.
            sources = [by_stem[s.strip()] for s in EMBED_RE.findall(text) if s.strip() in by_stem]
            if sources:
                ages = {}
                for src in sources:
                    try:
                        # a source that declares itself stalled/paused/queued is being honest,
                        # not breaking the dashboard's freshness promise — skip it
                        head = "\n".join(src.read_text(encoding="utf-8", errors="ignore").splitlines()[:6])
                        if re.search(r"status:.*(stalled|paused|queued)", head, re.I):
                            continue
                        ages[src.stem] = (now - dt.datetime.fromtimestamp(src.stat().st_mtime)).days
                    except OSError:
                        continue
                if ages:
                    stale_embed, age = max(ages.items(), key=lambda kv: kv[1])
                else:
                    age = mtime_age
            else:
                age = mtime_age  # machinery signal: did the generator rewrite the file?
        else:
            age = claim_age if claim_age is not None else mtime_age
        if age > THRESHOLDS[tier]:
            findings[tier].append({
                "file": str(rel), "age": age, "mtime_age": mtime_age, "claim_age": claim_age,
                "stale_embed": stale_embed, "machinery": MACHINERY.get(str(rel)),
            })
    for tier in findings:
        findings[tier].sort(key=lambda f: -f["age"])
    return {"findings": findings, "scanned": scanned, "skipped": skipped,
            "stamp": now.strftime("%Y-%m-%d %H:%M")}


def _section(title: str, items: list[dict], cap: int = 25) -> list[str]:
    lines = [title, ""]
    if not items:
        lines += ["_None — clean._", ""]
        return lines
    for f in items[:cap]:
        bits = [f"- `{f['file']}` — **{f['age']}d**"]
        if f.get("stale_embed"):
            bits.append(f"(oldest embedded source: [[{f['stale_embed']}]])")
        elif f["claim_age"] is not None and f["claim_age"] != f["mtime_age"]:
            bits.append(f"(file {f['mtime_age']}d · claims {f['claim_age']}d — fresh file ≠ fresh truth)")
        if f["machinery"]:
            bits.append(f"· machinery: {f['machinery']}")
        lines.append(" ".join(bits))
    if len(items) > cap:
        lines.append(f"- … +{len(items) - cap} more")
    lines.append("")
    return lines


def render(result: dict) -> str:
    f = result["findings"]
    lines = [
        "# FRESHNESS CHECK",
        "",
        f"*Auto-generated by `tools/vault/freshness.py` · {result['stamp']} · "
        f"{result['scanned']} files scanned · {result['skipped']} dated-by-design skipped · "
        "supersedes the manual 2026-05-30 audit (which caught real drift once, then went stale itself — "
        "hence this machinery).*",
        "",
        f"**Read:** 🔴 = a surface that claims auto-refresh but its machinery didn't run (>{THRESHOLDS['auto']}d). "
        f"🟡 = memory core aging past {THRESHOLDS['memory']}d, or other surfaces past {THRESHOLDS['other']}d. "
        "Aging ≠ wrong — it means *verify or refresh*.",
        "",
        "---",
        "",
    ]
    if result.get("healed"):
        lines += ["🔵 **Self-heal ran this pass:** " + " · ".join(f"`{s}`" for s in result["healed"]) +
                  " — findings below are POST-heal.", ""]
    lines += _section("## 🔴 Auto-claims with stalled machinery", f["auto"])
    lines += _section(f"## 🟡 Memory core aging (>{THRESHOLDS['memory']}d)", f["memory"])
    lines += _section(f"## 🟡 Other surfaces aging (>{THRESHOLDS['other']}d)", f["other"])
    lines += [
        "---",
        "",
        "*Ember/autoloop reads this to pick refresh work. James reads only the 🔴 row count: "
        "zero means the vault's promises hold.*",
    ]
    return "\n".join(lines) + "\n"


def heal(result: dict, runner=None) -> list[str]:
    """Self-healing rung (blessed by James 2026-06-10): for each 🔴 finding whose
    generator is on the explicit allowlist, re-run it. Allowlist-only, idempotent
    scripts, never daily_sync (recursion). Returns the scripts run."""
    import subprocess
    import sys

    def _default_runner(script: str) -> bool:
        try:
            return subprocess.run([sys.executable, str(REPO_ROOT / script)],
                                  capture_output=True, timeout=120).returncode == 0
        except Exception:
            return False

    runner = runner or _default_runner
    ran: list[str] = []
    for finding in result["findings"]["auto"]:
        for script in HEAL_COMMANDS.get(finding["file"], []):
            if script not in ran:
                runner(script)
                ran.append(script)
    return ran


def write_report(vault: Path | str = VAULT, now: dt.datetime | None = None,
                 self_heal: bool = False, runner=None) -> dict:
    vault = Path(vault)
    result = audit(vault, now)
    healed: list[str] = []
    if self_heal and result["findings"]["auto"]:
        healed = heal(result, runner)
        if healed:
            result = audit(vault, now)  # re-audit: report post-heal truth
    result["healed"] = healed
    (vault / REPORT_REL).write_text(render(result), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--heal", action="store_true",
                    help="re-run allowlisted generators for 🔴 findings, then re-audit")
    args = ap.parse_args(argv)
    result = write_report(self_heal=args.heal)
    f = result["findings"]
    healed = f" healed={len(result['healed'])}" if result["healed"] else ""
    print(f"freshness: scanned={result['scanned']} 🔴auto={len(f['auto'])} "
          f"🟡memory={len(f['memory'])} 🟡other={len(f['other'])}{healed} → {REPORT_REL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
