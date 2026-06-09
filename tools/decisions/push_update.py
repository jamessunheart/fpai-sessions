#!/usr/bin/env python3
"""
push_update · v1 · 2026-05-31
Proactively text James (via @sunheartbrain_bot) the two things that matter:
  1. Decisions that bottleneck progress (the open questions on THE PLATE)
  2. Build updates — what shipped + what's building
Deterministic (no LLM) → ~$0. Sends only when something CHANGED (anti-spam).
Reuses send_tg_digest's Telegram sender. Read-only on the vault.

Usage:  push_update.py            # send if changed
        push_update.py --force    # send regardless
        push_update.py --print    # print only, don't send
"""
import re, sys, hashlib, datetime, argparse
from pathlib import Path

VAULT = Path.home() / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS"
DECIDE = VAULT / "00_MEMORY" / "DECISIONS.md"  # single source of only-you decisions
PROOF = VAULT / "00_MEMORY" / "PROOF LOG.md"
STATE = Path.home() / ".config" / "fpai" / "push" / "last.txt"

def plate_decisions():
    """Open decisions from the single source (DECISIONS.md · '## 🟡 Open'). Same list the daily note shows."""
    if not DECIDE.exists(): return []
    txt = DECIDE.read_text(errors="ignore")
    if "## 🟡 Open" not in txt: return []
    seg = txt.split("## 🟡 Open", 1)[1].split("\n## ", 1)[0]
    return [m.group(1).strip() for m in re.finditer(r"^- (?:🟡|🎁) \*\*(.+?)\*\*", seg, re.M)]

def today_builds():
    if not PROOF.exists(): return []
    today = datetime.date.today().isoformat()
    out = []
    for line in PROOF.read_text(errors="ignore").splitlines():
        if line.startswith(f"- **{today}"):
            bolds = re.findall(r"\*\*(.+?)\*\*", line)
            title = next((b for b in bolds if not b.startswith(today)), None)
            if title: out.append(title.strip())
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--print", dest="pr", action="store_true")
    a = ap.parse_args()

    decisions = plate_decisions()
    builds = today_builds()
    sig = hashlib.md5(("|".join(decisions) + "##" + str(len(builds))).encode()).hexdigest()

    lines = ["🧭 <b>System update</b>"]
    if decisions:
        lines.append(f"\n🍽️ <b>On your plate ({len(decisions)} decisions):</b>")
        for d in decisions[:3]:
            lines.append(f"  • {d}")
        lines.append("  → reply here with the verb, or open DECISIONS.")
    else:
        lines.append("\n🍽️ Plate clear — nothing waiting on you.")
    if builds:
        lines.append(f"\n🛠 <b>Shipped today ({len(builds)}):</b>")
        for b in builds[:5]:
            lines.append(f"  ✅ {b}")
        if len(builds) > 5:
            lines.append(f"  …+{len(builds)-5} more")
    text = "\n".join(lines)

    if a.pr:
        print(text); return
    STATE.parent.mkdir(parents=True, exist_ok=True)
    last = STATE.read_text().strip() if STATE.exists() else ""
    if sig == last and not a.force:
        print("no change since last push — skipping"); return
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        import send_tg_digest as tg
        creds = tg.load_creds()
        ok, msg = tg.send_to_telegram(text, creds)
        print(("sent" if ok else "send failed: ") + str(msg))
        if ok: STATE.write_text(sig)
    except Exception as e:
        print(f"push failed: {e}")

if __name__ == "__main__":
    main()
