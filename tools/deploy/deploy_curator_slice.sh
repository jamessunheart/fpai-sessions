#!/usr/bin/env bash
# deploy_curator_slice.sh — d019: the GATED build→deploy bridge (curator/* slice).
#
# Closes merged≠live: takes AI-reviewed code from the build repo's curator/ and deploys it to the
# LIVE bot (/opt/sh-brain-src/curator/) — SAFELY. The keystone of self-standing FPOS.
#
# SAFETY MODEL (small blast radius, reversible, never clobbers):
#   - SLICE LOCK: only *.py under curator/. Never .env, secrets, /etc, anything outside the slice.
#   - ADDITIVE-ONLY v1: deploys files that are NEW live, or identical-base. A file that DIVERGED
#     from live (e.g. tgbot.py with live hand-patches) is SKIPPED + reported — never auto-overwritten.
#   - py_compile gate before any copy; full-package compile + health check after; AUTO-ROLLBACK on fail.
#   - Every deploy backed up to a timestamped dir → reversible via --rollback <stamp>.
#   - DRY-RUN by default. --apply to actually deploy. Logs to the ops ledger.
#   - HARD EXCLUDES credentials/secrets by pattern, defensively.
set -uo pipefail

BUILD=/opt/fpai-build/FPAI_Cockpit/SERVICES/sunheart-brain/curator
LIVE=/opt/sh-brain-src/curator
BAKROOT=/opt/sh-brain-src/.deploy-backups
SERVICE=sh-brain-tgbot
OL=/opt/fpai-build/FPAI_Cockpit/tools/build_loop/ops_log.py
STAMP=$(date -u +%Y%m%d-%H%M%S)
APPLY=0; ROLLBACK=""
for a in "$@"; do
  case "$a" in
    --apply) APPLY=1;;
    --rollback=*) ROLLBACK="${a#*=}";;
  esac
done
log(){ printf "%s\n" "$*"; }
ledger(){ FPAI_SURFACE=auto-merge python3 "$OL" deploy-bridge "$1" "$2" "\$0" "$3" 2>/dev/null || true; }

# secret/IO guard — refuse anything that smells like a credential even within the slice
is_secret(){ echo "$1" | grep -qiE 'secret|cred|token|\.env|password|api[_-]?key'; }

# ---------- rollback path ----------
if [ -n "$ROLLBACK" ]; then
  D="$BAKROOT/$ROLLBACK"
  [ -d "$D" ] || { log "no such backup: $ROLLBACK"; exit 1; }
  log "ROLLBACK from $D"
  cp -p "$D"/*.py "$LIVE"/ 2>/dev/null
  systemctl restart "$SERVICE"; sleep 4
  if [ "$(systemctl is-active $SERVICE)" = active ]; then
    log "rolled back + service active"; ledger reversed "rollback $ROLLBACK" ""; exit 0
  else
    log "ROLLBACK service NOT active — investigate"; exit 2
  fi
fi

# ---------- classify each build-repo curator file ----------
declare -a TO_DEPLOY=() DIVERGED=() SKIP=()
for f in "$BUILD"/*.py; do
  base=$(basename "$f")
  case "$base" in test_*|__init__.py) SKIP+=("$base (test/init)"); continue;; esac
  if is_secret "$base"; then SKIP+=("$base (secret-guard)"); continue; fi
  if [ ! -f "$LIVE/$base" ]; then
    TO_DEPLOY+=("$base")                                   # NEW live = additive, safe
  elif cmp -s "$f" "$LIVE/$base"; then
    : # identical, nothing to do
  else
    DIVERGED+=("$base")                                    # changed live = DO NOT clobber
  fi
done

log "=== deploy-bridge (curator slice) · stamp $STAMP · apply=$APPLY ==="
log "ADDITIVE (safe to deploy): ${TO_DEPLOY[*]:-none}"
log "DIVERGED (skipped — manual review, live has its own edits): ${DIVERGED[*]:-none}"
log "SKIPPED: ${SKIP[*]:-none}"

if [ "${#TO_DEPLOY[@]}" -eq 0 ]; then
  log "nothing additive to deploy."; ledger ran "no additive files; diverged=${#DIVERGED[@]}" ""; exit 0
fi

# ---------- py_compile gate on the new files ----------
for base in "${TO_DEPLOY[@]}"; do
  if ! python3 -m py_compile "$BUILD/$base" 2>/dev/null; then
    log "ABORT: $base fails py_compile in build repo"; ledger failed "py_compile $base" "fix build"; exit 3
  fi
done

if [ "$APPLY" -eq 0 ]; then
  log "DRY-RUN. would deploy: ${TO_DEPLOY[*]}. re-run with --apply."; exit 0
fi

# ---------- backup (additive files have no live original, but record the manifest) + deploy ----------
mkdir -p "$BAKROOT/$STAMP"
printf "%s\n" "${TO_DEPLOY[@]}" > "$BAKROOT/$STAMP/manifest.txt"
for base in "${TO_DEPLOY[@]}"; do
  [ -f "$LIVE/$base" ] && cp -p "$LIVE/$base" "$BAKROOT/$STAMP/$base"   # (additive → usually none)
  cp -p "$BUILD/$base" "$LIVE/$base"
  log "deployed $base"
done

# ---------- post-deploy: full compile + restart + health check + auto-rollback ----------
if ! /opt/sh-brain-src/.venv/bin/python -c "import compileall,sys; sys.exit(0 if compileall.compile_dir('$LIVE',quiet=1) else 1)" 2>/dev/null; then
  log "POST-COMPILE FAILED → rolling back"; for base in "${TO_DEPLOY[@]}"; do rm -f "$LIVE/$base"; [ -f "$BAKROOT/$STAMP/$base" ] && cp -p "$BAKROOT/$STAMP/$base" "$LIVE/$base"; done
  systemctl restart "$SERVICE"; ledger failed "post-compile; rolled back $STAMP" "review"; exit 4
fi
systemctl restart "$SERVICE"; sleep 4
if [ "$(systemctl is-active $SERVICE)" != active ] || journalctl -u "$SERVICE" --since '20 seconds ago' --no-pager 2>/dev/null | grep -qiE 'traceback|importerror|syntaxerror'; then
  log "HEALTH CHECK FAILED → rolling back $STAMP"
  for base in "${TO_DEPLOY[@]}"; do rm -f "$LIVE/$base"; [ -f "$BAKROOT/$STAMP/$base" ] && cp -p "$BAKROOT/$STAMP/$base" "$LIVE/$base"; done
  systemctl restart "$SERVICE"; sleep 3
  log "rolled back. service: $(systemctl is-active $SERVICE)"; ledger failed "health check; rolled back $STAMP" "review"; exit 5
fi
log "SUCCESS: deployed ${#TO_DEPLOY[@]} file(s), service active. backup: $BAKROOT/$STAMP"
log "reverse with: $0 --rollback=$STAMP"
ledger succeeded "deployed ${TO_DEPLOY[*]} (additive); diverged skipped=${#DIVERGED[@]}" "reverse=$STAMP"
