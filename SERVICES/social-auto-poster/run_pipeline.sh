#!/usr/bin/env bash
# Content Pipeline V1 — post-commit hook helper.
# Collects the latest commit's metadata, ships as JSON over SSH to the
# brain server, which drafts a build-in-public micro-post via Haiku and
# sends a Telegram preview to James. Backgrounded; silent on failure.
#
# Wired from .git/hooks/post-commit Job 5. Reversible: disable by chmod -x.

set -u

# Resolve repo root (the hook is invoked from there but we guard anyway).
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
[ -z "$ROOT" ] && exit 0
cd "$ROOT" || exit 0

command -v ssh >/dev/null 2>&1 || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

SHA="$(git rev-parse --short HEAD 2>/dev/null)"
[ -z "$SHA" ] && exit 0

q() { python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))'; }
qlist() { python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().splitlines()))'; }

SUBJECT="$(git log -1 --pretty=format:%s | q)"
BODY="$(git log -1 --pretty=format:%b | q)"
FILES="$(git diff-tree --no-commit-id --name-only -r HEAD | qlist)"
STAT="$(git show --stat --format= HEAD | q)"
AUTHOR="$(git log -1 --pretty=format:%an | q)"

PAYLOAD="{\"sha\":\"${SHA}\",\"subject\":${SUBJECT},\"body\":${BODY},\"files\":${FILES},\"stat\":${STAT},\"author\":${AUTHOR}}"

echo "$PAYLOAD" | ssh -o ConnectTimeout=5 -o BatchMode=yes root@162.0.208.88 \
  'set -a; source /etc/sh-brain/curator.env 2>/dev/null; set +a; python3 /opt/content-pipeline/tools/draft_from_commit.py' \
  >/dev/null 2>&1 || true
