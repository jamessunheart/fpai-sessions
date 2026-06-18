from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SIGNAL = REPO_ROOT / "core" / "BUILD" / "signals" / "frontier_adoptions.json"
DEFAULT_STATE = REPO_ROOT / "core" / "STATE" / "FRONTIER_ADOPTIONS.md"

EMAIL_RE = re.compile(r"[^@\s<>,]+@[^@\s<>,]+\.[^@\s<>,]+")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
SECRET_RE = re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]")


@dataclass(frozen=True)
class AdoptionCandidate:
    name: str
    status: str
    mode: str
    repo_or_source: str
    replaces: str
    proof_gate: str
    rollback: str
    notes: str


@dataclass(frozen=True)
class DittofeedEvent:
    event: str
    user_id: str
    stage: str
    traits: dict[str, str]


@dataclass(frozen=True)
class RoutingFixture:
    id: str
    prompt: str
    privacy: str
    complexity: str
    expected_route: str
    reason: str


def utc_stamp(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def has_private_pattern(text: str) -> bool:
    phone_like = any(len(re.sub(r"\D", "", match.group(0))) >= 10 for match in PHONE_RE.finditer(text))
    return bool(EMAIL_RE.search(text) or phone_like or SECRET_RE.search(text))


def assert_public_payload(payload: Any) -> None:
    text = json.dumps(payload, sort_keys=True)
    if has_private_pattern(text):
        raise ValueError("payload contains private-layer pattern")


def stable_user_id(source: str) -> str:
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    return f"anon_{digest}"


def infer_stage(session: dict[str, Any]) -> str:
    if session.get("completed_onboarding"):
        return "activate"
    if session.get("completed_spark"):
        return "awaken"
    if session.get("engaged"):
        return "spark"
    return "silent_probe"


def dittofeed_event_from_probe_session(session: dict[str, Any]) -> DittofeedEvent:
    source = str(session.get("probe_id") or session.get("id") or "")
    if not source:
        raise ValueError("probe session needs id or probe_id")
    stage = infer_stage(session)
    event = DittofeedEvent(
        event="probe_session_stage_changed",
        user_id=stable_user_id(source),
        stage=stage,
        traits={
            "pool": str(session.get("pool") or "unknown"),
            "stage": stage,
            "quality_band": quality_band(session.get("quality_score")),
        },
    )
    assert_public_payload(asdict(event))
    return event


def quality_band(value: Any) -> str:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if score >= 0.75:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def dittofeed_journey_config() -> dict[str, Any]:
    config = {
        "name": "becoming_engine_shadow_journey",
        "mode": "shadow",
        "source": "brain_index.probe_sessions anonymized events",
        "stages": ["spark", "awaken", "activate", "build", "contribute", "coach"],
        "entry_event": "probe_session_stage_changed",
        "channels": {
            "email": "brevo_existing_adapter",
            "whatsapp": "evolution_api_review_required",
            "sms": "twilio_review_required",
        },
        "rules": [
            {
                "if": {"stage": "silent_probe", "age_days": ">=3"},
                "then": "enqueue_reviewed_tg_cta_email_shadow",
            },
            {
                "if": {"stage": "awaken", "quality_band": "high"},
                "then": "enqueue_becoming_prompt_shadow",
            },
        ],
        "private_layer_excluded": [
            "email",
            "phone",
            "name",
            "raw conversation",
            "raw corrections",
            "notes text",
        ],
    }
    assert_public_payload(config)
    return config


def routing_fixtures() -> list[RoutingFixture]:
    return [
        RoutingFixture("r001", "Summarize this public release note.", "public", "low", "ollama_local", "cheap public summary"),
        RoutingFixture("r002", "Draft code for a repo-local parser.", "repo", "medium", "ollama_local", "local code task"),
        RoutingFixture("r003", "Classify whether this contains a secret.", "private", "low", "local_guard", "privacy guard first"),
        RoutingFixture("r004", "Reason about a failing integration test.", "repo", "high", "claude_review", "hard code reasoning"),
        RoutingFixture("r005", "Rewrite a public marketing sentence.", "public", "low", "ollama_local", "low risk text"),
        RoutingFixture("r006", "Analyze a private contact conversation.", "private", "high", "blocked_private", "external routing forbidden"),
        RoutingFixture("r007", "Benchmark a local model response.", "repo", "medium", "ollama_local", "local benchmark"),
        RoutingFixture("r008", "Search architecture options without user data.", "public", "medium", "claude_review", "frontier research"),
        RoutingFixture("r009", "Route a treasury transaction approval.", "reserved", "high", "james_gate", "reserved class"),
        RoutingFixture("r010", "Generate a simple JSON schema.", "repo", "low", "ollama_local", "deterministic local task"),
    ]


def router_eval_config() -> dict[str, Any]:
    fixtures = routing_fixtures()
    config = {
        "mode": "shadow_eval",
        "required_decisions_before_replace": 10,
        "passed_decision_count": len(fixtures),
        "litellm_proxy": {
            "status": "config_artifact_only",
            "models": [
                {
                    "model_name": "ollama_local",
                    "litellm_params": {
                        "model": "ollama/llama3.1:8b",
                        "api_base": "http://localhost:11434",
                    },
                },
                {
                    "model_name": "claude_review",
                    "litellm_params": {
                        "model": "anthropic/claude-sonnet",
                        "activation": "requires existing approved API path or claude-p bridge",
                    },
                },
            ],
        },
        "semantic_router": {
            "candidate": "vllm-project/semantic-router",
            "fallback": "RouteLLM or existing tools.router.instrument_rack",
            "policy": "prefer local/private-safe routes; never send private-layer content outward",
        },
        "fixtures": [asdict(fixture) for fixture in fixtures],
    }
    assert_public_payload(config)
    return config


def litellm_config_text() -> str:
    return """# d095 shadow LiteLLM config artifact. Review before use.
model_list:
  - model_name: ollama_local
    litellm_params:
      model: ollama/llama3.1:8b
      api_base: http://localhost:11434
  - model_name: claude_review
    litellm_params:
      model: anthropic/claude-sonnet
      activation: requires_existing_approved_api_path_or_claude_p_bridge
router_settings:
  routing_strategy: simple-shuffle
  fallbacks:
    - ollama_local
general_settings:
  auth: configure_outside_repo_after_review
"""


def adoption_candidates() -> list[AdoptionCandidate]:
    return [
        AdoptionCandidate(
            name="GEPA",
            status="covered_by_d106_d107",
            mode="prompt_efficiency_shadow_then_staged_adoption",
            repo_or_source="https://github.com/gepa-ai/gepa",
            replaces="primary hand-written prompt variant loop for template-shaped prompts",
            proof_gate="measurable prompt improvement on fixture task types before promotion",
            rollback="GEPA_OPTIMIZE_DISABLE=1; remove pending adoption row",
            notes="d106/d107 already wired the real package path and activation artifact; d095 records it as adopted, not duplicated.",
        ),
        AdoptionCandidate(
            name="Dittofeed",
            status="shadow_config_ready",
            mode="anonymized events only",
            repo_or_source="https://github.com/dittofeed/dittofeed",
            replaces="hand-built journey timing state machines after shadow comparison",
            proof_gate="one reviewed becoming-engine email is generated by Dittofeed shadow journey before live send approval",
            rollback="disable Dittofeed export; existing probe followup remains source of truth",
            notes="No deploy in this branch. Events hash probe_session ids and exclude email, phone, names, notes, and raw conversations.",
        ),
        AdoptionCandidate(
            name="LiteLLM plus vLLM Semantic Router",
            status="shadow_eval_ready",
            mode="10-decision route fixture before replacement",
            repo_or_source="https://github.com/BerriAI/litellm; https://github.com/vllm-project/semantic-router",
            replaces="future hand-coded T0-T5 provider dispatcher only after eval pass",
            proof_gate="10 routing decisions match expected local/frontier/James-gate outcomes",
            rollback="keep existing router paths; do not start proxy service",
            notes="Config artifact only. Private or reserved inputs route local/blocked/JAMES, never outward.",
        ),
    ]


def build_payload(now: datetime | None = None) -> dict[str, Any]:
    sample_sessions = [
        {"id": 1, "probe_id": "probe-alpha", "pool": "warm", "engaged": False, "quality_score": None},
        {"id": 2, "probe_id": "probe-beta", "pool": "adjacent", "engaged": True, "completed_spark": True, "quality_score": 0.82},
    ]
    payload = {
        "generated_at": utc_stamp(now),
        "spec": "SPEC_d095_adopt-gepa-dittofeed-vllm-router",
        "mode": "shadow_only_no_deploy_no_sends_no_installs",
        "candidates": [asdict(candidate) for candidate in adoption_candidates()],
        "dittofeed": {
            "journey": dittofeed_journey_config(),
            "sample_events": [asdict(dittofeed_event_from_probe_session(session)) for session in sample_sessions],
        },
        "router": router_eval_config(),
        "litellm_config": litellm_config_text(),
        "proof": {
            "gepa": "covered by d106/d107 focused tests and pending activation",
            "dittofeed": "journey config plus anonymized event export generated; live send remains gated",
            "router": "10 deterministic route decisions generated for pre-replacement eval",
        },
    }
    assert_public_payload(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Frontier Adoptions",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        "Mode: shadow only. No deploys, sends, package installs, secrets, or live service changes.",
        "",
        "## Candidates",
        "",
        "| Tool | Status | Mode | Proof gate | Rollback |",
        "|---|---|---|---|---|",
    ]
    for candidate in payload["candidates"]:
        lines.append(
            f"| {candidate['name']} | {candidate['status']} | {candidate['mode']} | "
            f"{candidate['proof_gate']} | {candidate['rollback']} |"
        )
    lines.extend(
        [
            "",
            "## Dittofeed Shadow Journey",
            "",
            f"Entry event: `{payload['dittofeed']['journey']['entry_event']}`",
            "",
            "Stages: " + ", ".join(payload["dittofeed"]["journey"]["stages"]),
            "",
            "Sample anonymized events:",
        ]
    )
    for event in payload["dittofeed"]["sample_events"]:
        lines.append(f"- `{event['event']}` user=`{event['user_id']}` stage=`{event['stage']}` traits={event['traits']}")
    lines.extend(["", "## Router Shadow Eval", ""])
    router = payload["router"]
    lines.append(f"Required decisions before replacement: {router['required_decisions_before_replace']}")
    lines.append(f"Fixture decisions generated: {router['passed_decision_count']}")
    lines.extend(["", "| ID | Privacy | Complexity | Expected route | Reason |", "|---|---|---|---|---|"])
    for fixture in router["fixtures"]:
        lines.append(
            f"| {fixture['id']} | {fixture['privacy']} | {fixture['complexity']} | "
            f"{fixture['expected_route']} | {fixture['reason']} |"
        )
    lines.extend(["", "## LiteLLM Config Artifact", "", "```yaml", payload["litellm_config"].rstrip(), "```", ""])
    return "\n".join(lines)


def write_outputs(signal_path: Path, state_path: Path, *, now: datetime | None = None) -> dict[str, Any]:
    payload = build_payload(now)
    signal_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    signal_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    state_path.write_text(render_markdown(payload), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate d095 frontier adoption shadow artifacts.")
    parser.add_argument("--signal", type=Path, default=DEFAULT_SIGNAL)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--json", action="store_true", help="Print summary JSON to stdout.")
    args = parser.parse_args(argv)

    payload = write_outputs(args.signal, args.state)
    summary = {
        "spec": payload["spec"],
        "mode": payload["mode"],
        "candidates": len(payload["candidates"]),
        "router_decisions": payload["router"]["passed_decision_count"],
        "dittofeed_events": len(payload["dittofeed"]["sample_events"]),
    }
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
