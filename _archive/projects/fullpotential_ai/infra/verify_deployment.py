#!/usr/bin/env python3
"""Deployment verifier that checks critical endpoints for availability."""

from __future__ import annotations

import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable, Tuple


TARGETS: Iterable[Tuple[str, str]] = (
    ("https://fullpotential.ai/missions", "Mission Control"),
    ("https://fullpotential.com/accelerator-kit", "Accelerator"),
    ("http://127.0.0.1:8001/health", "Registry"),
)

TIMEOUT_SECONDS = 15
SCRIPT_DIR = Path(__file__).resolve().parent
ALERT_FILE = SCRIPT_DIR / "ALERTS.md"
USER_AGENT = "FPAI-Deployment-Verify/1.0"


def fetch(url: str) -> Tuple[int, str]:
    """Fetch content from URL and return status code plus decoded body."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS, context=context) as resp:
        code = resp.getcode()
        body = resp.read().decode("utf-8", "ignore")
    return code, body


def record_alert(url: str) -> None:
    """Append alert notification to ALERTS.md."""
    ALERT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with ALERT_FILE.open("a", encoding="utf-8") as handle:
        handle.write(f"🚨 DEPLOYMENT FAILURE: {url} is down.\n")


def verify_targets(targets: Iterable[Tuple[str, str]]) -> int:
    """Verify all targets and return exit status."""
    failures = 0
    for url, expected_text in targets:
        try:
            status_code, body = fetch(url)
            body_lower = body.lower()
            expected_lower = expected_text.lower()
            status_ok = status_code == 200
            content_ok = expected_lower in body_lower
            if status_ok and content_ok:
                print(f"✅ PASS: {url}")
                continue
            print(f"❌ FAIL: {url} (Got {status_code})")
        except urllib.error.HTTPError as http_err:
            failures += 1
            print(f"❌ FAIL: {url} (Got {http_err.code})")
            record_alert(url)
            continue
        except urllib.error.URLError as url_err:
            failures += 1
            reason = getattr(url_err.reason, "strerror", url_err.reason)
            print(f"❌ FAIL: {url} (Got {reason})")
            record_alert(url)
            continue
        except Exception as exc:  # pragma: no cover - safety net
            failures += 1
            print(f"❌ FAIL: {url} (Got {exc})")
            record_alert(url)
            continue

        if not (status_ok and content_ok):
            failures += 1
            record_alert(url)

    return 1 if failures else 0


def main() -> int:
    return verify_targets(TARGETS)


if __name__ == "__main__":
    sys.exit(main())






