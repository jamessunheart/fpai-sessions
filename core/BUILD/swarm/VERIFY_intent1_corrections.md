# Verification — Intent #1 (fix correction detector) · 2026-07-04

**Verdict: the swarm's #1-priority fix is WRONG. Do NOT ship the regex broadening.**

Ground truth (324 real user messages, brain_index.tg_messages):
- Current detector matches **1.9%** (6/324) — not literally 0%, and with false positives.
- Challenge-aware broadening (why-not / isn't-that / i-meant / that's-not-what):
  **+1 match in 324.** Near-zero gain. James genuinely doesn't phrase in corrections.

**The real finding (revised diagnosis):** "corrections" is a SPARSE, wrong signal source.
James's taste is expressed as **direction · approval · choice · reframe**, not "no/wrong/
actually." His messages are ~90% questions + directives ("Top priorities?", "this or
something better", "I agree with your approach"). The learning loop is under-fed not
because the regex is strict but because it mines the shallowest pool.

**The right fix (a signal-source reframe, not a regex tweak):** feed L2 from the broader
taste signal — approvals/rejections of proposals, choices between options (the debates!),
"more coherent" redirects, decision outcomes. The session's richest taste data (the A/B
debates + James's reframes) is invisible to a corrections detector. That is the intent to
build; #1-as-written is retired.

**Meta:** adversarially verifying a swarm finding against ground truth (P2) caught a
plausible-but-wrong fix before it was built. This is the "verify before build" discipline
paying for itself — the swarm was right that the learning signal is weak, wrong about why.
