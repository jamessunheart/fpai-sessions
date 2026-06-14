#!/usr/bin/env python3
"""Patch v11 — make Ember's memory relevant AND current.

James 2026-06-14: "Fix memory as much as you can — it should be relevant and
current!" The bot stated OLD retrieved figures ($400k treasury, $25k goal) as
current fact because the note corpus is a historical archive with no recency
weighting. Three structural fixes:
  R1 — recency-rank: recent chunks + tg-memory beat stale ones (time decay over 120d).
  R2 — date every snippet with its year so the model can judge staleness.
  R3 — date-tag in the prompt + instruct: prefer recent/this-conversation; treat
       old specifics as possibly-outdated, attribute them by date, don't assert as current.

Safety: anchors match-once-or-abort, backup, compile-check, auto-revert.
"""
import shutil, py_compile, sys, time
P = "/opt/sh-brain-src/curator/tgbot.py"
src = open(P, encoding="utf-8").read()
edits = []

# R1 — recency decay + stronger tg-memory boost in the SQL
edits.append((
    "               (1 - (embedding <=> %s::vector)) + (CASE WHEN source = 'tg-memory' THEN 0.15 ELSE 0 END) AS score\n"
    "          FROM brain_index.note_chunks\n"
    "         WHERE sensitivity = ANY(%s)\n"
    "         ORDER BY (embedding <=> %s::vector) - (CASE WHEN source = 'tg-memory' THEN 0.15 ELSE 0 END)",
    "               (1 - (embedding <=> %s::vector))\n"
    "                 + (CASE WHEN source = 'tg-memory' THEN 0.25 ELSE 0 END)\n"
    "                 + GREATEST(0, 0.20 - 0.20 * LEAST(1, EXTRACT(EPOCH FROM (now() - created_at)) / (120*86400))) AS score\n"
    "          FROM brain_index.note_chunks\n"
    "         WHERE sensitivity = ANY(%s)\n"
    "         ORDER BY (embedding <=> %s::vector)\n"
    "                 - (CASE WHEN source = 'tg-memory' THEN 0.25 ELSE 0 END)\n"
    "                 - GREATEST(0, 0.20 - 0.20 * LEAST(1, EXTRACT(EPOCH FROM (now() - created_at)) / (120*86400)))",
))

# R2 — include the year in each snippet's date so staleness is visible
edits.append((
    '                    "added": ct.strftime("%b %-d") if ct else "",',
    '                    "added": ct.strftime("%b %-d, %Y") if ct else "undated",',
))

# R3a — show the date on each snippet in the prompt
edits.append((
    "            f\"[{i}] source={h['source']}/{h['sensitivity']} \"\n"
    "            f\"score={h['score']:.2f} tags={','.join(h['tags'][:4])}\\n\"",
    "            f\"[{i}] from {h['added']} · source={h['source']}/{h['sensitivity']} \"\n"
    "            f\"score={h['score']:.2f}\\n\"",
))

# R3b — instruct on staleness
edits.append((
    '        "No lists, no source citations, no headers, unless James explicitly asks for detail.\\n"\n'
    '        "Do not output markdown code fences, XML tags, or raw JSON.\\n"\n'
    '        "Keep it very short."',
    '        "No lists, no source citations, no headers, unless James explicitly asks for detail.\\n"\n'
    '        "Some snippets are old (see the \'from <date>\' tag). Money, numbers, goals, and personal facts "\n'
    '        "change — prefer the most recent memory and this conversation. If a specific figure or personal "\n'
    '        "detail comes only from an old note, treat it as possibly outdated; say roughly when it is from "\n'
    '        "rather than stating it as current truth.\\n"\n'
    '        "Do not output markdown code fences, XML tags, or raw JSON.\\n"\n'
    '        "Keep it very short."',
))

for a, b in edits:
    n = src.count(a)
    if n != 1:
        print(f"ABORT: anchor matched {n}x (need 1): {a[:55]!r}")
        sys.exit(1)
    src = src.replace(a, b)

bak = P + ".bak-currency-v11-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy2(P, bak)
open(P, "w", encoding="utf-8").write(src)
try:
    py_compile.compile(P, doraise=True)
    print(f"OK — {len(edits)} edits applied, compiles. bak={bak}")
except py_compile.PyCompileError as e:
    shutil.copy2(bak, P); print(f"REVERTED: {e}"); sys.exit(1)
