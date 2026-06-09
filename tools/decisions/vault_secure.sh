#!/bin/bash
# vault_secure.sh — encrypt-at-rest bridge for sensitive resources in the iCloud vault.
# James approved 2026-05-30 ("create this upgrade for visibility and security").
#
# MODEL: the vault stores ONLY ciphertext (RESOURCES_SENSITIVE.md.gpg). The passphrase
# lives in the macOS Keychain — NOT in the vault, NOT in iCloud. The AI (and James) decrypt
# on demand. Plaintext is assembled in a non-iCloud temp dir and securely removed after seal.
# Protects the iCloud channel. Does NOT protect a fully-compromised Mac (later hardening).
#
# Usage:
#   vault_secure.sh init-key      # generate passphrase into Keychain (idempotent)
#   vault_secure.sh seal          # rebuild encrypted blob from canonical sources
#   vault_secure.sh read          # decrypt to stdout (AI/James reading)
set -euo pipefail

SVC="fpos-vault-sensitive"
ACCT="ember"
VAULT="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/FPOS/Full Potential OS/00_MEMORY"
BLOB="$VAULT/RESOURCES_SENSITIVE.md.gpg"
MEM="$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory"
TRZ="$HOME/.config/fpai/treasury"

get_pass() { security find-generic-password -w -s "$SVC" -a "$ACCT" 2>/dev/null; }

cmd="${1:-}"
case "$cmd" in
  init-key)
    if get_pass >/dev/null 2>&1; then echo "✅ key already in Keychain ($SVC)"; exit 0; fi
    PASS="$(openssl rand -base64 32)"
    security add-generic-password -s "$SVC" -a "$ACCT" -w "$PASS" \
      -j "FPOS vault sensitive-resources passphrase (Ember + James). Created 2026-05-30." \
      -U
    echo "✅ passphrase generated + stored in Keychain ($SVC / $ACCT). Not printed."
    ;;

  seal)
    PASS="$(get_pass)" || { echo "❌ no key — run: vault_secure.sh init-key"; exit 1; }
    TMPD="$(mktemp -d "/tmp/vaultseal.XXXXXX")"; trap 'rm -Pf "$TMPD"/* 2>/dev/null; rmdir "$TMPD" 2>/dev/null' EXIT
    PT="$TMPD/plain.md"
    {
      echo "# RESOURCES — SENSITIVE (decrypted view)"
      echo
      echo "> 🔒 Decrypted from RESOURCES_SENSITIVE.md.gpg. Real amounts, addresses, server access."
      echo "> Ciphertext lives in iCloud; this plaintext exists only in memory when decrypted."
      echo "> Sealed: $(date '+%Y-%m-%d %H:%M %Z'). Rebuild with: vault_secure.sh seal"
      echo
      for src in "$TRZ/CURRENT.md" \
                 "$MEM/project_treasury_open_positions.md" \
                 "$MEM/reference_treasury_storage.md" \
                 "$MEM/reference_server_access.md"; do
        if [ -f "$src" ]; then
          echo; echo "---"; echo "## SOURCE: $(basename "$src")"; echo
          cat "$src"
        fi
      done
    } > "$PT"
    gpg --batch --yes --passphrase "$PASS" --symmetric --cipher-algo AES256 -o "$BLOB" "$PT"
    # secure-remove plaintext
    rm -Pf "$PT"
    echo "✅ sealed → $BLOB ($(wc -c <"$BLOB" | tr -d ' ') bytes ciphertext). Plaintext shredded."
    ;;

  read)
    PASS="$(get_pass)" || { echo "❌ no key — run: vault_secure.sh init-key"; exit 1; }
    [ -f "$BLOB" ] || { echo "❌ no sealed blob — run: vault_secure.sh seal"; exit 1; }
    gpg --batch --quiet --passphrase "$PASS" -d "$BLOB"
    ;;

  *)
    echo "usage: vault_secure.sh {init-key|seal|read}"; exit 1;;
esac
