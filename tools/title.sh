#!/usr/bin/env bash
# title.sh — set the terminal window/tab title.
#
# Usage:
#   bash tools/title.sh "🌀 FPAI Cockpit · Loop 9 building"
#   . tools/title.sh "..."   # sourced — same effect
#
# Or as a shell function (add to ~/.zshrc):
#   ttitle() { printf '\033]0;%s\007' "$*"; }
#
# Works in: Terminal.app, iTerm2, Cursor terminal, VS Code, kitty, etc.

if [ -t 1 ]; then
  printf '\033]0;%s\007' "$*"
fi
