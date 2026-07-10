#!/usr/bin/env python3
"""One-time secure capture of the Mailsac API key. James runs this in his own
terminal; the key is read hidden (getpass -> not echoed, not in shell history),
stored with restricted permissions, validated with the smallest authenticated
request, and never printed. Reports only success + a non-secret fingerprint.
"""
from __future__ import annotations

import getpass
import hashlib
import json
import os
import stat
import sys
import urllib.error
import urllib.request
from pathlib import Path

CRED_DIR = Path.home() / ".config" / "fpai" / "credentials"
CRED_FILE = CRED_DIR / "mailsac.env"


def _validate(key: str) -> tuple[bool, str]:
    """Smallest safe authenticated request: GET /api/me."""
    req = urllib.request.Request("https://mailsac.com/api/me",
                                 headers={"Mailsac-Key": key})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        # non-secret confirmation only (an account id / email domain, not the key)
        who = data.get("_id") or data.get("email") or "account"
        return True, f"authenticated as {who}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code} (key rejected)" if e.code in (401, 403) else f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}"


def main() -> int:
    key = getpass.getpass("Paste Mailsac API key (hidden, not echoed): ").strip()
    if not key:
        print("No key entered. Aborted.", file=sys.stderr)
        return 2

    ok, detail = _validate(key)
    if not ok:
        del key
        print(f"❌ Key did NOT validate: {detail}. Nothing written.", file=sys.stderr)
        return 1

    CRED_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CRED_DIR, stat.S_IRWXU)  # 700
    # Preserve any other keys already in the file; replace only MAILSAC_KEY.
    lines = []
    if CRED_FILE.exists():
        lines = [l for l in CRED_FILE.read_text().splitlines()
                 if l.strip() and not l.startswith("MAILSAC_KEY=")]
    lines.append(f"MAILSAC_KEY={key}")
    CRED_FILE.write_text("\n".join(lines) + "\n")
    os.chmod(CRED_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 600

    fingerprint = hashlib.sha256(key.encode()).hexdigest()[:12]
    del key
    print("✅ Mailsac key stored securely.")
    print(f"   location : {CRED_FILE}  (perms 600, dir 700)")
    print(f"   validated: {detail}")
    print(f"   fingerprint (non-secret): sha256:{fingerprint}")
    print("   Tell Ember this fingerprint; the secret itself was never printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
