#!/usr/bin/env bash
# Quick progress check for any in-flight brain_ingest run on the server.
# Run via:
#   ssh root@162.0.208.88 'bash -s' < ingest_progress.sh
# Or symlinked into /usr/local/bin/sh-brain-ingest-status on the server.
set -e

LOG=/var/log/sh-brain/claude-ingest.log
DB_URL=$(grep BRAIN_INDEX_DB_URL /etc/sh-brain/index.env | cut -d= -f2-)

if pgrep -f 'brain_ingest.*--source claude' > /dev/null; then
  STATUS="🟢 running"
  PID=$(pgrep -f 'brain_ingest.*--source claude' | head -1)
  ELAPSED=$(ps -p $PID -o etime= 2>/dev/null | xargs)
else
  STATUS="⏸ not running"
  ELAPSED="—"
fi

POSTS=$(grep -c 'POST /index/ingest/add_note' /var/log/nginx/access.log 2>/dev/null || echo 0)
TODAY_POSTS=$(grep "$(date +%d/%b/%Y)" /var/log/nginx/access.log 2>/dev/null | grep -c 'POST /index/ingest/add_note' || echo 0)

CHUNKS=$(/opt/sh-brain-src/.venv/bin/python - <<PY
import asyncio, psycopg, os
async def main():
    conn = await psycopg.AsyncConnection.connect("$DB_URL")
    async with conn.cursor() as cur:
        await cur.execute("SELECT count(*) FROM brain_index.note_chunks WHERE source IN ('claude','Claude')")
        (n,) = await cur.fetchone()
    print(n)
asyncio.run(main())
PY
)

cat <<EOF
sh-brain-ingest status
  process:         $STATUS  (elapsed: $ELAPSED)
  /add_note today: $TODAY_POSTS  (lifetime: $POSTS)
  claude chunks:   $CHUNKS

EOF
echo "Last 5 log lines:"
tail -5 "$LOG" 2>/dev/null || echo "(no log file)"
