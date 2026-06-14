# June-5 Stash — Value Review & Recovery Map

A `git stash --include-untracked` on 2026-06-05 swept the **entire untracked working tree** into `stash@{0}`. It holds **2,270 files**, **2,261 of which exist nowhere else on disk**. Already bit us 3×: the applicant scorer, the Stop hooks, now everything else. This doc categorizes it so we know what's worth keeping.

**Nothing has been dropped.** Files extracted (read-only) to `/tmp/stash_review/`; full per-file manifest at `/tmp/stash_manifest.csv` (sortable: category, area, path, already_on_disk, size).

---

## Value tiers (tag → disposition)

| Tag | Bucket | Files | Size | Recommended action |
|-----|--------|------:|-----:|--------------------|
| 🟢 **KEEP** | **A · Operating substrate** (agents, hooks, .cursor rules/skills) | 60 | 0.4 MB | **Commit now** — tiny, high-value, defines how the AI runs |
| 🟢 **KEEP** | **E · Tools / scripts / infra** (deploy-tools, kai-bridge, lead-capture) | 147 | 1.0 MB | **Commit** after a glance — operational utilities |
| 🟢 **KEEP** | **C · Docs / specs / knowledge** (BUTR whitepapers, CORA legal/AML/KYC, bank procedures, loop proofs) | 296 (.md) | few MB | **Commit the .md** — irreplaceable knowledge work |
| 🔵 **SERVER-TRUTH** | **B · Service code** (aria-command 356, zen-village 103, concierge 83, ad-portal 78, whiterock 57…) | 1,364 | 12.9 MB | **Reconcile vs live servers** — these run deployed; server is source of truth. Commit only services not already live/tracked |
| ⚪ **DISCARD** | **D · Scratch / archive / hotfix** (`backups/fiart` 800 MB, `.workspace/active/tmp_*.html`, `.hotfix`) | 122 | 801 MB | **Drop** — mostly a fiart backup tarball + temp HTML. Glance at `.hotfix/*.py` first |
| ⚪ **DISCARD (from git)** | **F · Sites / voice assets** | 79 | **16.3 GB** | **Do NOT commit** — 16 GB is one ML model (`voice/models/personaplex-7b-v1/model.safetensors`). Binaries don't belong in git; store externally / re-download. Small site images can be kept |
| 🟡 **REVIEW** | **G · Other** | 30 | 0.6 MB | Quick manual look |

> The headline: **~16.8 GB of the stash is two binaries** (16 GB voice model + 800 MB fiart backup) that should never be in git anyway. The genuinely valuable, committable material — buckets A + E + C — is **~700 small text files, a few MB total.**

---

## What's in the KEEP buckets (so you can verify)

### 🟢 A · Operating substrate (commit these)
- **Custom agents** (`.claude/agents/`): true-narrator, the-cross-substrate-auditor, the-publisher, the-recursive-optimizer, the-standards-keeper, meta-narrator, privacy-narrator, consciousness-observer, compliance-scanner — *several of these are referenced in your agent roster.*
- **Hooks** (`.claude/hooks/`): preflight-inject, check-canonical-reads, dashboard-rebuild, stream-substrate-writes (the 5 footer/narrator hooks were already restored last turn).
- **`.codex/`** mirror (agents + hooks + hooks.json) — the Codex-harness twin.
- **`.cursor/`**: rules (deploy, backup, godmode, coordination, project-memory…), skills (deploy-service, backup-restore…), mcp.json, hooks.json.

### 🟢 C · Docs / knowledge (high-value samples)
- BUTR Universe v0.1→v0.3 + v1.0 whitepaper (+ critiques)
- CORA Nation: AML/KYC policy, admission/exit procedures, allocation-platform securities critique, religious-purpose canon
- Bank v0.1: ledger charter, PFIC operations memo, religious-purpose, procedures
- 15-year backcast, agent meta-architecture, AI treasury architecture
- Loop proofs 46–49 (your own shipped-work record)

---

## Recommended sequence (each step reversible, smallest blast radius first)

1. **Commit A** (substrate) — 60 files, defines AI operation. *(hooks subset already done.)*
2. **Commit E + C(.md)** after a skim — tools + knowledge, ~440 small files.
3. **Reconcile B** — check which SERVICES are live on the servers; commit only those not deployed/tracked elsewhere.
4. **Tag the whole stash** as `backup/june5-untracked` (permanent, recoverable forever) — captures D/F binaries without bloating the repo.
5. **Drop the stash entry** — now safe, since value is committed and the rest is tagged.

---

*Generated 2026-06-09 during the Suri-handover session, after the scorer + hook recoveries traced the same root cause.*
