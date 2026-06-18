# AI Review — build/SPEC_d021_memory-rag-bridge-via-git-post

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Solid memory→RAG bridge with good path/secret guards, but the privacy classifier's sensitivity decision is discarded — every note is hardcoded as Personal, making the endpoint's private-tier refusal dead code for the only caller.

## Findings
- PRIVACY GAP: memory_git_bridge.py computes classify(body, tags) but only acts on classification.decision=='skip'. The payload hardcodes sensitivity='🟡 Personal' regardless of the classifier's actual tier. If classify() can return a 'private/keep-but-private' verdict (not 'skip'), that content is ingested into RAG as Personal, and the endpoint's `if sens_db=='private': refuse` guard becomes unreachable for the bridge path. Propagate the classifier's sensitivity instead of hardcoding it.
- Touches identity/memory SSOT and is intended to install a post-commit hook on production server 162 (/opt/fpai-build/memory/.git/hooks/post-commit). The diff itself does not touch 162 (deploy is manual per runbook), and it correctly branches off feat/headless-build not main — but live install requires Ember/James hands and the spec's RAG proof is unrun.
- Transaction/commit semantics: memory_git_note() runs INSERT loop + trailing-chunk DELETE inside `async with conn.cursor()` with no explicit commit. This matches existing add_note() pattern (presumed autocommit), but if the connection is NOT autocommit, writes silently never persist. Verify the connection mode before relying on it.
- Defense-in-depth is decent: path-traversal blocked in three places (_clean_memory_source_path, path_is_allowed, relative_to check), secret-path/marker exclusion list, personal→forced local embed (no external API for personal data), and DELETE-based rollback. Good.
- extract_markdown_tags() captures any '#token' including stray inline hashtags as tags; low-risk noise, not a security issue.
- add_note() scope touch (adding updated_at=NOW() to its ON CONFLICT) is minor and justified by the new column, but is unrelated to the stated d021 intent — acceptable but note the small scope creep.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
