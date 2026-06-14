from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "comms-hub"


def run_cli(tmp_path, *args):
    env = os.environ.copy()
    env["COMMS_HUB_VAR_DIR"] = str(tmp_path)
    env["COMMS_HUB_DRY_RUN"] = "1"
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def test_send_inbox_drain_and_health_commands(tmp_path):
    sent = run_cli(tmp_path, "send", "--to", "james", "--body", "cli smoke")
    received = run_cli(tmp_path, "receive", "--to", "system", "--body", "/system status")
    health = run_cli(tmp_path, "health")
    drained = run_cli(tmp_path, "drain", "--dry-run")
    dispatched = run_cli(tmp_path, "dispatch")
    ticked = run_cli(tmp_path, "tick")
    tg_status = run_cli(tmp_path, "tg-status")
    inbox = run_cli(tmp_path, "inbox", "--limit", "20")

    assert sent["queued"] is True
    assert received["received"] is True
    assert health["service"] == "comms-hub"
    assert drained["drained"] is True
    assert dispatched["dispatched"] is True
    assert ticked["tick"] is True
    assert ticked["poll"]["polled"] is True
    assert tg_status["will_call_get_updates"] is False
    assert len(inbox) == 1
