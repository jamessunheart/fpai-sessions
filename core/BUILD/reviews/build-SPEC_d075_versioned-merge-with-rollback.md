# 🔴 BLOCKED — touches the protected audit/improve layer

Branch `build/SPEC_d075_versioned-merge-with-rollback` modifies files that autonomous builds may NEVER touch:
- `tools/merge/merge_gate.sh`
- `tools/merge/pre_merge_snapshot.sh`
- `tools/merge/process_merge_requests.sh`
- `tools/merge/test_merge_gate.sh`
- `tools/merge/test_pre_merge_snapshot.sh`

This is escalated to James. Changes to the watchdog layer are human-directed only.
