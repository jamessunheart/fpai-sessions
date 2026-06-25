# CORA Probe Rewards

Draft status: review-only until James/Ember approve live presentation.

CORA probe credits recognize testers who make the AI better through meaningful probe conversations. They are closed-loop attention credits inside the CORA system, not cash, not transferable value, not investment language, and not redeemable outside the reviewed CORA access menu.

## Earn Rule

Event type: `probe_conversation_complete`

Award trigger: a `brain_index.probe_sessions` record is closed and either `completed_spark = true` or the conversation reached 5 or more messages.

Credit amount:

| Condition | CORA credits |
|---|---:|
| Completed probe conversation | 10 |
| Tester reports a specific gap or correction | +5 |
| Conversation triggers a James-validated correction | +10 |

The awarder is idempotent by `probe_id`, so a probe conversation can receive this event once.

## Access Tiers

| Balance | Access unlocked |
|---:|---|
| 10 credits | Name appears in the CORA Nation contributor list, with public acknowledgment only after identity/display-name approval. |
| 25 credits | Early access to new AI features before public release. |
| 50 credits | 1:1 conversation with Ember as a priority access slot. |
| 100 credits | Invitation to the Zen Village / Camp Zen early-bird offer. |

These tiers are the current "points / rewards / access" promise for probe testers. They do not create cash value, resale value, ownership, governance rights, debt, equity, yield, or a guarantee that scarce access is available at all times.

## Runtime Notes

`tools/probe/award_cora.py` applies the narrow migration:

```sql
ALTER TABLE brain_index.probe_sessions ADD COLUMN IF NOT EXISTS tester_identifier TEXT;
```

The `tester_identifier` value is the outreach email or Telegram handle used to link the tester to their CORA credit. If the column is absent on an old schema, the awarder can fall back to `notes` metadata for handle/email during migration.
