# SPEC_d188 Activation Audit Ledger

Generated with:

```bash
python3 tools/build_loop/activation_audit.py --repo-root . --ops-ledger /tmp/fpai-missing-ops.jsonl --markdown
```

Sandbox note: `/tmp/fpai-missing-ops.jsonl` intentionally has no live ops rows. This proves repo-local legacy declarations reduce historical inert rows to explained inert, not auto-activated.

| Spec | Classification | Explained | Evidence |
|---|---:|---:|---|
| `SPEC_build-queue-status` | INERT | true | `build_kind=inert` legacy declaration |
| `SPEC_cartographer-auto-refresh` | INERT | true | `build_kind=inert` legacy declaration |
| `SPEC_lantern-detector` | INERT | true | `build_kind=inert` legacy declaration |
| `SPEC_mirror-digest` | INERT | true | `build_kind=inert` legacy declaration |
| `SPEC_proof-river` | INERT | true | `build_kind=inert` legacy declaration |
| `build-20260614-cartographer-auto-refresh` | INERT | true | `build_kind=inert` legacy declaration |

Summary:

- Total merged builds audited: 6
- Auto-activated: 0
- Library/reference-backed: 0
- Explained inert: 6
- Unexplained inert: 0
