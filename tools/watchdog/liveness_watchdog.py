#!/usr/bin/env python3
"""Autonomy liveness watchdog — James directive 2026-07-09.

The confidence organ for autonomous operation. The improver loops (council,
queue-builder, autoloop, HOT_STATE synth) already run on their own; what was
missing is a monitor that CONFIRMS they are alive and reaches OUT to James:

  - Every 24h  → "on track" ping with the latest updates (proof-of-life digest).
  - The moment a monitored loop goes stale/dead → immediate 🔴 STALLED ping.
  - When a stalled loop recovers → 🟢 recovered ping.

Report-only + notify-only. Mutates NO production state. $0 marginal (file reads
+ one curl per ping). Kill switch: touch ~/.config/fpai/watchdog/.disabled

Run every ~30 min via launchd/cron. Idempotent — safe to run as often as you like;
alerts de-dupe on state transitions and the daily ping fires at most once / 24h.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
REPO = Path(__file__).resolve().parents[2]
CFG = HOME / ".config" / "fpai" / "watchdog"
CFG.mkdir(parents=True, exist_ok=True)
STATE_FILE = CFG / "state.json"
DISABLE_FILE = CFG / ".disabled"
NOTIFY = REPO / "tools" / "build_loop" / "notify_telegram.sh"
DAILY_PING_SECONDS = 24 * 3600

# name → (marker path, max age in minutes before we call it stalled)
# Only loops whose marker EXISTS are hard-alerted; a missing marker is reported
# as "unmonitored" in the daily digest (no false-alarm on a host that doesn't
# run that loop). Stale mtime is the death signal.
MONITORED = {
    "council-debate":   (HOME / ".config/fpai/council/runs.log",         30),
    "queue-builder":    (HOME / ".config/fpai/queue_builder/runs.log",   180),
    "hot-state-synth":  (HOME / ".config/fpai/hot_memory/HOT_STATE.md",  90),
    "autoloop":         (HOME / ".config/fpai/autoloop",                 360),
    "orchestrator":     (HOME / ".config/fpai/orchestrator",             360),
}


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def launchd_failures() -> dict[str, int]:
    """Every com.fpai.* launchd job whose LAST run exited nonzero → {label: exit}.

    Marker-mtime monitoring (MONITORED above) is blind to jobs that fail INSTANTLY:
    a job whose script is missing exits 127 and never writes a marker, so it looks
    'unmonitored' forever. launchctl's LastExitStatus is the ground truth for
    'did this loop's process actually succeed'. 127 = command/script not found.
    """
    try:
        out = subprocess.run(["launchctl", "list"], capture_output=True,
                             text=True, timeout=15).stdout
    except Exception:
        return {}
    failures: dict[str, int] = {}
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        pid, status, label = parts[0], parts[1], parts[2]
        if not label.startswith("com.fpai."):
            continue
        # A currently-running job (numeric pid) has no meaningful last-exit yet.
        if pid.strip().isdigit():
            continue
        try:
            code = int(status.strip())
        except ValueError:
            continue
        if code != 0:
            failures[label] = code
    return failures


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"loops": {}, "last_daily_ping": None}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def marker_age_minutes(path: Path):
    """Newest mtime under path (file or dir tree). None if the marker is absent."""
    if not path.exists():
        return None
    try:
        if path.is_dir():
            mtimes = [p.stat().st_mtime for p in path.rglob("*") if p.is_file()]
            if not mtimes:
                mtimes = [path.stat().st_mtime]
            newest = max(mtimes)
        else:
            newest = path.stat().st_mtime
    except OSError:
        return None
    return (now().timestamp() - newest) / 60.0


def ping(msg: str) -> None:
    try:
        subprocess.run(["bash", str(NOTIFY), msg], timeout=30,
                       capture_output=True, text=True)
    except Exception:
        pass  # never break the watchdog on a send failure


def recent_updates() -> str:
    """A few lines of 'what shipped' for the daily on-track digest."""
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "log", "--oneline", "-6",
             "--grep=build\\|feat\\|Merge", "-E"],
            capture_output=True, text=True, timeout=15).stdout.strip()
        return out or "(no recent build commits)"
    except Exception:
        return "(git log unavailable)"


def treasury_line() -> str:
    hs = HOME / ".config/fpai/hot_memory/HOT_STATE.md"
    try:
        for line in hs.read_text().splitlines():
            if "Treasury" in line:
                return line.strip("- *").strip()[:160]
    except OSError:
        pass
    return "treasury: see HOT_STATE"


def main() -> int:
    if DISABLE_FILE.exists():
        return 0

    state = load_state()
    loops = state.setdefault("loops", {})
    alive, stalled, unmonitored = [], [], []

    for name, (path, max_age) in MONITORED.items():
        age = marker_age_minutes(path)
        prev = loops.get(name, {}).get("status", "unknown")

        if age is None:
            unmonitored.append(name)
            loops[name] = {"status": "unmonitored", "age_min": None}
            continue

        is_alive = age <= max_age
        status = "alive" if is_alive else "stalled"
        loops[name] = {"status": status, "age_min": round(age, 1)}

        if is_alive:
            alive.append(f"{name} ({int(age)}m)")
            if prev == "stalled":
                ping(f"🟢 <b>RECOVERED</b> — <code>{name}</code> is firing again "
                     f"(last beat {int(age)}m ago). Autonomy back on track.")
        else:
            stalled.append(f"{name} (stale {int(age)}m, limit {max_age}m)")
            if prev != "stalled":  # transition → alert once
                ping(f"🔴 <b>STALLED</b> — <code>{name}</code> hasn't fired in "
                     f"{int(age)}m (limit {max_age}m). A loop died silently. "
                     f"System is NOT fully autonomous right now.")

    # launchd exit-code health — catches jobs that fail instantly (missing script →
    # exit 127) which marker-mtime monitoring can never see.
    failures = launchd_failures()
    prev_failures = state.get("launchd_failures", {})
    new_breaks = {lbl: code for lbl, code in failures.items() if str(prev_failures.get(lbl)) != str(code)}
    recovered = [lbl for lbl in prev_failures if lbl not in failures]
    for lbl, code in new_breaks.items():
        hint = " (script/binary not found)" if code == 127 else ""
        ping(f"🔴 <b>JOB BROKEN</b> — <code>{lbl}</code> last exited "
             f"<b>{code}</b>{hint}. A scheduled loop is failing silently.")
    for lbl in recovered:
        ping(f"🟢 <b>JOB RECOVERED</b> — <code>{lbl}</code> is exiting clean again.")
    state["launchd_failures"] = failures

    # Daily on-track digest
    last = state.get("last_daily_ping")
    due = last is None or (now().timestamp() - dt.datetime.fromisoformat(last).timestamp()) >= DAILY_PING_SECONDS
    if due:
        head = "✅ <b>ON TRACK</b>" if not (stalled or failures) else "⚠️ <b>PARTIAL</b>"
        body = [
            f"{head} — autonomous run, 24h check-in.",
            f"🟢 Alive: {', '.join(alive) if alive else 'none'}",
        ]
        if stalled:
            body.append(f"🔴 Stalled: {', '.join(stalled)}")
        if failures:
            body.append("🔴 Broken jobs (nonzero exit): "
                        + ', '.join(f"{lbl.replace('com.fpai.','')}={code}"
                                    for lbl, code in sorted(failures.items())))
        if unmonitored:
            body.append(f"⚪ Unmonitored here: {', '.join(unmonitored)}")
        body.append(f"💰 {treasury_line()}")
        body.append("📦 Latest:\n" + recent_updates())
        ping("\n".join(body))
        state["last_daily_ping"] = now().isoformat()

    save_state(state)
    print(f"watchdog: alive={len(alive)} stalled={len(stalled)} "
          f"broken={len(failures)} unmonitored={len(unmonitored)} "
          f"daily_ping={'sent' if due else 'no'}")
    if failures:
        print("  broken jobs: " + ", ".join(f"{l}={c}" for l, c in sorted(failures.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
