# SPEC_d160_spec-url-first-assessment-intake Result

Status: done in working tree / awaiting independent review + merge

## Summary

Implemented URL-first Assessment intake across the repo-local funnel:

- `tools/growth/score_assessment.py` now accepts `--url`, fetches public home/about/pricing/services pages, respects robots.txt, skips login-walled/non-HTML pages, bounds reads with timeouts, caches by domain, summarizes business type/tools/team/pricing/ops hints, and appends that as pre-filled intake context before scoring.
- `SERVICES/champion-sign/main.py` exposes `/lead/first-read`, a bounded same-origin endpoint for the assessment page to request the public-site first read without changing the lead-submit contract.
- `sites/fullpotential-com/audit.html` adds the "Your website (optional but magic)" field, shows an "Our first read" panel, calls the first-read endpoint, falls back to a local URL hint if unavailable, and submits the URL/first-read inside the existing bottleneck field.
- `tools/growth/test_score_assessment.py` covers URL normalization, robots skipping, public-page extraction, pre-fill context, and per-domain cache behavior.

## Tests

- `python3 -B -m unittest tools.growth.test_score_assessment` (3 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/growth/score_assessment.py tools/growth/test_score_assessment.py SERVICES/champion-sign/main.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d160-registry.json`
- Champion service smoke import with all data dirs redirected to `/tmp`, asserting `/lead/first-read` and `/lead/submit` routes are registered.
- `git diff --check`

## Risks

- A live real-business URL was not fetched from the public internet in this sandbox. The network path is covered with fake fetchers and a harmless CLI smoke on an unreachable test domain.
- The first-read endpoint depends on the live champion service deploy/restart path after merge; until then, the page still falls back to local first-read copy and preserves the website in the submitted lead.
- The summary is conservative when public pages are thin, blocked by robots, or unreachable.

## Rollback

Revert this branch to remove the scorer URL helpers/tests, `/lead/first-read` endpoint, assessment form field/panel, result artifact, registry entry, and handoff note.

## Intent solved

d160 turns the Assessment from a blank typing-first intake into a URL-first flow that can read public website context and pre-fill the scoring engine.

## Downstream intent unlocked

Real assessment leads can receive a faster first read and the scorer can generate Allocation Scores from confirmed/corrected website-derived context instead of starting from manual free text only.
