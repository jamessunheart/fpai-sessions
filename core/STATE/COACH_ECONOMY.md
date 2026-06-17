# Human Coach Matching + CORA Credit Economy

Status: repo-side scaffold only. No live outreach, fiat payout, DB migration, or production routing is enabled by this document.

## Roles

- Seeker: a person working toward full potential who gets stuck in a probe or regular conversation.
- Coach: a person the system has identified as having already navigated similar terrain.
- System: detects the stuck point, proposes a human match, tracks outcomes, awards CORA credits, and records learning signals.

## Match Trigger

The human-match offer is eligible when all are true:

- Conversation has at least 5 messages.
- The seeker has named a specific blocker: career, relationship, creative, health, or financial.
- The AI has already routed as well as it can and the seeker still signals being stuck or wanting more depth.

Suggested user-facing line:

```text
I know someone who has been exactly here. Want me to connect you?
```

## Coach Discovery

Coaches are discovered from high-quality probe conversations, not hired manually. A probe participant can become a pending coach when:

- `quality_score >= 0.7`
- The transcript shows they have navigated a specific challenge domain.
- The system extracts at least one specialty tag.

Pending coaches are inserted with `active=false` until they accept. The repo scaffold only composes the invitation text; it does not send messages.

## Credit Awards

| Event | CORA credits |
|---|---:|
| Text async session, 30 minutes | 25 |
| Voice session, 60 minutes | 75 |
| Video session, 60 minutes | 75 |
| Seeker rating is 4-5 stars | +15 |
| Seeker achieves stated goal within 30 days | +50 |

Awards are idempotent per session: if `coach_credits_awarded` is already set, the credit ledger does not add credits again.

## Unlock Tiers

| Balance | Unlock |
|---:|---|
| 25 | 1 month priority AI access |
| 50 | Early feature access |
| 100 | Zen Village / Camp Zen early-bird rate |
| 200 | Co-creator status review |
| 500 | Affiliate tier eligibility |

## Fiat Phase Gate

Phase 1 is credits only. Fiat conversion is blocked until there are at least 20 active coaches.

Phase 2 starts at 20 active coaches. The reviewed scaffold uses `$0.50 / credit` as the conversion rate, so a base 60-minute voice/video session maps to 75 credits or `$37.50` fiat equivalent.

No fiat movement is performed by the repo code. Any conversion or payout remains a Reserved Class action requiring explicit James approval and a separate live operations artifact.

## DB Shape

Expected future tables:

```sql
CREATE TABLE brain_index.coaches (
  id SERIAL PRIMARY KEY,
  identifier TEXT,
  platform TEXT,
  specialty_tags TEXT[],
  quality_score FLOAT,
  sessions_completed INT DEFAULT 0,
  cora_credits INT DEFAULT 0,
  fiat_earned FLOAT DEFAULT 0.0,
  active BOOLEAN DEFAULT true,
  recruited_from_probe_id TEXT
);

CREATE TABLE brain_index.coach_sessions (
  id SERIAL PRIMARY KEY,
  seeker_identifier TEXT,
  coach_id INT REFERENCES brain_index.coaches(id),
  matched_at TIMESTAMPTZ,
  blocker_type TEXT,
  session_type TEXT,
  completed BOOLEAN DEFAULT false,
  seeker_rating INT,
  coach_credits_awarded INT,
  outcome_achieved BOOLEAN,
  ai_brief TEXT
);
```

## Learning Signal

Completed sessions become positive routing examples:

- blocker type that required human escalation
- coach intervention the seeker rated highly
- whether the seeker achieved the stated goal
- credit/session metadata

The scaffold returns correction-shaped records for later insertion into `brain_index.corrections`; it does not write to the live DB in tests or by default.

