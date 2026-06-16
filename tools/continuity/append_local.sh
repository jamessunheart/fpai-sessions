#!/usr/bin/env bash
# UserPromptSubmit (162/phone-ember): append James prompt to the live thread (surface=phone).
# Filters out internal system prompts (council debate, code review, blueprint injection)
# that share the same claude -p invocation path and would pollute the signal.
P=$(python3 -c "
import json, sys
try:
    p = json.load(sys.stdin).get('prompt', '')
except Exception:
    p = ''

# Length gate: James messages are short; system prompts are always long
if len(p) > 600:
    sys.exit(0)

# Pattern gate: known system prompt prefixes
skip_prefixes = (
    'Goal: identify the single highest-leverage',  # council debate SYS
    'Branch build/',                                # ai_review diff prompt
    '[Module blueprints',                           # blueprint injection
    'You are an independent senior code reviewer',  # review SYS
    'You are an independent',                       # any reviewer persona
    '{',                                            # raw JSON
    'DECISION QUEUE:',                              # council queue dump
    'Diff to review:',                              # review diff
)
for prefix in skip_prefixes:
    if p.lstrip().startswith(prefix):
        sys.exit(0)

print(p)
" 2>/dev/null)
[ -z "$P" ] && exit 0
printf "%s" "$P" | /opt/sh-brain-src/.venv/bin/python /opt/sh-brain-src/tools/continuity/thread.py append phone james -
exit 0
