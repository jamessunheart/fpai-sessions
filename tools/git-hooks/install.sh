#!/usr/bin/env bash
# Install git hooks from tools/git-hooks/ into .git/hooks/.
# Idempotent: replaces existing hooks of the same name.

set -e
ROOT="$(git rev-parse --show-toplevel)"
HOOK_SRC="$ROOT/tools/git-hooks"
HOOK_DST="$ROOT/.git/hooks"

mkdir -p "$HOOK_DST"

for src in "$HOOK_SRC"/*; do
  name="$(basename "$src")"
  case "$name" in
    install.sh|README*) continue ;;
  esac
  dst="$HOOK_DST/$name"
  cp "$src" "$dst"
  chmod +x "$dst"
  echo "installed: .git/hooks/$name"
done
