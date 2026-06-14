"""brain-curator — AI-to-AI optimizer for Sunheart Brain.

The curator runs on scheduled cadences (hourly / 6h / daily / weekly / monthly)
on the Secondary server. Each job proposes structural improvements to the
brain and writes them to the "07 · Curator Queue" AppFlowy database.

Pipeline:
    1. Job runs → reads brain-index + AppFlowy state
    2. Picks candidates (near-duplicate pairs, stale conversations, untagged
       notes, etc.)
    3. Asks an LLM (Claude preferred, Ollama fallback) to produce a structured
       decision with reasoning and confidence
    4. Writes a proposal row to "07 · Curator Queue"
    5. If proposal type is in the "safe-auto-apply" list AND confidence is
       high, also executes the change immediately and marks the row
       ✅ Applied. Otherwise sits as 🟡 Proposed for human review.
    6. A separate `apply-approved` job scans the queue for rows the user
       flipped to ✅ Approved and executes them.

Everything is reversible: merges land in merge_log with the pre-state diff.
"""
