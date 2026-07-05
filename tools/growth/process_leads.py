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
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
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
META_PIXEL_ID = os.environ.get("META_PIXEL_ID", "110851475615838")
META_API_VERSION = os.environ.get("META_API_VERSION", "v20.0")
META_ENV = Path(os.environ.get("META_ENV_FILE", "/root/.config/fpai/meta.env"))
BREVO_ENV = Path(os.environ.get("BREVO_ENV_FILE", "/root/.config/fpai/brevo.env"))
ASSESSMENT_URL = os.environ.get("ASSESSMENT_URL", "https://fullpotential.com/assessment")


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


def read_env_value(path: Path, key: str) -> str:
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return ""
    prefix = f"{key}="
    for line in lines:
        if line.strip().startswith(prefix):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def meta_access_token() -> str:
    return (
        os.environ.get("META_CONVERSIONS_API_TOKEN")
        or os.environ.get("META_CAPI_TOKEN")
        or os.environ.get("META_ACCESS_TOKEN")
        or read_env_value(META_ENV, "META_CONVERSIONS_API_TOKEN")
        or read_env_value(META_ENV, "META_CAPI_TOKEN")
        or read_env_value(META_ENV, "META_ACCESS_TOKEN")
    )


def _sha256_normalized(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def meta_lead_payload(*, lead_id: str, email: str, event_time: int | None = None) -> dict:
    return {
        "data": [
            {
                "event_name": "Lead",
                "event_time": int(event_time or time.time()),
                "event_id": lead_id,
                "action_source": "website",
                "event_source_url": ASSESSMENT_URL,
                "user_data": {"em": [_sha256_normalized(email)]},
            }
        ]
    }


def send_meta_lead_event(*, lead_id: str, email: str, access_token: str, pixel_id: str = META_PIXEL_ID) -> tuple[bool, str]:
    if not access_token:
        return (False, "missing Meta access token")
    if not pixel_id:
        return (False, "missing Meta pixel id")
    if not email:
        return (False, "missing lead email")

    url = f"https://graph.facebook.com/{META_API_VERSION}/{pixel_id}/events?access_token={access_token}"
    req = urllib.request.Request(
        url,
        data=json.dumps(meta_lead_payload(lead_id=lead_id, email=email)).encode(),
        headers={"content-type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return (200 <= resp.status < 300, f"HTTP {resp.status}: {body[:300]}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        return (False, f"HTTP {e.code}: {detail}")
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="actually send emails (default: dry-run)")
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args(argv)

    if KILL.exists():
        print("[leads] kill-switch present — exiting")
        return 0

    STATE.parent.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    processed = set(STATE.read_text().split()) if STATE.exists() else set()

    brevo_key = ""
    if BREVO_ENV.exists():
        for line in BREVO_ENV.read_text().splitlines():
            if line.startswith("BREVO_API_KEY="):
                brevo_key = line.split("=", 1)[1].strip().strip('"')
    meta_token = meta_access_token()

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
        deliverable = out.read_text().rstrip() + (
            "\n\n—\nJames Sunheart + AI\n"
            "Full Potential · fullpotential.com  ·  Allocation Intelligence · fullpotential.ai"
        )
        subject = "Your Full Potential Assessment — Allocation Score inside"

        print(f"\n===== {lead_id} → {email} =====")
        if not args.live:
            print(f"[DRY-RUN] would email {email} ({len(deliverable)} chars). First lines:")
            print("\n".join(deliverable.splitlines()[:6]))
            continue

        ok, detail = send_email(email, name, subject, deliverable, brevo_key)
        if ok:
            meta_ok, meta_detail = send_meta_lead_event(lead_id=lead_id, email=email, access_token=meta_token)
            processed.add(lead_id)
            done += 1
            meta_status = "Meta CAPI Lead sent" if meta_ok else f"Meta CAPI Lead failed: {meta_detail}"
            tg_alert(
                f"✅ New assessment lead scored + delivered: {name} <{email}>. Deliverable emailed. {meta_status}",
                os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            )
            print(f"[leads] SENT {lead_id} → {email} ({detail}); {meta_status}")
        else:
            print(f"[leads] SEND FAILED {lead_id}: {detail}")

    if args.live:
        STATE.write_text("\n".join(sorted(processed)))
    print(f"[leads] done — {done} delivered this run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
