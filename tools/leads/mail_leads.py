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
    """Deliver via 162 -> direct to MX (port 25). Proven 2026-07-03: authenticated
    relay sends got swallowed (209 hosts a phantom fullpotential.com domain; Brevo
    drops self-sends). Direct-to-MX from 162 lands in the real inbox."""
    doc = json.dumps({"subject": subject, "body": body, "reply_to": reply_to or ""})
    script = """
import smtplib, sys, json
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
d = json.loads(sys.stdin.read())
m = EmailMessage()
m["Subject"] = d["subject"]
m["From"] = "FP AI Builders <noreply@sunheart.com>"
m["To"] = "james@fullpotential.com"
if d.get("reply_to"):
    m["Reply-To"] = d["reply_to"]
m["Date"] = formatdate(localtime=True)
m["Message-ID"] = make_msgid(domain="sunheart.com")
m.set_content(d["body"])
s = smtplib.SMTP("mail.fullpotential.com", 25, timeout=20)
s.send_message(m); s.quit(); print("sent")
"""
    r = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=12", "root@162.0.208.88",
         "T=$(mktemp); cat > $T; python3 $T <<< '" + doc.replace("'", "'\\''") + "'"],
        input=script, capture_output=True, text=True, timeout=45)
    ok = "sent" in r.stdout
    return ok, (r.stderr.strip()[:150] or "162→MX")


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
