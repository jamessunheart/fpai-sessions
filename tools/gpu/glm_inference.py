#!/usr/bin/env python3
"""OpenAI-compatible GLM inference through RunPod serverless."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any, Callable
import urllib.error
import urllib.request

from tools.gpu import budget_guard


DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))


class GLMInferenceError(RuntimeError):
    """Raised when RunPod GLM inference fails before fallback."""


def _messages_to_prompt(messages: list[dict[str, str]]) -> str:
    parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        parts.append(f"{role.upper()}: {content}")
    return "\n\n".join(parts)


def call_claude_fallback(
    messages: list[dict[str, str]],
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> str:
    claude = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
    prompt = _messages_to_prompt(messages)
    run = runner or subprocess.run
    result = run(
        [claude, "-p", "--effort", "medium", prompt],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise GLMInferenceError(result.stderr.strip() or f"claude exited {result.returncode}")
    return result.stdout.strip()


def _post_json(url: str, payload: dict[str, Any], api_key: str, timeout: int) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_text(payload: dict[str, Any]) -> str:
    output = payload.get("output", payload)
    if isinstance(output, dict):
        choices = output.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message") or {}
            if message.get("content"):
                return str(message["content"])
            if choices[0].get("text"):
                return str(choices[0]["text"])
        for key in ("text", "content", "response", "output"):
            if output.get(key):
                return str(output[key])
    if isinstance(output, str):
        return output
    raise GLMInferenceError("RunPod response did not include OpenAI-compatible text")


def _gpu_seconds(payload: dict[str, Any], elapsed: float) -> float:
    for container in (payload, payload.get("output") if isinstance(payload.get("output"), dict) else {}):
        if not isinstance(container, dict):
            continue
        for key in ("gpu_seconds", "gpuSeconds", "executionTime", "execution_time", "delayTime"):
            value = container.get(key)
            if isinstance(value, (int, float)):
                return float(value)
    return elapsed


def log_inference(
    *,
    endpoint_id: str,
    status: str,
    gpu_seconds: float = 0.0,
    reason: str = "",
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
) -> None:
    row = {
        "ts": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "loop": "glm_runpod",
        "event": status,
        "endpoint_id": endpoint_id,
        "gpu_seconds": round(float(gpu_seconds), 3),
        "detail": reason,
        "cost": "runpod-metered",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
    }
    try:
        ops_ledger.parent.mkdir(parents=True, exist_ok=True)
        with ops_ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    except Exception:
        pass


def call_runpod(
    messages: list[dict[str, str]],
    *,
    endpoint_id: str,
    api_key: str,
    max_tokens: int,
    temperature: float,
    timeout: int,
    poster: Callable[[str, dict[str, Any], str, int], dict[str, Any]] | None = None,
) -> tuple[str, dict[str, Any], float]:
    url = f"https://api.runpod.ai/v2/{endpoint_id}/runsync"
    payload = {
        "input": {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
    }
    started = time.monotonic()
    data = (poster or _post_json)(url, payload, api_key, timeout)
    elapsed = time.monotonic() - started
    return _extract_text(data), data, elapsed


def call_glm(
    messages: list[dict[str, str]],
    max_tokens: int = 1000,
    temperature: float = 0.7,
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    retries: int = 1,
    endpoint_id: str | None = None,
    api_key: str | None = None,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    fallback_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    poster: Callable[[str, dict[str, Any], str, int], dict[str, Any]] | None = None,
    budget_checker: Callable[[], budget_guard.BudgetDecision] | None = None,
) -> str:
    endpoint = endpoint_id or os.environ.get("RUNPOD_GLM_ENDPOINT_ID", "")
    key = api_key or os.environ.get("RUNPOD_API_KEY", "")
    if os.environ.get("RUNPOD_GLM_DISABLE") == "1":
        return call_claude_fallback(messages, timeout=timeout, runner=fallback_runner)
    if not endpoint or not key:
        return call_claude_fallback(messages, timeout=timeout, runner=fallback_runner)
    budget = budget_checker() if budget_checker else budget_guard.check_budget(api_key=key)
    if not budget.allowed:
        budget_guard.log_budget_alert(budget, ops_ledger=ops_ledger)
        log_inference(endpoint_id=endpoint, status="skipped", reason=budget.reason, ops_ledger=ops_ledger)
        return call_claude_fallback(messages, timeout=timeout, runner=fallback_runner)

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            text, payload, elapsed = call_runpod(
                messages,
                endpoint_id=endpoint,
                api_key=key,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
                poster=poster,
            )
            log_inference(
                endpoint_id=endpoint,
                status="succeeded",
                gpu_seconds=_gpu_seconds(payload, elapsed),
                ops_ledger=ops_ledger,
            )
            return text
        except (TimeoutError, urllib.error.URLError, GLMInferenceError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < retries:
                continue
    log_inference(endpoint_id=endpoint, status="failed", reason=str(last_error), ops_ledger=ops_ledger)
    return call_claude_fallback(messages, timeout=timeout, runner=fallback_runner)
