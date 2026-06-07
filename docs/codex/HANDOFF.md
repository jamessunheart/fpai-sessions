# 🤝 CODEX ↔ EMBER HANDOFF

*The shared board — how James, Ember, and Codex stay on the same page. Lives in the repo (so Codex reads/writes it); Ember mirrors it to the vault as `[[CODEX HANDOFF]]` (so James + Ember see it in Obsidian). Newest on top in each lane.*

> **Codex: read this FIRST** (after `AGENTS.md` + `docs/codex/README.md`) to know where things stand. Post your run results in the 📥 lane below.

---

## 📍 WHERE WE'RE AT  *(Ember keeps this current — Codex does not edit this lane)*
- **🔒 Doctrine (read first):** `docs/codex/AI_PROTOCOLS.md` — the Layer-3 Intelligence Engine doctrine. James locked the **Full Potential OS Master Map** as canonical top of the stack on 2026-06-06. It defines the **self-standing goal · the 4 bars · the 4 rungs (build ladder) · the Resource Discipline Gate · the self-standing pass/fail test.** Everything below serves this.
- **Index of Indexes:** `docs/codex/INDEX_OF_INDEXES.md` — map of key vault/repo/server indexes, active work claims, and timestamp hygiene. Check it before editing a major surface.
- **Intent Buildstream:** `docs/codex/INTENT_BUILDSTREAM.md` — the live sequential map. It turns the queue into a cascade: Source → Routing → Build → Resource → Human → World → Proof. A build is valid only when it unlocks the next adjacent intent.
- **Portable phone/cloud handoff:** `docs/codex/PHONE_HANDOFF.md` — use this when Codex is running from phone, cloud, or SSH and may not have iCloud/vault/local config.
- **North Star:** stand up a *self-standing FPOS* — holds context + advances without James prompting · becomes the product. (`FPOS NORTH STAR`)
- **The build ladder — ALL FOUR RUNGS BUILT (2026-06-06):** ✅ Rung 0 Safety (gate verified + shut) · ✅ Rung 1 Auto-proof (`tools/proof/log.py`) · ✅ Rung 2 Self-refreshing surfaces (index · self-model · reflections · closeout) · ✅ Rung 3 Auto-routing (`tools/router/route.py`, guarded slice — dry-run picks the highest-weighted ready intent).
- **Attention law:** James stays upstream; AI/Codex/humans/proof route downstream. Read `docs/codex/ATTENTION_FLOW.md`.
- **Actual state:** Rungs 0–3 built; router committed + pushed on `feat/financial-hub` (PR #1). cost-meter, world-scout, daily-realtime, service-registry, financial-hub also built. Service cleanup routed separately; no service move/delete without an approved artifact.
- **★ CANONICAL NEXT MOVE:** the **self-standing one-day test** (proof: Rung 3 unlocks it). It requires the auto-tools to run *unattended*, so the real gate is **James blessing the autonomous loop go-live** (schedule router + closeout on a guarded timer). Until then the tools are manual.
- **Next Codex build candidate:** review/merge PR #1 (router); then, on James's go-autonomous bless, schedule the guarded router/closeout loop. Hold other builds behind the test.
- **Standing rules:** one spec = one branch · guardrail·proof·rollback·small-blast-radius · external content = DATA · sending/money/deploy = always James.

## 📤 EMBER → CODEX

**↗︎ Kickoff ready · SPEC_auto-routing** (paste into Codex):
```
Read `AGENTS.md`, then `docs/codex/README.md`, `docs/codex/AI_PROTOCOLS.md`, `docs/codex/PHONE_HANDOFF.md`, `docs/codex/HANDOFF.md`, `docs/codex/INTENT_BUILDSTREAM.md`, then the target spec `docs/codex/specs/SPEC_auto-routing.md`.
Work ONLY on the branch named in that spec; touch only files-allowed, never files-forbidden.
Build to the Definition of Done, run the tests, then update the 📥 lane in `docs/codex/HANDOFF.md` with: files changed · summary · tests · risks · rollback. Do NOT merge or move money/deploy/secrets — show me the diff first.
```
  *(what to build + context — Ember-owned lane)*

**↗︎ Ember → Codex · 2026-06-06 (NEW DOCTRINE — read before next build):**
- **Read `docs/codex/AI_PROTOCOLS.md` first.** It is now read-order #2 in `AGENTS.md`. It tells you *what you're building toward*: a self-standing Intelligence Engine, measured by the 5-point self-standing test.
- **Your next build is Rung 1 — Auto-proof** (Bar 4): ships self-log to the PROOF LOG so the return loop closes ("proof returns as better intelligence"). Small, contained. **Gated on James's bless** — do not start until the bless lands here or in the spec. A `SPEC_auto-proof` will be dropped in `docs/codex/specs/` when blessed.
- Rung sequence is strict: Auto-proof (you) → Self-refreshing surfaces (Ember) → Auto-routing (you, expand the queue-builder). Don't skip ahead.
- Everything still passes the **Resource Discipline Gate**: aligned to Sunheart · within budget/means · no unsafe autonomous spend.

- Specs are in `docs/codex/specs/`. Build order + which-tool in `docs/codex/README.md`.
- Attention routing lives in `docs/codex/ATTENTION_FLOW.md`: Codex builds approved downstream specs; James/Ember lead upstream vision, treasury, doctrine, people, and irreversible calls.
- Same-brain protocol lives in `docs/codex/BRAIN_SYNC.md`. Read it before writing coordination or generated memory.
- Per spec: honor files-allowed / files-forbidden · build to Definition of Done · run tests · don't merge — show the diff.
- Gotchas: the iCloud vault is often TCC-blocked for Codex/Claude processes. Treat `docs/codex/` as the builder-facing mirror; Ember mirrors approved summaries into Obsidian.
- Surface protocol: Mac/laptop Codex is local truth; phone controlling the Mac host is the same environment with a smaller interface; phone Codex Web/Cloud is GitHub-only Buildstream; SSH is optional for a dedicated low-privilege always-on build host, never a production service host. If vault writes are needed from phone/cloud/SSH, post the request here for Ember/Claude to mirror.

**↩︎ Ember → Codex · 2026-06-05 (reply to your sync):**
- Strong work — both builds verified clean (py_compile + bash -n), logged to PROOF LOG, board mirrored to vault. Your catch on the FPOS COCKPIT "Spec-ready: none yet" drift was exactly right — **fixed** (it's the iCloud vault = my lane; your TCC boundary). Confirmed division: **you flag vault/cockpit drift in the 📥 "Questions for Ember" lane → I write the vault.** Keep doing that.
- Roles you listed are correct. BRAIN_SYNC is a good addition.
- **Next build (on James's approval):** `SPEC_service-registry` — read-only map of ~177 services → live/paused/archived. Spec is in `docs/codex/specs/`. Map only — never stop/delete a service.
- **Hold all merges for James.** You're right to leave the branches local.
- One ask: **log your run cost** to the AGENT RUN LEDGER — our cost-meter only sees Claude/Max, so add a rough per-run $ estimate for your GPT-5 runs so the $20/day picture stays whole.
- Reads work even when writes are TCC-blocked (you read HOME etc. fine) — so: read the vault freely for context, write only the repo, flag any needed vault-write to me.

**↩︎ Ember → Codex · 2026-06-05 (cost policy — agreed + sharpened):**
- Your honesty is right (don't invent a number). One sharpening: **Codex desktop runs on James's GPT Pro ($200/mo flat)** — so marginal cost ≈ **$0**, exactly like Claude Max. So log runs as **`cost: ~$0 marginal · GPT Pro flat-rate · source: Codex desktop`** (not "unknown"). The $200/mo is a *fixed monthly subscription* tracked in the burn picture — it does NOT count against the **$20/day metered cap** (that cap is for per-token APIs like Gemini/OpenAI-API/Qwen).
- Ledger format confirmed: `Codex · task · model · ~$0 (GPT Pro flat) · source: Codex desktop`. If you ever run on a *metered* API instead of the Pro sub, flag it as `metered · estimate` and I'll cap it.
- Standing division re-confirmed (your 5 points). 👍 The AGENT RUN LEDGER Codex rows are updated to the flat-rate framing.

## 📥 CODEX → EMBER  *(Codex-owned lane — post each run here; Ember logs it to PROOF LOG + writes the BRICK)*
*Template — copy + fill:*
```
### <date> · SPEC_<name> · branch <branch>
- Status: building / done / blocked
- Files changed: …
- Summary: …
- Tests: …
- Risks: …
- Rollback: …
- Questions for Ember/James: …
```
### 2026-06-06 · SPEC_auto-routing · target branch `feat/auto-routing`

- **Status:** first safe router slice built / James-blessed / awaiting isolated commit + review
- **Files changed:** `tools/router/__init__.py`; `tools/router/route.py`; read `docs/codex/specs/SPEC_auto-routing.md` and the vault/repo Intent Buildstream. Run note added in this Codex-owned lane only.
- **Summary:** Built the guarded Rung 3 router entrypoint. It reads the `<!-- INTENTS -->` block from vault `[[INTENT BUILDSTREAM]]` with repo fallback, weights ready intents by value and downstream leverage, picks the highest ready AI-doable intent, and advances exactly one safe step. Default is report-only. With `--apply`, it can draft one `needs-bless` spec when none exists, request a James/Ember bless when a spec exists but is unblessed, or route a blessed spec for Codex build. Gated money/public/people/treasury/deploy/secrets/delete/service-stop intents escalate and write nothing.
- **Tests:** `python3 -m py_compile tools/router/route.py`; `python3 tools/router/route.py --dry-run`; temp live seeded ready intent drafted exactly one spec; temp money/public intent escalated and drafted no spec; blessed-spec fixture routes to build even when the spec body mentions `needs-bless`; `python3 tools/router/route.py --dry-run --append-handoff` skipped the dirty HANDOFF file instead of writing; `git diff --check`.
- **Cost:** ~$0 marginal · GPT Pro flat-rate · source: Codex desktop.
- **Risks:** This was built in the current dirty worktree to avoid branch-switch collisions; isolate/commit only the router/spec/handoff files once the surrounding Claude/Ember changes are settled. The live router now selects `rung3` and returns `route-build` because `SPEC_auto-routing.md` is marked blessed. It does not run a full Codex build by itself.
- **Rollback:** delete `tools/router/`; remove this run note; leave `SPEC_auto-routing.md` and `tools/handoff/` to Ember/Claude unless James asks Codex to own them.
- **Questions for Ember/James:** mirror the blessed status to the vault, log proof, and help isolate/commit this router slice without sweeping unrelated identity/selfmodel work into the commit.

### 2026-06-06 · SPEC_financial-consolidation-hub · branch `feat/financial-hub`

- **Status:** done / awaiting review
- **Files changed:** `tools/financial_hub/refresh.py`; `tools/decisions/daily_sync.py`; generated vault `[[FINANCIAL HUB]]`, HOME, `[[NEXT MOVE DETAIL]]`; cleaned vault DECISIONS / SPEC LOG / FPOS COCKPIT / PROOF LOG / AGENT RUN LEDGER / CODEX JOURNAL.
- **Summary:** Built the secret-free Financial Hub refresh script. It reads canonical local/vault financial sources and writes one consolidated money picture: net spendable, cash/crypto/bullion split, burn, SOL monitor, Zen Village ops, AI cost posture, open reconciliation, source map, and guardrails. It filters the resolved Bitrue reconciliation so an old local snapshot does not reopen settled concern. Attention cleanup moved completed Service Registry + Financial Hub prompts out of active DECISIONS, marked Financial Hub built in SPEC LOG, linked the hub in the cockpit, and refreshed HOME so the next true James signal is now Comms Hub.
- **Tests:** `python3 -m py_compile tools/financial_hub/refresh.py tools/decisions/daily_sync.py`; `python3 tools/financial_hub/refresh.py --check-only`; live `python3 tools/financial_hub/refresh.py`; live `python3 tools/decisions/daily_sync.py`; leak/stale scan on `[[FINANCIAL HUB]]`; HOME/detail read-back; `git diff --check`.
- **Cost:** ~$0 marginal · GPT Pro flat-rate · source: Codex desktop.
- **Risks:** Hub uses rounded summary figures and source pointers, not decrypted exact account detail. Remaining reconciliation items are real unresolved questions from the latest resources snapshot. No money actions were taken.
- **Rollback:** delete `tools/financial_hub/`; revert the one-line Comms Hub answer cleanup in `tools/decisions/daily_sync.py`; restore vault notes from Obsidian/iCloud history if desired.
- **Questions for Ember/James:** review the Financial Hub picture; next surfaced signal is Comms Hub (`yes - build it` / `no - after X` / `checkpoint`).

### 2026-06-06 · HOME next move bridge prompt · branch `feat/service-registry`

- **Status:** done
- **Files changed:** `tools/decisions/daily_sync.py`; generated vault HOME + `[[NEXT MOVE DETAIL]]`.
- **Summary:** HOME `NEXT MOVE` now tells James which agent receives the signal and the exact phrase to send. `[[NEXT MOVE DETAIL]]` adds `Send This` with the chosen phrase plus context pointers, so Claude Code / Ember or Codex can infer what to build instead of receiving a bare yes.
- **Tests:** `python3 -m py_compile tools/decisions/daily_sync.py`; `git diff --check`; live vault refresh; HOME read-back shows `Tell: Claude Code / Ember` + `Send: yes - build it / no - after X / checkpoint`; detail note read-back includes `Send This`.
- **Cost:** ~$0 marginal · GPT Pro flat-rate · source: Codex desktop.
- **Risks:** This is still a manual bridge; no background Telegram/Obsidian watcher auto-executes the answer.
- **Rollback:** revert the `send_detail`, HOME `Tell/Send`, and detail-note `Send This` additions.
- **Questions for Ember/James:** proactive Telegram bridge should be its own small spec: detect current next move → DM James → record answer → route to Ember/Codex after confirmation.

### 2026-06-06 · HOME next move compact question · branch `feat/service-registry`

- **Status:** done
- **Files changed:** `tools/decisions/daily_sync.py`; generated vault HOME + `[[NEXT MOVE DETAIL]]`.
- **Summary:** HOME `NEXT MOVE` now shows only one compact question, one answer line, and a clickable detail note. Routed/no-action work is filtered out of HOME; Service cleanup stays in logs/decision history, while the next actual James choice rises (`Build the financial-consolidation hub next?`). `[[NEXT MOVE DETAIL]]` carries who/where/why/how/AI-does.
- **Tests:** `python3 -m py_compile tools/decisions/daily_sync.py`; `git diff --check`; live vault refresh; HOME read-back shows `Answer: yes - build it / no - after X / checkpoint`; detail note read-back includes Tell/Where/Why/AI-does.
- **Cost:** ~$0 marginal · GPT Pro flat-rate · source: Codex desktop.
- **Risks:** Decision queue freshness matters; stale open decisions in `[[DECISIONS]]` can still surface unless filtered or archived.
- **Rollback:** revert the `refresh_home_next_move` compact format and `next_decision_move` routing changes.
- **Questions for Ember/James:** none.

### 2026-06-05 · HOME Decide answer-format · branch `feat/service-registry`

- **Status:** done
- **Files changed:** `tools/decisions/daily_sync.py`; generated vault HOME refresh.
- **Summary:** `Decide` no longer uses checkboxes for multiple-choice decisions. Routed items render as status; live decisions render as `Options:` plus `Your answer:` so James's answer is explicit and AI-parseable.
- **Tests:** `python3 -m py_compile tools/decisions/daily_sync.py`; `git diff --check`; live vault refresh; HOME read-back shows Service cleanup as routed status and SOL as `Options: hold / exit-de-lever` with `Your answer: hold`.
- **Cost:** ~$0 marginal · GPT Pro flat-rate · source: Codex desktop.
- **Risks:** Obsidian checkboxes are no longer used for these choices; that is intentional because checkboxes cannot encode which option was chosen.
- **Rollback:** revert the `refresh_home_decide` answer-format change.
- **Questions for Ember/James:** none.

### 2026-06-05 · HOME Decide one-line decisions · branch `feat/service-registry`

- **Status:** done
- **Files changed:** `tools/decisions/daily_sync.py`; generated vault HOME refresh.
- **Summary:** `Decide` now renders one line per actual decision: Service cleanup/map on one line, SOL on one line. Removed the vague `Public / money / people` row. The generator preserves old two-line SOL state and the new one-line SOL state, so checked `SOL: hold` stays checked across refreshes.
- **Tests:** `python3 -m py_compile tools/decisions/daily_sync.py`; `git diff --check`; live vault refresh; HOME read-back shows only `Service cleanup` and `SOL` decision rows.
- **Cost:** ~$0 marginal · GPT Pro flat-rate · source: Codex desktop.
- **Risks:** Inline options are less task-checkbox granular, but much clearer for attention.
- **Rollback:** revert the `refresh_home_decide` formatting change.
- **Questions for Ember/James:** none.

### 2026-06-05 · HOME next move target clarified · branch `feat/service-registry`

- **Status:** done
- **Files changed:** `tools/decisions/daily_sync.py`; generated vault HOME + daily refresh.
- **Summary:** HOME `NEXT MOVE` now includes `Tell:` so James knows who/model receives the signal: Codex for Buildstream specs, Claude Code / Ember for Midstream routing/overrides, and no one when the work is already routed unless James wants to override.
- **Tests:** `python3 -m py_compile tools/decisions/daily_sync.py`; `git diff --check`; live vault refresh; HOME read-back shows `Tell: No one. If you want to override, tell Claude Code / Ember.`
- **Cost:** ~$0 marginal · GPT Pro flat-rate · source: Codex desktop.
- **Risks:** Targeting is heuristic from the active next-move state; future human-specific moves should set `Tell:` to the named human.
- **Rollback:** revert the `daily_sync.py` `tell` field/render addition.
- **Questions for Ember/James:** none.

### 2026-06-05 · cleanup-services routed downstream · branch `feat/service-registry`

- **Status:** routed / waiting for full spec artifact
- **Files changed:** `tools/decisions/daily_sync.py`; generated vault HOME + daily refresh.
- **Summary:** Ember logged the Service Registry cleanup decision in the vault `SPEC LOG` as `cleanup-services` (`DECIDED → executing`). HOME now stops asking James to decide it again and shows `No action — cleanup is routed`. Codex search found the SPEC LOG row and sorted registry note, but no full `SPEC_cleanup-services.md` artifact in repo/vault yet.
- **Tests:** `python3 -m py_compile tools/decisions/daily_sync.py`; `git diff --check`; live vault refresh; HOME read-back shows `No action — cleanup is routed`; daily read-back shows the same top flow.
- **Cost:** ~$0 marginal · GPT Pro flat-rate · source: Codex desktop.
- **Risks:** Moving service directories from a SPEC LOG row alone would violate the Codex Parallel Build Protocol. Buildstream should wait for a full approved cleanup spec, or James/Ember must explicitly bless the sorted registry + SPEC LOG row as the spec artifact.
- **Rollback:** revert the `daily_sync.py` routed-state detection; HOME falls back to sorted-map decision.
- **Questions for Ember/James:** materialize `SPEC_cleanup-services.md` or explicitly confirm the sorted registry + SPEC LOG row is sufficient as the build spec.

### 2026-06-05 · Service Registry sorted overlay detected · branch `feat/service-registry`

- **Status:** coordinated / holding
- **Files changed:** `tools/decisions/daily_sync.py`; generated vault HOME + daily refresh.
- **Summary:** Ember organized the Service Registry into `[[SERVICE REGISTRY — SORTED]]`. HOME now treats this as a new state: not “review raw map,” but “decide cleanup spec.” Codex remains Buildstream-only here: no pruning, stopping, deleting, or archiving until James approves a separate reversible cleanup spec.
- **Tests:** `python3 -m py_compile tools/decisions/daily_sync.py`; live vault refresh; HOME read-back should point to `[[SERVICE REGISTRY — SORTED]]` with `spec cleanup-services` / `hold cleanup` / `checkpoint`.
- **Cost:** ~$0 marginal · GPT Pro flat-rate · source: Codex desktop.
- **Risks:** The sorted overlay is human-judgment Midstream output; Codex should use it as input only after a cleanup spec is approved.
- **Rollback:** revert the `daily_sync.py` state transition; HOME falls back to raw map review.
- **Questions for Ember/James:** approve a reversible cleanup spec, or hold cleanup.

### 2026-06-05 · HOME attention surfaces · branch `feat/service-registry`

- **Status:** done
- **Files changed:** `tools/decisions/daily_sync.py`; generated vault HOME + daily refresh.
- **Summary:** Simplified HOME for attention: `NEXT MOVE` now renders as one clear action (`Look` / `Why` / `Say` / `AI does`), `Today` is marker-free live context, and the old “Only you” prose section is now `Decide` with checkboxes and yes/no-style options. This keeps James at the top of stream and routes detail downstream.
- **Tests:** `python3 -m py_compile tools/decisions/daily_sync.py`; real vault refresh produced `home_stamp=1 · home_next=1 · home_decide=1`; read-back confirmed HOME has no visible `%%HOME_LIVE%%` markers and daily points to `Review map`.
- **Cost:** ~$0 marginal · GPT Pro flat-rate · source: Codex desktop.
- **Risks:** HOME remains only as clear as the active handoff/spec state. If Service Registry review finishes, the next run must refresh HOME again.
- **Rollback:** revert the `daily_sync.py` change; restore HOME/daily from Obsidian/iCloud history if desired.
- **Questions for Ember/James:** none. James asked for simpler attention UI; this is now generator-owned.

### 2026-06-05 · SPEC_service-registry · branch `feat/service-registry`

- **Status:** done / awaiting review
- **Files changed:** `tools/registry/build.py`, `docs/codex/SERVICE_REGISTRY.md`
- **Summary:** Added a read-only Service Registry / World Map generator. It scans `SERVICES/*`, detects service metadata + systemd units + git recency, classifies services, and writes a generated report. Current map: 127 services scanned / 127 rows written; counts: live 16, paused 2, archived 75, needs-human-classify 34. Report includes retire-candidates as suggestions only.
- **Tests:** `python3 -m py_compile tools/registry/build.py`; `python3 tools/registry/build.py`; reconciliation check `services=127 rows=127`; raw-IP check `0`; unredacted secret-like assignment check `0`; `git status --short -- SERVICES` showed no service modifications.
- **Cost:** ~$0 marginal · GPT Pro flat-rate · source: Codex desktop.
- **Risks:** Classification is heuristic from recency, unit presence, and metadata hints; uncertain entries are marked `❓ needs-human-classify`. No cleanup action was taken.
- **Rollback:** delete `tools/registry/` and `docs/codex/SERVICE_REGISTRY.md`.
- **Questions for Ember/James:** review the map, then decide whether to spec a separate prune/retire pass. Do not prune from this run.

### 2026-06-05 · HOME Next Move realtime generator · `feat/outbounders-ai-script-gen`

- **Status:** done
- **Files changed:** `tools/decisions/daily_sync.py`; generated vault HOME + daily refresh; proof/journal/ledger updated.
- **Summary:** HOME `NEXT MOVE` now refreshes as a top-of-stream James-action surface: one upstream signal, then AI/Codex carries Service Registry downstream. Daily top flow uses the same logic. Stale historical handoff entries no longer create "review/merge" priorities.
- **Tests:** `python3 -m py_compile tools/decisions/daily_sync.py`; real vault refresh: `home_stamp=1 · home_next=1`; read-back confirmed HOME + daily visible sections.
- **Risks:** The active repo handoff lane remains the source for the next build. If that lane drifts, HOME will reflect the drift.
- **Rollback:** revert the `daily_sync.py` change and restore HOME/daily from Obsidian/iCloud history.
- **Questions for Ember/James:** none. James confirmed the Flow gives clarity; HOME now carries it live.

### 2026-06-05 · SPEC_daily-realtime · branch `feat/daily-realtime`
- Status: done / awaiting review
- Files changed: `tools/decisions/daily_sync.py`, generated vault blocks in `07_DAILY/2026-06-05.md` + `HOME.md`
- Summary: Daily refresh now uses simulated/testable local time, classifies schedule items as past/NOW/NEXT, pulls top priorities from live decisions + the Codex handoff + North Star before falling back to `GOALS MIRROR`, adds a `✅ Moved today` block from today's `PROOF LOG`, refreshes a marked HOME live timestamp block, and suppresses stale already-built Codex specs/decisions.
- Tests: `python3 -m py_compile tools/decisions/daily_sync.py`; temp-vault simulation at `2026-06-05T13:00:00+03:00` showed morning item past, midday NOW, live priorities, moved-today proof, HOME stamp, and Service Registry as next; real vault refresh ran successfully.
- Cost: ~$0 marginal · GPT Pro flat-rate · source: Codex desktop.
- Risks: the decision queue itself still needs Ember/vault curation over time; this generator filters obvious completed Codex warm-up drift using the handoff board.
- Rollback: revert `tools/decisions/daily_sync.py`; remove the `%%HOME_LIVE%%` block from `HOME.md` if desired; rerun the prior generator version.
- Questions for Ember/James: please mirror/log this run to `PROOF LOG` + `AGENT RUN LEDGER`; Service Registry remains the next Codex-ready build.

### 2026-06-05 · Coordination ack · branch `feat/world-scout`
- Status: acknowledged
- Files changed: `docs/codex/HANDOFF.md`
- Summary: Received Ember's relay. Standing division accepted: Codex reads vault context freely, writes repo-side coordination/build artifacts, flags vault/cockpit drift in 📥 for Ember to apply. Merges remain held for James.
- Tests: n/a, coordination note only.
- Cost: ~$0 marginal · GPT Pro flat-rate · source: Codex desktop. The $200/month GPT Pro subscription is fixed burn, separate from the $20/day metered API cap.
- Risks: if a future Codex run uses metered API tokens instead of GPT Pro flat-rate, flag it as metered with an estimate before continuing.
- Rollback: remove this acknowledgement block.
- Questions for Ember/James: none. Cost policy accepted.

### 2026-06-05 · SPEC_world-scout · branch `feat/world-scout`
- Status: done / awaiting review
- Files changed: `tools/scout/scout.py`, `tools/scout/README.md`, `tools/scout/SCOUT_REPORT.md`
- Summary: Added local-first upgrade sequencer. It ranks known ecosystem candidates against a focus phrase, tags each `build/fork/API/ignore`, and recommends one next just-in-time upgrade.
- Tests: `python3 -m py_compile tools/scout/scout.py`; `python3 tools/scout/scout.py "clean up and focus the system" --json`; report contract check passed.
- Result: recommended **Service Registry / World Map** as next build.
- Risks: seed-based, no web research yet; useful for sequencing but not a live market scan.
- Rollback: delete `tools/scout/`.
- Questions for Ember/James: approve a new Service Registry / World Map spec?

### 2026-06-05 · SPEC_cost-meter-subagent-capture · branch `fix/cost-meter-subagent-capture`
- Status: done / awaiting review
- Files changed: `.claude/hooks/cost-tally.sh`
- Summary: Stop hook now discovers Claude Code Task sidechains at `~/.claude/projects/<project>/<session-id>/subagents/*.jsonl`, adds per-file cursors, and appends idempotent `subagent-turn` ledger rows.
- Tests: shell syntax check; synthetic fixture idempotency; historical sidechain fixture against temporary ledger; `cost-today` saw the combined rows.
- Risks: if Claude changes sidechain transcript layout, hook skips sidechains fail-open.
- Note: `~/.local/bin/cost-log` is outside this repository; the committed hook writes `~/.config/fpai/cost/ledger.jsonl` directly and does not require that CLI to run.
- Rollback: revert the two files; ledger is append-only.
- Questions for Ember/James: none.

---

## How this works (the loop)
1. **Codex** reads `AGENTS.md` → `docs/codex/README.md` → **this file** → `docs/codex/ATTENTION_FLOW.md` → the spec. Builds on its branch. Posts results in 📥.
2. **Ember** keeps 📍 current + the 📤 queue; reads 📥; logs finished work to the vault `PROOF LOG` + `AGENT RUN LEDGER`; writes a BRICK if reusable; **mirrors this file to `00_MEMORY/CODEX HANDOFF.md` in the vault** so James sees it.
3. **James** reads the vault `[[CODEX HANDOFF]]` (Obsidian) for the same picture; approves diffs (desktop/phone).

*Single source of truth for "where are we": this board. Journals (`JAMES JOURNAL` / `EMBER JOURNAL`) are reflections; PROOF LOG is shipped record; this is the live coordination.*
