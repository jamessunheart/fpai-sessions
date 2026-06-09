#!/bin/bash
# inbox_add.sh — convenience producer wrapper for James's Veto Inbox
#
# Adds an item to the inbox AND (if --notify) streams a TG ping respecting
# quiet hours + classification rules via existing stream_to_tg.sh.
#
# USAGE:
#   inbox_add.sh \
#     --category=yield|savings|sales|voice|zv|bridge|strategic|quick|treasury|ops|village|champion|infra|other \
#     --description="<one-line summary>" \
#     [--time-cost-min=N]         (default 5)
#     [--leverage=high|med|low]   (default med)
#     [--urgency=high|med|low]    (default med)
#     [--context-link=<path>]
#     [--classification=PRIVATE|COUNCIL-RESTRICTED|COUNCIL-OPEN|PUBLIC]  (default PRIVATE)
#     [--notes="..."]
#     [--notify]                  push a TG ping when leverage=high OR --notify forced
#     [--silent]                  suppress TG ping even if leverage=high
#
# Phoenix:
#   This script is a thin wrapper. Core lives in veto_inbox.py.
#   If TG broken, item still added. If python broken, exit non-zero.
#
# Exit:
#   0 ok  1 invalid args  2 python add failed  3 TG send failed (item still added)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INBOX_PY="${SCRIPT_DIR}/veto_inbox.py"
STREAM_TG="${SCRIPT_DIR}/stream_to_tg.sh"

CATEGORY=""
DESCRIPTION=""
TIME_COST=5
LEVERAGE="med"
URGENCY="med"
CONTEXT_LINK=""
CLASSIFICATION="PRIVATE"
NOTES=""
NOTIFY=0
SILENT=0

for arg in "$@"; do
    case "$arg" in
        --category=*)        CATEGORY="${arg#*=}" ;;
        --description=*)     DESCRIPTION="${arg#*=}" ;;
        --time-cost-min=*)   TIME_COST="${arg#*=}" ;;
        --leverage=*)        LEVERAGE="${arg#*=}" ;;
        --urgency=*)         URGENCY="${arg#*=}" ;;
        --context-link=*)    CONTEXT_LINK="${arg#*=}" ;;
        --classification=*)  CLASSIFICATION="${arg#*=}" ;;
        --notes=*)           NOTES="${arg#*=}" ;;
        --notify)            NOTIFY=1 ;;
        --silent)            SILENT=1 ;;
        *)                   echo "unknown arg: $arg" >&2; exit 1 ;;
    esac
done

if [ -z "$CATEGORY" ] || [ -z "$DESCRIPTION" ]; then
    echo "ERROR: --category and --description required" >&2
    echo "Try: inbox_add.sh --category=yield --description=\"Stripe key rotation\" --leverage=high" >&2
    exit 1
fi

# Add to inbox
ITEM_ID=$(python3 "$INBOX_PY" add \
    --category="$CATEGORY" \
    --description="$DESCRIPTION" \
    --time-cost-min="$TIME_COST" \
    --leverage="$LEVERAGE" \
    --urgency="$URGENCY" \
    --context-link="$CONTEXT_LINK" \
    --classification="$CLASSIFICATION" \
    --notes="$NOTES" 2>&1)

ADD_EXIT=$?
if [ $ADD_EXIT -ne 0 ]; then
    echo "ERROR: inbox add failed (exit $ADD_EXIT): $ITEM_ID" >&2
    exit 2
fi

echo "inbox: added $ITEM_ID"

# Decide on TG notify
SHOULD_NOTIFY=0
if [ "$SILENT" -eq 1 ]; then
    SHOULD_NOTIFY=0
elif [ "$NOTIFY" -eq 1 ]; then
    SHOULD_NOTIFY=1
elif [ "$LEVERAGE" = "high" ] || [ "$URGENCY" = "high" ]; then
    SHOULD_NOTIFY=1
fi

if [ "$SHOULD_NOTIFY" -eq 1 ] && [ -x "$STREAM_TG" ]; then
    SEV="med"
    [ "$URGENCY" = "high" ] && SEV="high"

    BODY="📥 New inbox item · [${ITEM_ID}] ${CATEGORY}
${DESCRIPTION}
lev=${LEVERAGE} · urg=${URGENCY} · ~${TIME_COST}m
/inbox show ${ITEM_ID}"

    "$STREAM_TG" \
        --category="inbox" \
        --severity="$SEV" \
        --classification="$CLASSIFICATION" \
        --body="$BODY" \
        ${CONTEXT_LINK:+--link="$CONTEXT_LINK"} \
        2>/dev/null || {
            echo "WARN: TG notify failed (item ${ITEM_ID} still added)" >&2
            exit 3
        }
fi

exit 0
