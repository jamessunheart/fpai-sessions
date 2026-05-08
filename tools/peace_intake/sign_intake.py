#!/usr/bin/env python3
"""
sign_intake.py — Email-to-Agreement intake for World Peace Agreement signers.

Takes an email message (from stdin or file path), parses signing intent,
creates a World Peace Agreement file via the Agreement Builder library,
and emits:

  - The created Agreement file (in core/INTENT/AGREEMENTS/)
  - A confirmation reply (printed to stdout, ready for SMTP send)
  - Optional: git commit, registry regen, and deploy

Designed to run on the production server, polled by systemd timer or
called from a webhook. See tools/peace_intake/README.md for deployment.

Usage:
  # Process a saved email file (smoke test, dev)
  python tools/peace_intake/sign_intake.py --email-file path/to/email.eml

  # Process from stdin (e.g. piped from imap fetcher)
  cat email.eml | python tools/peace_intake/sign_intake.py

  # Full pipeline — write file, regenerate registry, commit, deploy
  python tools/peace_intake/sign_intake.py \\
      --email-file path/to/email.eml \\
      --commit \\
      --deploy

  # Dry run — parse and preview without writing
  python tools/peace_intake/sign_intake.py --email-file path/to/email.eml --dry-run

Exit codes:
  0  signing processed (Agreement created)
  1  email rejected (subject doesn't match, missing fields, etc.)
  2  configuration / system error
"""

from __future__ import annotations

import argparse
import email
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from email.utils import parseaddr
from pathlib import Path

# Make the Agreement Builder importable
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "registry"))

# Import builder helpers
import new_agreement as builder  # noqa: E402

AGREEMENTS_DIR = REPO_ROOT / "core" / "INTENT" / "AGREEMENTS"
TOOLS_REGISTRY = REPO_ROOT / "tools" / "registry"
DEPLOY_SCRIPT = REPO_ROOT / "sites" / "zenvillage-peace" / "deploy.sh"

# ───────────────────────────── Configuration ─────────────────────────────

SUBJECT_PATTERN = re.compile(
    r"i\s+sign\s+the\s+world\s+peace\s+agreement",
    re.IGNORECASE,
)

# Body markers — used to extract signer name and detect flags
NAME_PATTERN = re.compile(
    r"^\s*(?:my\s+name|i\s+am|name|signed\s+by)\s*[:\-]\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

PRIVATE_PATTERN = re.compile(
    r"\bprivate\b|\bdo\s*not\s*publish\b|\bdon'?t\s*publish\b|\bnot\s+public\b",
    re.IGNORECASE,
)

WPO_PARTY = {
    "name": "World Peace Organization (Zen Village)",
    "role": "Receiver of public Agreements",
    "party_type": "organization",
}

# Reject senders whose addresses match these patterns (basic spam guard)
REJECT_FROM_PATTERNS = [
    re.compile(r"noreply", re.I),
    re.compile(r"no-reply", re.I),
    re.compile(r"mailer-daemon", re.I),
    re.compile(r"postmaster", re.I),
]


# ───────────────────────────── Email Parsing ─────────────────────────────

def load_email_message(args) -> email.message.Message:
    """Load email from --email-file or stdin."""
    if args.email_file:
        raw = Path(args.email_file).read_bytes()
    else:
        raw = sys.stdin.buffer.read()
    if not raw:
        sys.stderr.write("ERROR: empty input\n")
        sys.exit(2)
    return email.message_from_bytes(raw)


def get_body_text(msg: email.message.Message) -> str:
    """Extract plain-text body from a (possibly multipart) email."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        return payload.decode(charset, errors="replace")
                    except (LookupError, UnicodeDecodeError):
                        return payload.decode("utf-8", errors="replace")
        return ""
    payload = msg.get_payload(decode=True)
    if not payload:
        return msg.get_payload() or ""
    charset = msg.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except (LookupError, UnicodeDecodeError):
        return payload.decode("utf-8", errors="replace")


def extract_signer(msg: email.message.Message) -> tuple[str, str, str]:
    """
    Return (display_name, email_address, body_text).

    Display name resolution order:
      1. Body line "My name: X" / "I am X" / "Name: X" / "Signed by: X"
      2. Email "From" header display name
      3. Email username (before @)
    """
    body = get_body_text(msg)
    from_header = msg.get("From", "")
    from_display, from_email = parseaddr(from_header)

    body_name = None
    m = NAME_PATTERN.search(body)
    if m:
        body_name = m.group(1).strip()
        # strip trailing punctuation/period
        body_name = body_name.rstrip(".,;:")

    if body_name and len(body_name) >= 2 and len(body_name) <= 100:
        signer_name = body_name
    elif from_display:
        signer_name = from_display.strip()
    elif from_email and "@" in from_email:
        signer_name = from_email.split("@", 1)[0].replace(".", " ").replace("_", " ").title()
    else:
        signer_name = ""

    return signer_name, (from_email or "").lower(), body


def is_rejected_sender(from_email: str) -> bool:
    return any(p.search(from_email) for p in REJECT_FROM_PATTERNS)


# ───────────────────────────── Agreement Creation ─────────────────────────────

def collision_safe_path(base_path: Path) -> Path:
    """If base_path exists, append a suffix to make it unique."""
    if not base_path.exists():
        return base_path
    stem = base_path.stem
    parent = base_path.parent
    for i in range(2, 100):
        candidate = parent / f"{stem}_{i:02d}.md"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"too many collisions for {base_path.name}")


def build_signer_agreement(
    signer_name: str,
    signer_email: str,
    body_text: str,
    message_id: str,
    date_str: str,
) -> tuple[Path, dict, str]:
    """Construct meta + markdown for a signer Agreement. Return (path, meta, markdown)."""
    is_public = not bool(PRIVATE_PATTERN.search(body_text))

    parties = [
        {"name": signer_name, "role": "Signer of the World Peace Agreement", "party_type": "human"},
        WPO_PARTY,
    ]

    fname = builder.build_filename(date_str, parties)
    path = collision_safe_path(AGREEMENTS_DIR / fname)
    aid = path.stem.lower()

    witness_ref = message_id or f"email-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    meta = {
        "agreement_id": aid,
        "date_formed": date_str,
        "parties": parties,
        "context": "Public signing of the World Peace Agreement v1.0 — practitioner enters into the seven-clause covenant.",
        "scope_tags": ["public_signer", "individual_practitioner"],
        "status": "active",
        "public": is_public,
        "witness_type": "email",
        "witness_reference": witness_ref,
        "canonical_record": "file",
    }

    md = builder.build_markdown(meta, {}, drafted_by_third_party=False)
    return path, meta, md


# ───────────────────────────── Confirmation Reply ─────────────────────────────

CONFIRMATION_TEMPLATE = """\
Subject: You have signed the World Peace Agreement

Dear {name},

Welcome. Your signature has been received and recorded under the
Coherent Champions of CHRIST Manifesto v1.0.

You are now part of {visibility} World Peace Organization registry.

View the public roll:
  https://zenvillage.live/peace/registry/

Read the full manifesto:
  https://zenvillage.live/peace/#manifesto

────────────────────────────────────────────────────────────────

THE SEVEN COMMITMENTS YOU HAVE MADE

  • Practice peace in thought, word, and action.
  • Reduce unnecessary suffering.
  • Seek understanding before hatred.
  • Repair where you have caused harm.
  • Protect life, truth, beauty, and future generations.
  • Become trustworthy with intelligence, influence, and resources.
  • Make peace visible through action.

DAILY PRACTICES

  one act of service · one act of truth · one act of repair
  one act of regeneration · one moment of silence

WEEKLY PRACTICES

  shared meals · dialogue circles · music · movement · nature
  reflection · community contribution

────────────────────────────────────────────────────────────────

The Agreement is renewed not by re-signing it, but by living it.

Signed not in perfection, but in sincere participation.

— The World Peace Organization (Zen Village)
   https://zenvillage.live/peace/

P.S. If you ever need to update your Agreement (amend status,
mark private, withdraw), reply to this email and we will record
the change in the public ledger.
"""


def build_confirmation(signer_name: str, public: bool) -> str:
    visibility = "the public" if public else "the private (non-public)"
    return CONFIRMATION_TEMPLATE.format(name=signer_name, visibility=visibility)


# ───────────────────────────── Pipeline Operations ─────────────────────────────

def run_registry_regen() -> None:
    sys.stderr.write("→ regenerating registry…\n")
    subprocess.run([sys.executable, str(TOOLS_REGISTRY / "build_index.py")], check=True)
    sys.stderr.write("→ regenerating public roll…\n")
    subprocess.run([sys.executable, str(TOOLS_REGISTRY / "build_public_roll.py")], check=True)


def run_git_commit(file_path: Path, signer_name: str) -> None:
    sys.stderr.write(f"→ git committing for {signer_name}…\n")
    subprocess.run(
        ["git", "add", str(file_path.relative_to(REPO_ROOT)),
         "core/INTENT/AGREEMENTS/INDEX.md",
         "core/INTENT/AGREEMENTS/registry.json",
         "sites/zenvillage-peace/peace/registry/index.html"],
        cwd=REPO_ROOT, check=True
    )
    msg = (
        f"Form Agreement: signer {signer_name} via email intake\n"
        f"\nReceived through sign_intake.py (WPAP intake pipeline).\n"
        f"\nCo-Authored-By: WPAP Intake <peace@zenvillagecr.com>\n"
    )
    subprocess.run(["git", "commit", "-m", msg], cwd=REPO_ROOT, check=True)


def run_deploy() -> None:
    sys.stderr.write("→ deploying site…\n")
    subprocess.run([str(DEPLOY_SCRIPT)], cwd=REPO_ROOT, check=True)


# ───────────────────────────── Main ─────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="WPAP signing intake — email to Agreement file")
    ap.add_argument("--email-file", help="path to .eml file (default: read stdin)")
    ap.add_argument("--commit", action="store_true", help="git commit after creating Agreement")
    ap.add_argument("--deploy", action="store_true", help="run deploy.sh after committing")
    ap.add_argument("--dry-run", action="store_true", help="parse and preview, do not write")
    ap.add_argument("--no-regen", action="store_true", help="skip registry regen")
    args = ap.parse_args()

    if args.deploy and not args.commit:
        sys.stderr.write("WARN: --deploy without --commit will deploy uncommitted changes\n")

    msg = load_email_message(args)

    subject = msg.get("Subject", "")
    if not SUBJECT_PATTERN.search(subject):
        sys.stderr.write(
            f"REJECT: subject does not match signing pattern\n"
            f"  Got:      {subject!r}\n"
            f"  Expected: matches /i sign the world peace agreement/i\n"
        )
        return 1

    signer_name, signer_email, body = extract_signer(msg)

    if not signer_name:
        sys.stderr.write("REJECT: could not extract signer name from body or From header\n")
        return 1

    if is_rejected_sender(signer_email):
        sys.stderr.write(f"REJECT: blocked sender pattern matched: {signer_email}\n")
        return 1

    message_id = msg.get("Message-ID", "").strip("<>") or ""
    date_str = date.today().isoformat()

    path, meta, md = build_signer_agreement(
        signer_name=signer_name,
        signer_email=signer_email,
        body_text=body,
        message_id=message_id,
        date_str=date_str,
    )

    sys.stderr.write(
        f"\n─── INTAKE ─────────────────────────────────────────────\n"
        f"  signer:     {signer_name}\n"
        f"  email:      {signer_email}\n"
        f"  public:     {meta['public']}\n"
        f"  message-id: {message_id or '(none)'}\n"
        f"  file:       {path.relative_to(REPO_ROOT)}\n"
        f"────────────────────────────────────────────────────────\n\n"
    )

    if args.dry_run:
        sys.stderr.write("DRY RUN: not writing file\n")
        # Still emit the confirmation reply for inspection
        print(build_confirmation(signer_name, meta["public"]))
        return 0

    AGREEMENTS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(md, encoding="utf-8")
    sys.stderr.write(f"✓ wrote {path.relative_to(REPO_ROOT)}\n")

    if not args.no_regen:
        run_registry_regen()

    if args.commit:
        run_git_commit(path, signer_name)

    if args.deploy:
        run_deploy()

    # Print the confirmation message to stdout for the SMTP wrapper to send
    print(build_confirmation(signer_name, meta["public"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
