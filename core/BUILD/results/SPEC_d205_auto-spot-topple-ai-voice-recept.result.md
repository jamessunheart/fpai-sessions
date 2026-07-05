# SPEC_d205_auto-spot-topple-ai-voice-recept Result

build_kind=library

## Files Changed

- `tools/growth/voice_receptionist.py`
- `tools/growth/test_voice_receptionist.py`
- `core/BUILD/specs/SPEC_d205_auto-spot-topple-ai-voice-recept.md`
- `core/BUILD/results/SPEC_d205_voice_call.fixture.json`
- `core/BUILD/results/SPEC_d205_voice_call.expected_payload.json`
- `core/BUILD/results/SPEC_d205_capability_created.fixture.jsonl`
- `core/BUILD/results/SPEC_d205_auto-spot-topple-ai-voice-recept.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Built a sandbox-only AI Voice Receptionist intake proof for `ai-voice-receptionist`. The proof reads a transcript fixture, extracts caller/contact/business/service/time/fallback/problem fields, and emits a review-ready appointment payload. It explicitly records `live_phone_number_touched=false`, `live_send_performed=false`, `calendar_write_performed=false`, and `marginal_cost_usd=0`.

The payload status is `requires_human_review`, not booked. No live phone number, calendar, SMS, outreach send, deployment, secret, or metered API path is wired.

## Proof

- Fixture: `core/BUILD/results/SPEC_d205_voice_call.fixture.json`
- Expected payload: `core/BUILD/results/SPEC_d205_voice_call.expected_payload.json`
- Capability learning fixture: `core/BUILD/results/SPEC_d205_capability_created.fixture.jsonl`

The fixture call produces the expected appointment payload and a machine-readable rollback path. The d185-style capability row is written only as a build-result fixture ledger, not to the live capability ledger.

## Tests

- `python3 -B -m unittest tools.growth.test_voice_receptionist` - 4 OK
- `python3 -B -m unittest tools.growth.test_voice_receptionist tools.allocation.test_capability_ledger tools.allocation.test_opportunity_engine` - 15 OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/growth/voice_receptionist.py tools/growth/test_voice_receptionist.py`
- `python3 tools/growth/voice_receptionist.py --fixture core/BUILD/results/SPEC_d205_voice_call.fixture.json --output /tmp/d205-voice-payload.json --capability-ledger /tmp/d205-capability-ledger.jsonl && cmp /tmp/d205-voice-payload.json core/BUILD/results/SPEC_d205_voice_call.expected_payload.json`
- `python3 tools/build_loop/activation_policy.py --repo-root . --spec-id SPEC_d205_auto-spot-topple-ai-voice-recept --base-ref feat/headless-build --head-ref HEAD`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d205-registry-check.json`
- `python3 -m json.tool core/BUILD/results/SPEC_d205_voice_call.fixture.json >/tmp/d205-fixture-check.json`
- `python3 -m json.tool core/BUILD/results/SPEC_d205_voice_call.expected_payload.json >/tmp/d205-payload-check.json`
- `git diff --check`

## Risks

- This is transcript-fixture proof only; it does not validate STT, TTS, telephony latency, no-answer behavior, calendar availability, or live caller consent.
- Regex extraction is intentionally narrow for the first proof. It is suitable for a controlled fixture, not arbitrary live callers.
- The capability-created row is defensible for sandbox learning only; it does not count market proof, cash flow, or a toppled live domino.

## Rollback

Revert this branch. Runtime rollback is also inert: delete generated appointment/capability result artifacts and keep telephony, SMS, calendar, and live-number adapters disconnected. No service was activated.

## Intent Solved

The AI Voice Receptionist opportunity now has a bounded first proof: one fixture call can become a structured appointment-intake payload with a rollback path before any live phone number is touched.

## Downstream Intent Unlocked

James/Ember can decide whether to bless a separate live-call sandbox activation spec that wires a test number through d182/d188 guarded activation, with this payload contract as the acceptance target.
