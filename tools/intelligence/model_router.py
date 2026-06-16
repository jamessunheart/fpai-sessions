#!/usr/bin/env python3
"""Tiered model router for autonomous AI calls.

T0: flat-rate subscription CLIs. T1: local Ollama. T2: metered APIs behind the
daily cost cap. T3: explicit outage flag + Telegram alert, never silent failure.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
ROUTING_FILE = Path(__file__).with_name("routing.yaml")
OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
FALLBACK_ENV = Path(os.environ.get("MODEL_FALLBACK_ENV", "~/.config/fpai/model_fallback.env")).expanduser()
OUTAGE_FLAG = Path(os.environ.get("MODEL_OUTAGE_FLAG", "/opt/fpai-build/.model_outage"))
OUTAGE_ALERT = Path(os.environ.get("MODEL_OUTAGE_ALERT", "/opt/fpai-build/.model_outage_alerted"))
DEGRADED_SUMMARY = Path(os.environ.get("MODEL_DEGRADED_SUMMARY", "/opt/fpai-build/.model_degraded_summary_date"))
OLLAMA_MODEL = os.environ.get("MODEL_ROUTER_OLLAMA_MODEL", "llama3.1:8b")
CLI_TIMEOUT = int(os.environ.get("MODEL_ROUTER_CLI_TIMEOUT", "30"))
API_TIMEOUT = int(os.environ.get("MODEL_ROUTER_API_TIMEOUT", "45"))
AUTH_ERROR_STRINGS = ("invalid bearer", "not logged in", "401", "unauthor", "rate limit", "authentication")
T2_RATES = {
    "anthropic-api": {"model": "claude-3-5-sonnet-latest", "in": 3.0, "out": 15.0},
    "openai-api": {"model": "gpt-4.1-mini", "in": 0.4, "out": 1.6},
    "gemini-api": {"model": "gemini-1.5-flash", "in": 0.35, "out": 1.05},
}


@dataclass
class ProviderFailure(Exception):
    provider: str
    tier: int
    reason: str

    def __str__(self) -> str:
        return f"{self.provider} T{self.tier}: {self.reason}"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def provider_tier(provider: str) -> int:
    if provider in {"claude", "codex"}:
        return 0
    if provider == "ollama":
        return 1
    if provider.endswith("-api"):
        return 2
    return 3


def load_routing(path: Path = ROUTING_FILE) -> dict[str, list[str]]:
    routing: dict[str, list[str]] = {}
    current: str | None = None
    if not path.exists():
        return {"synthesis": ["claude", "ollama", "openai-api", "anthropic-api", "gemini-api"]}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith(":") and not line.startswith("-"):
            current = line[:-1].strip()
            routing[current] = []
            continue
        if current and line.startswith("-"):
            routing[current].append(line[1:].strip())
    return routing


def route_for(task_type: str, tier_floor: int = 0) -> list[str]:
    routing = load_routing()
    providers = routing.get(task_type) or routing.get("synthesis") or ["claude", "ollama", "openai-api"]
    return [provider for provider in providers if provider_tier(provider) >= tier_floor]


def _append_ops(loop: str, event: str, detail: str, cost: str = "$0", artifact: str = "", next_action: str = "") -> None:
    row = {
        "ts": now_iso(),
        "loop": loop,
        "event": event,
        "detail": detail,
        "cost": cost,
        "artifact": artifact,
        "next": next_action,
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
    }
    try:
        OPS_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with OPS_LEDGER.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
    except Exception:
        pass


def log_fallback(from_tier: int, to_tier: int, reason: str) -> None:
    _append_ops("model-router", "model_fallback", f"from_tier={from_tier} to_tier={to_tier} reason={reason}")


def log_restored(provider: str) -> None:
    _append_ops("model-router", "model_restored", f"provider={provider}", next_action="Primary model back online")
    _send_tg("Primary model back online")


def _send_tg(message: str) -> None:
    script = REPO / "tools" / "build_loop" / "notify_telegram.sh"
    if not script.exists():
        return
    try:
        subprocess.run(["bash", str(script), message], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
    except Exception:
        pass


def _send_daily_degraded_summary(task_type: str, provider: str) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    try:
        if DEGRADED_SUMMARY.exists() and DEGRADED_SUMMARY.read_text(encoding="utf-8").strip() == today:
            return
        _send_tg(f"Model router degraded: T0 failed; continuing on {provider} for {task_type}.")
        DEGRADED_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        DEGRADED_SUMMARY.write_text(today + "\n", encoding="utf-8")
    except Exception:
        pass


def _mark_outage(reason: str) -> None:
    try:
        OUTAGE_FLAG.parent.mkdir(parents=True, exist_ok=True)
        OUTAGE_FLAG.write_text(f"{now_iso()} {reason}\n", encoding="utf-8")
        if not OUTAGE_ALERT.exists():
            _send_tg("All model providers unreachable. Build loop paused. Will auto-resume.")
            OUTAGE_ALERT.write_text(now_iso() + "\n", encoding="utf-8")
    except Exception:
        pass
    _append_ops("model-router", "model_outage", reason, next_action="pause build loop until any model provider responds")


def clear_outage_if_needed(provider: str) -> None:
    if OUTAGE_FLAG.exists():
        try:
            OUTAGE_FLAG.unlink()
        except Exception:
            pass
        try:
            OUTAGE_ALERT.unlink()
        except Exception:
            pass
        log_restored(provider)


def _has_auth_error(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in AUTH_ERROR_STRINGS)


def _run_cli(provider: str, cmd: list[str], *, prompt: str, input_stdin: bool = False, timeout: int = CLI_TIMEOUT) -> str:
    started = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            input=prompt if input_stdin else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProviderFailure(provider, provider_tier(provider), f"timeout after {timeout}s") from exc
    combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
    if result.returncode != 0:
        reason = combined.strip()[:500] or f"exit {result.returncode}"
        raise ProviderFailure(provider, provider_tier(provider), reason)
    if _has_auth_error(combined):
        raise ProviderFailure(provider, provider_tier(provider), combined.strip()[:500])
    if not result.stdout.strip():
        raise ProviderFailure(provider, provider_tier(provider), "empty response")
    _ = started
    return result.stdout


def _call_claude(prompt: str) -> str:
    claude = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude")
    if not Path(claude).exists() and not shutil.which("claude"):
        raise ProviderFailure("claude", 0, "claude CLI not found")
    return _run_cli("claude", [claude, "-p", prompt], prompt=prompt, input_stdin=False)


def _call_codex(prompt: str) -> str:
    codex = shutil.which("codex") or str(Path.home() / ".local" / "bin" / "codex")
    if not Path(codex).exists() and not shutil.which("codex"):
        raise ProviderFailure("codex", 0, "codex CLI not found")
    return _run_cli(
        "codex",
        [codex, "exec", "--cd", str(REPO), "--sandbox", "read-only", "--skip-git-repo-check", "-"],
        prompt=prompt,
        input_stdin=True,
    )


def _ollama_tags() -> set[str]:
    try:
        result = subprocess.run(
            ["curl", "-sS", "--max-time", "5", "http://localhost:11434/api/tags"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=8,
        )
    except Exception:
        return set()
    if result.returncode != 0:
        return set()
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return set()
    return {str(model.get("name", "")) for model in data.get("models", []) if isinstance(model, dict)}


def _ensure_ollama_model(model: str) -> None:
    if os.environ.get("MODEL_ROUTER_SKIP_OLLAMA_PULL") == "1":
        return
    tags = _ollama_tags()
    if model in tags:
        return
    try:
        subprocess.run(["ollama", "pull", model], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=240)
    except Exception:
        pass


def _call_ollama(prompt: str) -> str:
    if not shutil.which("ollama"):
        raise ProviderFailure("ollama", 1, "ollama CLI not found")
    _ensure_ollama_model(OLLAMA_MODEL)
    return _run_cli("ollama", ["ollama", "run", OLLAMA_MODEL, prompt], prompt=prompt, input_stdin=False, timeout=max(CLI_TIMEOUT, 60))


def _load_env(path: Path = FALLBACK_ENV) -> dict[str, str]:
    env = dict(os.environ)
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = shlex.split(value.strip())[0] if value.strip() else ""
    return env


def _estimate_tokens(prompt: str, response: str = "") -> tuple[int, int]:
    return max(1, len(prompt) // 4), max(1, max(len(response), 800) // 4)


def _estimate_cost(provider: str, in_tokens: int, out_tokens: int) -> float:
    rate = T2_RATES.get(provider, T2_RATES["openai-api"])
    return round(in_tokens / 1_000_000 * rate["in"] + out_tokens / 1_000_000 * rate["out"], 6)


def _remaining_cap() -> float:
    try:
        sys.path.insert(0, str(REPO / "tools" / "cost"))
        import track  # type: ignore

        total, _ = track.today()
        return max(0.0, float(track.cap()) - float(total))
    except Exception:
        return 20.0


def _log_metered_cost(label: str, provider: str, in_tokens: int, out_tokens: int) -> float:
    model = T2_RATES.get(provider, {}).get("model", provider)
    try:
        sys.path.insert(0, str(REPO / "tools" / "cost"))
        import track  # type: ignore

        return float(track.log(label, model, in_tokens, out_tokens))
    except Exception:
        return _estimate_cost(provider, in_tokens, out_tokens)


def _json_post(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body[:300]}") from exc


def _call_api(provider: str, prompt: str) -> tuple[str, int, int, float]:
    env = _load_env()
    in_tokens, out_tokens = _estimate_tokens(prompt)
    estimated = _estimate_cost(provider, in_tokens, out_tokens)
    if estimated > _remaining_cap():
        raise ProviderFailure(provider, 2, f"daily metered cap would be exceeded by estimated ${estimated:.4f}")

    if provider == "anthropic-api":
        key = env.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise ProviderFailure(provider, 2, "ANTHROPIC_API_KEY missing")
        data = _json_post(
            "https://api.anthropic.com/v1/messages",
            {"model": T2_RATES[provider]["model"], "max_tokens": 1200, "messages": [{"role": "user", "content": prompt}]},
            {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        )
        text = "\n".join(part.get("text", "") for part in data.get("content", []) if isinstance(part, dict)).strip()
        usage = data.get("usage", {})
        in_tokens = int(usage.get("input_tokens", in_tokens))
        out_tokens = int(usage.get("output_tokens", out_tokens))
    elif provider == "openai-api":
        key = env.get("OPENAI_API_KEY", "")
        if not key:
            raise ProviderFailure(provider, 2, "OPENAI_API_KEY missing")
        data = _json_post(
            "https://api.openai.com/v1/chat/completions",
            {"model": T2_RATES[provider]["model"], "messages": [{"role": "user", "content": prompt}], "max_tokens": 1200},
            {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        text = data["choices"][0]["message"]["content"].strip()
        usage = data.get("usage", {})
        in_tokens = int(usage.get("prompt_tokens", in_tokens))
        out_tokens = int(usage.get("completion_tokens", out_tokens))
    elif provider == "gemini-api":
        key = env.get("GEMINI_API_KEY", "")
        if not key:
            raise ProviderFailure(provider, 2, "GEMINI_API_KEY missing")
        model = T2_RATES[provider]["model"]
        data = _json_post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
            {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 1200}},
            {"Content-Type": "application/json"},
        )
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    else:
        raise ProviderFailure(provider, 2, "unknown API provider")

    cost = _log_metered_cost(f"model-router:{provider}", provider, in_tokens, out_tokens)
    return text, in_tokens, out_tokens, cost


def _call_provider(provider: str, prompt: str) -> tuple[str, float]:
    if provider == "claude":
        return _call_claude(prompt), 0.0
    if provider == "codex":
        return _call_codex(prompt), 0.0
    if provider == "ollama":
        return _call_ollama(prompt), 0.0
    if provider.endswith("-api"):
        text, _in_tokens, _out_tokens, cost = _call_api(provider, prompt)
        return text, cost
    raise ProviderFailure(provider, provider_tier(provider), "unknown provider")


def call_model(prompt: str, task_type: str, tier_floor: int = 0) -> dict[str, Any]:
    """Call the best available model for a task, falling through configured tiers."""
    if os.environ.get("MODEL_ROUTER_DISABLE") == "1":
        started = time.monotonic()
        response = _call_claude(prompt)
        latency = int((time.monotonic() - started) * 1000)
        return {"response": response, "provider": "claude", "tier": 0, "latency_ms": latency, "cost_estimate": 0.0}

    failures: list[ProviderFailure] = []
    last_tier: int | None = None
    for provider in route_for(task_type, tier_floor=tier_floor):
        tier = provider_tier(provider)
        if last_tier is not None and tier > last_tier:
            log_fallback(last_tier, tier, "; ".join(f"{f.provider}: {f.reason}" for f in failures[-3:]))
        last_tier = tier
        started = time.monotonic()
        try:
            response, cost = _call_provider(provider, prompt)
        except ProviderFailure as exc:
            failures.append(exc)
            continue
        except Exception as exc:
            failures.append(ProviderFailure(provider, tier, str(exc)))
            continue
        latency = int((time.monotonic() - started) * 1000)
        clear_outage_if_needed(provider)
        if tier == 1 and any(f.tier == 0 for f in failures):
            _append_ops("model-router", "model_degraded", f"task_type={task_type} provider=ollama after T0 failure", "$0")
            _send_daily_degraded_summary(task_type, provider)
        _append_ops("model-router", "model_call", f"task_type={task_type} provider={provider} tier={tier}", f"${cost:.6f}")
        return {"response": response, "provider": provider, "tier": tier, "latency_ms": latency, "cost_estimate": float(cost)}

    reason = "; ".join(str(f) for f in failures) or "no providers configured"
    _mark_outage(reason)
    raise RuntimeError(f"all model providers failed: {reason}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-type", default="synthesis")
    parser.add_argument("--tier-floor", type=int, default=0)
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("prompt", nargs="*")
    args = parser.parse_args(argv)
    prompt = args.prompt_file.read_text(encoding="utf-8") if args.prompt_file else " ".join(args.prompt)
    result = call_model(prompt, args.task_type, tier_floor=args.tier_floor)
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(result["response"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
