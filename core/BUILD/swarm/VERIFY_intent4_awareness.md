# Verification — Intent #4 (awareness metric honesty) · 2026-07-04 · CONFIRMED

**Verdict: the honesty flag is CORRECT. "Awareness 100%" is a narrowed, mislabeled metric.**

Ground truth (`tools/awareness/verify_awareness.py` line 91-93):
- The probe returns TRUE iff `title in rendered` — i.e. the latest session_insight's TITLE
  string appears in the bot's rendered context. A **context-injection / string-presence** check.
- The original "5%" (SYSTEM_ARCHITECTURE.md:220) was `0/8 correct on live probe, 3
  hallucinations` — a **behavioral** test: does the bot ANSWER correctly?

**These measure different things, and the current one is far easier.** A title can be present
in context while the bot still hallucinates or fails to use it. So "100%" is TRUE for
render-continuity but says nothing about answer-correctness — which has been UNMEASURED since
the 5% baseline. The metric's label ("awareness reliability") overclaims what it measures.

**Honest correction to the record:** stop citing "awareness 100%" as if the bot is reliable.
It means "the latest insight's title is visible in context," not "the bot answers correctly."

**The right fix (intent #4, CONFIRMED real — unlike #1):** (a) rename the metric to
`context-render-continuity` across the JSON schema + HOT_STATE + ALIGNMENT + the metric_coherence
guard; (b) add a SEPARATE `--probe-bot-response` behavioral mode to verify_awareness.py that
actually asks the live bot a question and grades the answer. Never conflate the two again (P6:
two axes, two columns). This is a real build for the queue.

**Meta:** two swarm intents verified against ground truth this turn — #1 (corrections) was
WRONG (retired), #4 (awareness) is CONFIRMED. Adversarial verify-before-build separated the
real from the plausible. Exactly the discipline working.
