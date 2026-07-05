#!/usr/bin/env python3
"""REALIZE the funnel — score each new lead and email the deliverable (closes d193).

The /assessment funnel (champion-sign on 198) captures leads to
/var/lib/full-potential/leads/*.md but never delivered the promised Allocation
Score. This worker closes that loop:

  new lead  →  score_assessment.py  →  email the deliverable  →  alert James  →  mark done

$0-marginal (score_assessment.py runs on the Max subscription CLI; Brevo sends).
Dry-run by default — pass --live to actually send. Skips test/smoke leads.
Kill switch: touch /opt/fpai-build/.leads_worker_disabled
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path("/opt/fpai-build/FPAI_Cockpit")
SCORER = REPO / "tools" / "growth" / "score_assessment.py"
REMOTE = "root@198.54.123.234"
REMOTE_LEADS = "/var/lib/full-potential/leads"
STATE = Path("/root/.config/fpai/leads_worker/processed.txt")
WORK = Path("/tmp/leads_work")
KILL = Path("/opt/fpai-build/.leads_worker_disabled")
TG_OWNER = os.environ.get("OWNER_TG_ID") or os.environ.get("TELEGRAM_CHAT_ID") or "8514069423"
SENDER_EMAIL = os.environ.get("ASSESSMENT_SENDER_EMAIL", "james@fullpotential.ai")
SENDER_NAME = os.environ.get("ASSESSMENT_SENDER_NAME", "Full Potential")
SKIP_EMAILS = {"test@test.test", ""}
SKIP_NAME_MARKERS = ("__smoke_test__", "smoke_test", "test ember")


def _ssh(cmd: str) -> str:
    r = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=8", "-o", "BatchMode=yes", REMOTE, cmd],
        capture_output=True, text=True, timeout=40,
    )
    return r.stdout


def list_remote_leads() -> list[str]:
    out = _ssh(f"ls -t {REMOTE_LEADS}/*.md 2>/dev/null | grep -v audit || true")
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def fetch_lead(remote_path: str, local: Path) -> str:
    content = _ssh(f"cat {remote_path}")
    local.write_text(content, encoding="utf-8")
    return content


def parse_frontmatter(text: str) -> dict:
    fm = {}
    m = re.search(r"^---\n(.*?)\n---", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip()
    return fm


def send_email(to_email: str, to_name: str, subject: str, md_body: str, api_key: str) -> tuple[bool, str]:
    # Deliver the markdown as a readable text email (kept simple + deliverable; HTML polish later).
    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to": [{"email": to_email, "name": to_name or to_email}],
        "subject": subject,
        "textContent": md_body,
    }
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode(),
        headers={"api-key": api_key, "content-type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return (200 <= resp.status < 300, f"HTTP {resp.status}")
    except Exception as e:  # noqa: BLE001
        return (False, str(e))


def tg_alert(msg: str, token: str) -> None:
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=json.dumps({"chat_id": TG_OWNER, "text": msg}).encode(),
            headers={"content-type": "application/json"}, method="POST",
        )
        urllib.request.urlopen(req, timeout=15)
    except Exception:  # noqa: BLE001
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="actually send emails (default: dry-run)")
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()

    if KILL.exists():
        print("[leads] kill-switch present — exiting")
        return 0

    STATE.parent.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    processed = set(STATE.read_text().split()) if STATE.exists() else set()

    brevo_key = ""
    env = Path("/root/.config/fpai/brevo.env")
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("BREVO_API_KEY="):
                brevo_key = line.split("=", 1)[1].strip().strip('"')

    leads = list_remote_leads()
    print(f"[leads] {len(leads)} remote lead(s); {len(processed)} already processed")
    done = 0
    for rp in leads:
        lead_id = Path(rp).stem
        if lead_id in processed:
            continue
        if done >= args.limit:
            break
        local = WORK / f"{lead_id}.md"
        content = fetch_lead(rp, local)
        fm = parse_frontmatter(content)
        email = fm.get("email", "").lower()
        name = fm.get("name", "")
        if email in SKIP_EMAILS or any(mk in (name.lower() + email) for mk in SKIP_NAME_MARKERS):
            print(f"[leads] SKIP test lead: {lead_id} ({email})")
            processed.add(lead_id)
            continue

        out = WORK / f"{lead_id}.deliverable.md"
        r = subprocess.run(
            ["python3", str(SCORER), "--lead", str(local), "--out", str(out)],
            capture_output=True, text=True, timeout=180, cwd=str(REPO),
        )
        if r.returncode != 0 or not out.exists():
            print(f"[leads] SCORE FAILED {lead_id}: {r.stderr[-200:]}")
            continue
        deliverable = out.read_text()
        subject = "Your Full Potential Assessment — Allocation Score inside"

        print(f"\n===== {lead_id} → {email} =====")
        if not args.live:
            print(f"[DRY-RUN] would email {email} ({len(deliverable)} chars). First lines:")
            print("\n".join(deliverable.splitlines()[:6]))
            continue

        ok, detail = send_email(email, name, subject, deliverable, brevo_key)
        if ok:
            processed.add(lead_id)
            done += 1
            tg_alert(f"✅ New assessment lead scored + delivered: {name} <{email}>. Deliverable emailed.", os.environ.get("TELEGRAM_BOT_TOKEN", ""))
            print(f"[leads] SENT {lead_id} → {email} ({detail})")
        else:
            print(f"[leads] SEND FAILED {lead_id}: {detail}")

    if args.live:
        STATE.write_text("\n".join(sorted(processed)))
    print(f"[leads] done — {done} delivered this run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
