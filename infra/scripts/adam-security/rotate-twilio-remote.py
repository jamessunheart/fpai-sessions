#!/usr/bin/env python3
"""Run on server once: TWILIO_NEW=... python3 rotate-twilio-remote.py"""
import os
import re
import shutil
import time

t = os.environ.get("TWILIO_NEW", "").strip()
if not t:
    raise SystemExit("Set TWILIO_NEW to the new auth token")
sid_new = os.environ.get("TWILIO_SID_NEW", "").strip()

ts = int(time.time())

files_env = ["/opt/fpai/voice-phone/.env", "/opt/fpai/aria-command/.env"]
for p in files_env:
    shutil.copy2(p, p + ".bak-twilio-" + str(ts))
    s = open(p, encoding="utf-8").read()
    s2, n = re.subn(r"^TWILIO_AUTH_TOKEN=.*$", "TWILIO_AUTH_TOKEN=" + t, s, flags=re.M)
    if n != 1:
        raise SystemExit(f"TWILIO_AUTH_TOKEN replace count {n} in {p}")
    if sid_new:
        s2, n = re.subn(r"^TWILIO_ACCOUNT_SID=.*$", "TWILIO_ACCOUNT_SID=" + sid_new, s2, flags=re.M)
        if n != 1:
            raise SystemExit(f"TWILIO_ACCOUNT_SID replace count {n} in {p}")
    open(p, "w", encoding="utf-8").write(s2)
    os.chmod(p, 0o600)
    print("ok", p)

cj = "/opt/fpai/voice-caller/call_james.py"
shutil.copy2(cj, cj + ".bak-twilio-" + str(ts))
s = open(cj, encoding="utf-8").read()
s2, n = re.subn(r'TWILIO_TOKEN = "[^"]*"', 'TWILIO_TOKEN = "' + t + '"', s, count=1)
if n != 1:
    raise SystemExit(f"call_james TWILIO_TOKEN replace count {n}")
if sid_new:
    s2, n2 = re.subn(r'TWILIO_SID = "[^"]*"', 'TWILIO_SID = "' + sid_new + '"', s2, count=1)
    if n2 != 1:
        raise SystemExit(f"call_james TWILIO_SID replace count {n2}")
open(cj, "w", encoding="utf-8").write(s2)
print("ok", cj)

wp = "/opt/fpai/aria/whatsapp.py"
if os.path.exists(wp):
    shutil.copy2(wp, wp + ".bak-twilio-" + str(ts))
    s = open(wp, encoding="utf-8").read()
    s2, n = re.subn(
        r'TWILIO_AUTH_TOKEN = os\.getenv\("TWILIO_AUTH_TOKEN",\s*"[^"]*"\)',
        'TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")',
        s,
        count=1,
    )
    if n != 1:
        print("skip whatsapp.py (pattern not found or already clean)")
    else:
        open(wp, "w", encoding="utf-8").write(s2)
        print("ok", wp)

print("done")
