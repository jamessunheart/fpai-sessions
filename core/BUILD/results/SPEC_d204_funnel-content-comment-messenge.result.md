# SPEC_d204_funnel-content-comment-messenge Result

build_kind=activation

## Files Changed

- `SERVICES/champion-sign/main.py`
- `tools/growth/life_assessment/test_champion_life_lead.py`
- `core/BUILD/activate/SPEC_d204_funnel-content-comment-messenge.sh`
- `core/BUILD/specs/SPEC_d204_funnel-content-comment-messenge.md`
- `core/BUILD/results/SPEC_d204_funnel-content-comment-messenge.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Added a Meta FB/IG comment -> Messenger adapter to `champion-sign` that reuses the existing public assessment chat engine instead of forking the funnel. The webhook verifies Meta subscriptions, parses comment and Messenger events, gates comment triggers through compliance/rate checks, stages a public reply plus comment private reply, persists Messenger chat state, runs the same public Allocation Score conversation, writes the lead to the existing lead store, and keeps CAPI Lead capture on the existing background task path.

Live Graph API writes are inert by default. They require `META_COMMENT_AUTOMATION_ENABLED=1`, `META_PAGE_ACCESS_TOKEN`, and separate approval flags for public replies and Messenger/private replies. Disabled mode returns `would_send` actions and writes `meta_funnel_audit.jsonl`, which supports the requested one-post semi-manual fast test without accidental outreach.

## Tests

- `python3 -B -m unittest tools.growth.life_assessment.test_champion_life_lead` - 9 OK
- `python3 -B -m unittest tools.growth.test_process_leads tools.growth.test_score_assessment tools.growth.life_assessment.test_champion_life_lead tools.leads.test_mail_leads` - 27 OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/champion-sign/main.py tools/growth/life_assessment/test_champion_life_lead.py`
- `bash -n core/BUILD/activate/SPEC_d204_funnel-content-comment-messenge.sh`
- `python3 tools/build_loop/activation_policy.py --repo-root . --spec-id SPEC_d204_funnel-content-comment-messenge --base-ref feat/headless-build --head-ref HEAD`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d204-registry-check.json`
- `git diff --check`

## Risks

- Live Meta permissions, page token, webhook subscription, public reply, private reply, and Messenger send proof were not run in this sandbox.
- Public comment copy remains James-voice/reserved for live activation. The code only sends live replies when explicit approval env flags are present.
- HERMES `brain_index.thread` append is best-effort and disabled unless `HERMES_THREAD_APPEND_ENABLED=1`; lead/audit storage works without DB access.
- Meta policy windows and page-app review still need live validation with the actual page scopes: `pages_messaging` and `pages_manage_engagement`.

## Rollback

Revert this branch. If already activated, restore the previous `SERVICES/champion-sign/main.py` from the live-service guard backup and restart `champion-sign.service`. Runtime mitigation without rollback: leave `META_COMMENT_AUTOMATION_ENABLED=0`, unset `META_PUBLIC_REPLY_APPROVED`, unset `META_DM_REPLY_APPROVED`, or remove `META_PAGE_ACCESS_TOKEN`.

## Intent Solved

The funnel can now convert on-platform conversations: a qualifying FB/IG comment is recognized, a public reply and Messenger prompt are staged, the Messenger thread runs the public assessment chat, the lead is captured in the existing store, and the Allocation Score is delivered in-thread.

## Downstream Intent Unlocked

James/Ember can run the one-off fast test with a single approved offer post: manually or guarded-live reply/DM a commenter, confirm Messenger assessment completion, verify lead file + CAPI attribution, then decide whether to bless full automation.
