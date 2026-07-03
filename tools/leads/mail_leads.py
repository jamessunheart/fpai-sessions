#!/usr/bin/env python3
"""
mail_leads · watches the 198 leads dir and emails each new application to James.

Why laptop-side: 198 prod code is James-gated; this reads 198 (read-only ssh,
deploy key) and sends via the proven SMTP relays from email_health/accounts.json.

To: james@fullpotential.com · Reply-To: the applicant (hit reply to answer them).
State: ~/.config/fpai/leads_mailer/seen.txt · Runs via launchd every 10 min.
"""
import json, os, re, smtplib, ssl, subprocess
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

HOME = Path.home()
KEY = HOME / ".ssh" / "fpai_deploy_ed25519"
SERVER = "root@198.54.123.234"
LEADS = "/var/lib/full-potential/leads"
STATE_DIR = HOME / ".config" / "fpai" / "leads_mailer"
SEEN = STATE_DIR / "seen.txt"
ACCOUNTS = HOME / ".config" / "fpai" / "email_health" / "accounts.json"
TO = "james@fullpotential.com"

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE  # same posture as email canary (self-hosted relays)


def sh(cmd, timeout=25):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.stdout


def remote(cmd):
    return sh(["ssh", "-i", str(KEY), "-o", "StrictHostKeyChecking=no",
               "-o", "ConnectTimeout=12", SERVER, cmd])


def send(subject, body, reply_to=None):
    cfg = json.loads(ACCOUNTS.read_text())
    relays = cfg.get("smtp_relays", [])
    from_addr = cfg.get("email_alert_from") or "canary@fullpotential.com"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"FP AI Builders <{from_addr}>"
    msg["To"] = TO
    if reply_to:
        msg["Reply-To"] = reply_to
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=from_addr.split("@")[-1])
    msg.set_content(body)
    last = ""
    for r in relays:
        try:
            if r.get("tls") == "smtps":
                s = smtplib.SMTP_SSL(r["host"], int(r["port"]), timeout=15, context=_SSL)
            else:
                s = smtplib.SMTP(r["host"], int(r["port"]), timeout=15)
                s.starttls(context=_SSL)
            s.login(r["username"], r["password"])
            s.send_message(msg)
            s.quit()
            return True, r["host"]
        except Exception as e:
            last = f"{r['host']}: {e}"
    return False, last


def main():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    seen = set(SEEN.read_text().split()) if SEEN.exists() else set()
    listing = remote(f"ls -1 {LEADS}/*.md 2>/dev/null").split()
    new = [p for p in listing if os.path.basename(p) not in seen]
    if not new:
        print(json.dumps({"ok": True, "new": 0})); return
    sent = 0
    for p in new[:10]:  # safety cap per run
        base = os.path.basename(p)
        body = remote(f"cat '{p}'")
        m_name = re.search(r"^name:\s*(.+)$", body, re.M)
        m_mail = re.search(r"^email:\s*(.+)$", body, re.M)
        name = (m_name.group(1).strip() if m_name else base)
        applicant = (m_mail.group(1).strip() if m_mail else None)
        m_int = re.search(r"^interest:\s*(.+)$", body, re.M)
        interest = (m_int.group(1).strip() if m_int else "lead")
        subject = f"🛠️ New application — {name} ({interest})"
        ok, via = send(subject, body + "\n\n—\nReply to this email to answer the applicant directly.", reply_to=applicant)
        if ok:
            seen.add(base); sent += 1
        else:
            print(json.dumps({"ok": False, "file": base, "err": via})); break
    SEEN.write_text("\n".join(sorted(seen)))
    print(json.dumps({"ok": True, "new": len(new), "sent": sent}))


if __name__ == "__main__":
    main()
