# AI Review — build/SPEC_d091_resource-inventory-system-knows

**Verdict:** APPROVE · **Risk:** low

**Summary:** Side-effect-free local resource scanner + names-only inventory file + safe council prompt-load patch; no money/prod/identity/secrets/main touched, secret-name filtering is double-gated and test-proven, matches spec scope.

## Findings
- Prompt bloat / self-defeating: _resources_text() injects the ENTIRE 1345-line AVAILABLE_RESOURCES.md into every council debate prompt, ~1000 lines of which are redundant `backups/aria-command/...` duplicated trees. Even at $0 flat-rate (claude -p), this buries the useful CLIs/APIs/libs under noise and dilutes signal — add `backups` to SKIP_DIRS and/or inject only the CLIs/Python-libs/Configured-APIs sections (not Local-scripts) into the prompt.
- Local-scripts hit the limit=1000 truncation inside the alphabetical `backups/` noise, so real /opt/fpai scripts sorted after it are silently omitted — inventory completeness is weaker than it appears; excluding backups fixes both this and the bloat.
- Env var NAMES (e.g. BRAIN_INDEX_DB_URL, TWILIO_ACCOUNT_SID) are committed to the repo — values are never written and names-only was the explicit spec ask, so acceptable, but note this is architecture disclosure if the repo ever goes public.
- pkg_resources is deprecated (emits DeprecationWarning); functional but consider importlib.metadata for longevity — non-blocking.
- Timer/service artifacts are committed but NOT installed (per result.md); when Ember installs on server 162, confirm it runs as a non-privileged user and only writes the repo file.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
