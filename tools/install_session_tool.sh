#!/usr/bin/env bash
# install_session_tool.sh — make `session-state` callable from anywhere on this Mac.
#
# Installs:
#   ~/.local/bin/session-state  → symlink to tools/session_state.py
#   ~/.config/git/hooks/post-commit  → global git post-commit hook that
#       auto-pushes state on every commit in ANY repo
#   git config --global core.hooksPath ~/.config/git/hooks  (so the global hook fires)
#
# After this, every Claude session in every project reports state on commit,
# and the founder can call `session-state update --quest "X"` from any directory.
#
# Idempotent. Safe to run multiple times.

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="$HOME/.local/bin"
HOOK_DIR="$HOME/.config/git/hooks"
TOOL_PATH="$ROOT/tools/session_state.py"

if [ ! -f "$TOOL_PATH" ]; then
  echo "❌ session_state.py not found at $TOOL_PATH" >&2
  exit 1
fi

mkdir -p "$BIN_DIR"
mkdir -p "$HOOK_DIR"

# Step 1: symlink the tool to ~/.local/bin
ln -sf "$TOOL_PATH" "$BIN_DIR/session-state"
chmod +x "$BIN_DIR/session-state"
echo "✓ session-state command installed at $BIN_DIR/session-state"

# Step 2: ensure ~/.local/bin is on PATH
if ! echo "$PATH" | grep -q "$BIN_DIR"; then
  for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do
    if [ -f "$rc" ] && ! grep -q "$BIN_DIR" "$rc"; then
      echo '' >> "$rc"
      echo '# Added by FPAI_Cockpit/tools/install_session_tool.sh' >> "$rc"
      echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
      echo "✓ added $BIN_DIR to PATH in $rc (open new terminal to take effect)"
    fi
  done
fi

# Step 3: write a global post-commit hook that runs in ANY git repo
cat > "$HOOK_DIR/post-commit" <<'HOOK'
#!/usr/bin/env bash
# Global post-commit hook — pushes session state to fullpotential.com/api/sessions.
# Runs on every commit in every repo. Silent on failure. Never blocks.
set +e

# Skip if no token (means tool not configured for this user)
[ -f "$HOME/.config/sessions-api.token" ] || exit 0

# Pick session-state from PATH; bail if not present
SESSION_STATE="$(command -v session-state 2>/dev/null)"
[ -n "$SESSION_STATE" ] || exit 0

COMMIT_SUBJECT="$(git log -1 --pretty=format:%s 2>/dev/null | head -c 200)"
COMMIT_HASH="$(git log -1 --pretty=format:%h 2>/dev/null)"

"$SESSION_STATE" update \
  --quest "$COMMIT_SUBJECT" \
  --status "active" \
  --highlight "commit $COMMIT_HASH: $COMMIT_SUBJECT" \
  >/dev/null 2>&1 || true

exit 0
HOOK
chmod +x "$HOOK_DIR/post-commit"
echo "✓ global post-commit hook installed at $HOOK_DIR/post-commit"

# Step 4: tell git to use the global hooks dir
CURRENT_HOOKS_PATH="$(git config --global --get core.hooksPath || true)"
if [ "$CURRENT_HOOKS_PATH" != "$HOOK_DIR" ]; then
  if [ -n "$CURRENT_HOOKS_PATH" ] && [ "$CURRENT_HOOKS_PATH" != "$HOOK_DIR" ]; then
    echo "⚠️  git core.hooksPath was: $CURRENT_HOOKS_PATH"
    echo "   Skipping override. To enable global session-state hook, run:"
    echo "   git config --global core.hooksPath $HOOK_DIR"
  else
    git config --global core.hooksPath "$HOOK_DIR"
    echo "✓ git core.hooksPath set globally to $HOOK_DIR"
  fi
fi

echo ""
echo "✅ Installed. From any directory you can now run:"
echo "   session-state update --quest 'what I am working on' --next-move 'next thing'"
echo "   session-state list"
echo ""
echo "Every git commit in every repo will auto-push state too."
echo ""
echo "Test: cd to another project and run 'session-state list'."
