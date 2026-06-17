#!/usr/bin/env python3
"""Council debate over James's surfaced intents.

The council now uses a true multi-model route where available:

- Pragmatist: GLM-5.2 via Z-AI/local endpoint when configured, otherwise Claude.
- Visionary: Claude Opus/Max via ``claude -p``.
- Skeptic: Claude Opus/Max via ``claude -p``.

The runtime guardrails remain: change-gated, daily-capped, one proposal surfaced,
and all metered GLM usage logged separately from flat-rate Claude/Codex calls.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from pathlib import Path
import re as _re
import ssl
import subprocess
import sys
from typing import Any, Callable


HOME = os.path.expanduser("~")
HOST = os.environ.get("BRAIN_HOST", "root@162.0.208.88")
SERVER_MODE = os.path.isdir("/opt/sh-brain-src/curator")


def _default_repo() -> str:
    env_repo = os.environ.get("FPAI_REPO")
    if env_repo:
        return env_repo
    server_repo = "/opt/fpai-build/FPAI_Cockpit"
    if SERVER_MODE:
        return server_repo
    cwd = Path.cwd()
    if (cwd / "tools" / "cost" / "track.py").exists():
        return str(cwd)
    return HOME + "/FPAI_Cockpit"


REPO = _default_repo()
CLAUDE = os.path.expanduser(os.environ.get("CLAUDE_BIN", "~/.local/bin/claude"))
CODEX = os.path.expanduser(os.environ.get("CODEX_BIN", "~/.local/bin/codex"))
CFG = HOME + "/.config/fpai/council"
DAILY_CAP = float(os.environ.get("COUNCIL_DAILY_USD", "3.0"))
GLM_DAILY_CAP = float(os.environ.get("GLM_COUNCIL_DAILY_USD", "5.0"))
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
ENV = (
    'ENVFILE=$(systemctl show sh-brain-tgbot -p EnvironmentFiles 2>/dev/null | '
    'sed -E "s/EnvironmentFiles=//; s/ .*//"); cd /opt/sh-brain-src && set -a; '
    '. "$ENVFILE" 2>/dev/null; set +a;'
)

sys.path.insert(0, REPO + "/tools/cost")
sys.path.insert(0, REPO)

try:
    import track  # type: ignore
except Exception:  # pragma: no cover - only used outside repo-shaped test envs
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cost"))
    import track  # type: ignore

try:
    from curator.blueprints.manager import build_blueprint_context
except Exception:
    build_blueprint_context = None

try:
    from . import glm_client
except Exception:
    try:
        import glm_client  # type: ignore
    except Exception:
        glm_client = None  # type: ignore

try:
    from .self_diagnostic import is_decision_queue_empty, run_diagnostic_dialogue, trigger_from_files
except Exception:
    try:
        from self_diagnostic import is_decision_queue_empty, run_diagnostic_dialogue, trigger_from_files
    except Exception:
        is_decision_queue_empty = run_diagnostic_dialogue = trigger_from_files = None

try:
    import certifi

    SSLCTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSLCTX = ssl.create_default_context()


LensRunner = Callable[[str, str], str]


def _today_iso() -> str:
    return _dt.datetime.utcnow().date().isoformat()


def _estimate_tokens(*parts: str) -> int:
    text = "\n".join(p or "" for p in parts)
    return max(1, (len(text) + 3) // 4)


def _glm_cost(tokens_in: int, tokens_out: int) -> float:
    return round((tokens_in / 1_000_000 * 1.40) + (tokens_out / 1_000_000 * 4.40), 6)


def _glm_max_output_tokens() -> int:
    if glm_client is not None:
        try:
            return int(glm_client.configured_max_tokens())
        except Exception:
            pass
    return int(os.environ.get("GLM_MAX_TOKENS", "1200"))


def estimate_glm_call_cost(system_prompt: str, user_prompt: str) -> float:
    return _glm_cost(_estimate_tokens(system_prompt, user_prompt), _glm_max_output_tokens())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def glm_spend_today(ops_ledger: Path = DEFAULT_OPS_LEDGER) -> float:
    total = 0.0
    today = _today_iso()
    for row in _read_jsonl(ops_ledger):
        ts = str(row.get("ts") or row.get("timestamp") or "")
        if not ts.startswith(today):
            continue
        if str(row.get("model") or "").startswith("glm") or row.get("label") == "council.pragmatist":
            total += float(row.get("cost_usd") or row.get("est_usd") or 0.0)
    return round(total, 6)


def append_glm_ops_ledger(
    usage: dict[str, Any],
    *,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    model: str = "glm-5.2",
) -> dict[str, Any]:
    tokens_in = int(usage.get("tokens_in") or usage.get("input_tokens") or 0)
    tokens_out = int(usage.get("tokens_out") or usage.get("output_tokens") or 0)
    cost_usd = float(usage.get("cost_usd") or _glm_cost(tokens_in, tokens_out))
    row = {
        "ts": _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "loop": "council",
        "event": "glm_call",
        "label": "council.pragmatist",
        "lens": "pragmatist",
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": round(cost_usd, 6),
        "billing": "metered",
        "source": "z-ai" if os.environ.get("GLM_API_KEY") else "local",
    }
    ops_ledger.parent.mkdir(parents=True, exist_ok=True)
    with ops_ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def glm_available(
    env: dict[str, str] | None = None,
    *,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    estimated_call_cost: float = 0.0,
) -> tuple[bool, str]:
    env = env or os.environ
    if env.get("GLM_COUNCIL_DISABLE") == "1":
        return False, "disabled"
    if not (env.get("GLM_API_KEY") or env.get("GLM_LOCAL_URL")):
        return False, "not_configured"
    if glm_spend_today(ops_ledger) + max(0.0, estimated_call_cost) >= GLM_DAILY_CAP:
        return False, "daily_cap"
    return True, "available"


def run_claude(system_prompt: str, user_prompt: str, *, effort: str = "xhigh") -> str:
    prompt = system_prompt + "\n\n" + user_prompt
    r = subprocess.run(
        [CLAUDE, "-p", "--effort", effort, prompt],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return r.stdout.strip()


def run_pragmatist(system_prompt: str, user_prompt: str, *, ops_ledger: Path = DEFAULT_OPS_LEDGER) -> tuple[str, dict[str, Any]]:
    estimated_call_cost = estimate_glm_call_cost(system_prompt, user_prompt)
    available, reason = glm_available(ops_ledger=ops_ledger, estimated_call_cost=estimated_call_cost)
    if available and glm_client is not None:
        try:
            text = glm_client.call_glm(system_prompt, user_prompt)
            usage = glm_client.get_last_usage()
            if not usage:
                usage = {
                    "tokens_in": _estimate_tokens(system_prompt, user_prompt),
                    "tokens_out": _estimate_tokens(text),
                    "cost_usd": _glm_cost(_estimate_tokens(system_prompt, user_prompt), _estimate_tokens(text)),
                }
            model = str(usage.get("model") or os.environ.get("GLM_MODEL") or "glm-5.2")
            row = append_glm_ops_ledger(usage, ops_ledger=ops_ledger, model=model)
            return text, {"lens": "pragmatist", "model": model, "provider": "glm", "cost_usd": row["cost_usd"]}
        except glm_client.GLMUnavailableError as exc:
            reason = f"unavailable:{exc}"

    text = run_claude(system_prompt, user_prompt)
    return text, {"lens": "pragmatist", "model": "claude -p", "provider": "claude", "fallback_reason": reason, "cost_usd": 0.0}


def _lens_system(name: str) -> str:
    personas = {
        "pragmatist": "You are the Pragmatist lens: cheapest path to proof, what ships today. Return one concrete sentence.",
        "visionary": "You are the Visionary lens: long-term vision, network effects, and fundable story. Return one concrete sentence.",
        "skeptic": "You are the Skeptic lens: biggest risk, what not to build, and what breaks. Return one concrete sentence.",
    }
    return personas[name]


def run_lenses(context: str, *, ops_ledger: Path = DEFAULT_OPS_LEDGER) -> tuple[dict[str, str], list[dict[str, Any]]]:
    lenses: dict[str, str] = {}
    model_log: list[dict[str, Any]] = []

    text, meta = run_pragmatist(_lens_system("pragmatist"), context, ops_ledger=ops_ledger)
    lenses["pragmatist"] = text.strip()
    model_log.append(meta)

    for name in ("visionary", "skeptic"):
        lenses[name] = run_claude(_lens_system(name), context).strip()
        model_log.append({"lens": name, "model": "claude -p", "provider": "claude", "cost_usd": 0.0})

    return lenses, model_log


def synthesize_debate(lenses: dict[str, str], context: str, model_log: list[dict[str, Any]]) -> dict[str, Any]:
    sys_prompt = (
        "Goal: identify the single highest-leverage next build for a self-evolving AI platform, or propose "
        "nothing if no build clearly warrants it. James's attention is the scarcest resource. "
        "Hard boundaries: no duplicate proposals, no cruft, no builds that add complexity without clear proof value. "
        "Respond with ONLY valid JSON, no prose outside it: "
        "{\"pragmatist\":\"1 sentence\",\"visionary\":\"1 sentence\",\"skeptic\":\"1 sentence\","
        "\"synthesis\":\"one-paragraph verdict\",\"propose\":true|false,"
        "\"title\":\"<=8 words\",\"why\":\"one sentence\","
        "\"build_spec\":\"concrete: what to build, where, what the proof looks like\","
        "\"risk\":\"low\"|\"med\"}."
    )
    user_prompt = (
        "MODEL ROUTING LOG:\n"
        + json.dumps(model_log, sort_keys=True)
        + "\n\nLENS OUTPUTS:\n"
        + json.dumps(lenses, sort_keys=True)
        + "\n\nCONTEXT:\n"
        + context
    )
    txt = run_claude(sys_prompt, user_prompt)
    d = json.loads(txt[txt.find("{") : txt.rfind("}") + 1])
    d["model_log"] = model_log
    return d


def ssh(cmd: str, inp: str | None = None) -> str:
    return subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", HOST, ENV + " " + cmd],
        input=inp,
        capture_output=True,
        text=True,
        timeout=70,
    ).stdout


def run_curator(cmd: str, inp: str | None = None) -> str:
    if SERVER_MODE:
        full = (
            'ENVFILE=$(systemctl show sh-brain-tgbot -p EnvironmentFiles 2>/dev/null | '
            'sed -E "s/EnvironmentFiles=//; s/ .*//"); cd /opt/sh-brain-src && set -a; '
            '. "$ENVFILE" 2>/dev/null; . /root/.config/fpai/claude.env 2>/dev/null; set +a; '
            + cmd
        )
        return subprocess.run(["bash", "-c", full], input=inp, capture_output=True, text=True, timeout=70).stdout
    return ssh(cmd, inp)


def _ops(event: str, detail: str, nxt: str = "") -> None:
    try:
        subprocess.run(
            ["python3", REPO + "/tools/build_loop/ops_log.py", "council", event, detail, "$0", "", nxt],
            timeout=15,
        )
    except Exception:
        pass


def gpt_voice(intents: str) -> str:
    try:
        q = (
            "In 1-2 sentences only, no code and no file changes: given these intents + queue, what is the "
            "single highest-leverage thing this autonomous build system should build NEXT, and why? "
            "Be concrete and conservative.\n\n"
            + intents[:2500]
        )
        r = subprocess.run(
            [CODEX, "exec", "--cd", REPO, "--sandbox", "read-only", "--skip-git-repo-check", "-"],
            input=q,
            capture_output=True,
            text=True,
            timeout=150,
        )
        out = [line.strip() for line in r.stdout.splitlines() if line.strip()]

        def noise(line: str) -> bool:
            return (
                line.startswith("hook:")
                or line.lower() == "tokens used"
                or line.replace(",", "").isdigit()
                or line.startswith("EXIT=")
                or line.startswith("warning:")
                or line.startswith("[")
                or line.startswith("codex")
            )

        clean = [line for line in out if not noise(line)]
        return clean[-1][:280] if clean else ""
    except Exception:
        return ""


def build_context(queue: str, chats: str) -> str:
    focus = ""
    try:
        fp = Path(REPO) / "core/STATE/COUNCIL_FOCUS.md"
        if fp.exists():
            focus = "\n\nSTANDING FOCUS - weight every proposal toward this (set by James):\n" + fp.read_text().strip()
    except Exception:
        pass

    context = "DECISION QUEUE:\n" + queue + "\n\nRECENT INTENTS (chats):\n" + chats + focus
    if build_blueprint_context and os.environ.get("BLUEPRINTS_DISABLE") != "1":
        try:
            blueprint_context = build_blueprint_context(queue, chats, focus, include_council=True)
            if blueprint_context:
                context = "[Module blueprints - what already exists + quality standards]\n" + blueprint_context + "\n\n" + context
        except Exception:
            pass
    return context


def main() -> int:
    os.makedirs(CFG, exist_ok=True)
    if os.path.exists(CFG + "/.disabled") or os.path.exists(HOME + "/.config/fpai/decisions/.recommend_disabled"):
        print("disabled")
        return 0

    spent, _ = track.today("council")
    if spent >= DAILY_CAP:
        print(f"council daily cap hit (${spent:.2f}/${DAILY_CAP})")
        return 0

    queue = run_curator("./.venv/bin/python -m curator.decisions list")

    if trigger_from_files and run_diagnostic_dialogue and is_decision_queue_empty:
        try:
            diag_decision = trigger_from_files(queue_empty=is_decision_queue_empty(queue))
            if diag_decision.should_run:
                specs = run_diagnostic_dialogue()
                print(f"self-diagnostic ran ({diag_decision.trigger}); queued {len(specs)} improvements")
                return 0
        except Exception as e:
            _ops("diagnostic_error", f"self-diagnostic skipped after error: {e}")
            print("self-diagnostic error; continuing normal debate:", e)

    chats = run_curator("./.venv/bin/python -m curator.decisions recent-chats 30").strip()
    signal = queue + "\n" + chats
    sig_hash = hashlib.sha256(signal.encode()).hexdigest()[:16]
    last = ""
    if os.path.exists(CFG + "/last_hash"):
        last = Path(CFG + "/last_hash").read_text().strip()
    if sig_hash == last:
        print("no new intent since last debate - skip (~$0)")
        return 0

    context = build_context(queue, chats)
    try:
        lenses, model_log = run_lenses(context)
        d = synthesize_debate(lenses, context, model_log)
    except Exception as e:
        print("debate error:", e)
        return 1

    Path(CFG + "/last_hash").write_text(sig_hash)
    total_today, _ = track.today("council")
    print(f"debated via multi-model council. lens models: {json.dumps(d.get('model_log', []), sort_keys=True)}")
    print(f"real metered today: ${total_today:.4f}; GLM council today: ${glm_spend_today():.4f}")

    if not d.get("propose") or len((d.get("build_spec") or "")) < 15:
        _ops("nothing", "council debated, chose to build nothing this round")
        print("council verdict: build nothing this round")
        return 0

    stop = {"with", "that", "this", "from", "into", "build", "system", "fixes", "pipeline", "intent", "the", "and", "for"}
    title_words = {w for w in _re.findall(r"[a-z]{4,}", (d.get("title") or "").lower()) if w not in stop}
    overlap = sum(1 for w in title_words if w in queue.lower())
    if title_words and overlap >= max(2, (len(title_words) + 1) // 2):
        _ops("nothing", f"skipped duplicate - '{d.get('title', '')}' overlaps an existing decision")
        print("council: proposal duplicates an existing/recent decision - skip")
        return 0

    gpt = gpt_voice(signal)
    why = (
        d.get("why", "")
        + "  Council: "
        + (d.get("synthesis", "")[:180])
        + (("  GPT(2nd lab): " + gpt) if gpt else "")
    )
    payload = json.dumps({"title": d["title"], "why": why, "build_spec": d["build_spec"], "risk": d.get("risk", "low")})
    out = run_curator("./.venv/bin/python -m curator.decisions recommend", inp=payload)
    _ops("proposed", d.get("title", ""), "James: approve or veto the proposal")
    print("proposed + surfaced:", out.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
