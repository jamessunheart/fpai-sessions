#!/usr/bin/env python3
"""
classify_promote.py — propose promotion of a memory file from one classification tier to a higher one.

USAGE:
    classify_promote.py <source-file> --target=COUNCIL-OPEN
    classify_promote.py <source-file> --target=PUBLIC --curate
    classify_promote.py <source-file> --target=PUBLIC --curate --commit  (writes to public_curated/)

DESIGN CONTRACT:
    - NEVER overwrites the source file
    - NEVER publishes anywhere on its own (requires --commit for staging move)
    - ALWAYS writes audit record
    - Proposes promotion to staging dir; James reviews before final
    - Refuses demotion (use a direct edit for that)
    - Refuses any operation that would re-classify already-published Tier 3 content downward

Exit codes:
    0 success (proposal staged + audit written)
    1 invalid args
    2 source-not-found
    3 demotion attempted (refused)
    4 voice/adversarial check failed (for --curate)
    5 tier-3 reverse-prevention triggered
"""

import argparse
import sys
from pathlib import Path

# Use absolute import path (script lives in infra/scripts/)
sys.path.insert(0, str(Path(__file__).parent))
import classification_lib as cl


STAGING_DIR = Path.home() / ".config" / "fpai" / "classification_architecture" / "staging"
PUBLIC_CURATED_DIR = Path.home() / ".config" / "fpai" / "classification_architecture" / "public_curated"
AUDIT_DIR = Path.home() / ".config" / "fpai" / "classification_audit"
TIER3_LOG = AUDIT_DIR / "tier3_published.tsv"


def main() -> int:
    parser = argparse.ArgumentParser(description="Propose promotion of a memory file to a higher classification tier.")
    parser.add_argument("source", help="Path to source markdown file")
    parser.add_argument("--target", required=True, choices=list(cl.TIERS.keys()),
                        help="Target classification tier")
    parser.add_argument("--curate", action="store_true",
                        help="Apply Tier 3 curation pipeline (voice-check + adversarial-check)")
    parser.add_argument("--commit", action="store_true",
                        help="For --target=PUBLIC with --curate: move staged file to public_curated/ + log to tier3_published.tsv")
    parser.add_argument("--operator", default="forge",
                        help="Operator name for audit log (default: forge)")
    args = parser.parse_args()

    src = Path(args.source).expanduser().resolve()
    if not src.exists():
        print(f"ERROR: source file not found: {src}", file=sys.stderr)
        return 2

    target_tier_str = args.target
    target_tier_num = cl.TIERS[target_tier_str]

    # Read source
    source_text = src.read_text()
    source_classification = cl.parse_frontmatter_classification(source_text)
    source_tier_num = cl.TIERS[source_classification]

    # Refuse demotion
    if target_tier_num < source_tier_num:
        print(f"REFUSED: demotion from {source_classification} to {target_tier_str} is not allowed via this tool.", file=sys.stderr)
        print("To make content MORE private, edit the file directly (changing the classification field).", file=sys.stderr)
        return 3

    # Same-tier is a no-op
    if target_tier_num == source_tier_num:
        print(f"NO-OP: source already at {source_classification}.", file=sys.stderr)
        return 0

    # Tier 3 reverse-prevention check
    source_hash = cl.sha256_hash(source_text)
    if target_tier_str != "PUBLIC" and cl.check_tier3_published(source_hash, TIER3_LOG):
        print(f"REFUSED: source file hash already exists in tier3_published.tsv. Tier 3 content cannot be re-classified downward.", file=sys.stderr)
        print("Use 'retract+note' workflow instead (write a new Tier 3 file documenting the retraction).", file=sys.stderr)
        return 5

    # Apply redaction pipeline for target tier
    transformed_text, redaction_records = cl.transform(source_text, target_tier_num)

    # Update frontmatter classification
    transformed_text = cl.set_frontmatter_classification(transformed_text, target_tier_str)

    proposed_hash = cl.sha256_hash(transformed_text)

    # Tier 3 curation pipeline
    voice_passed = True
    voice_reasons: list[str] = []
    adv_passed = True
    adv_reasons: list[str] = []
    if args.curate:
        voice_passed, voice_reasons = cl.voice_check(transformed_text)
        adv_passed, adv_reasons = cl.adversarial_check(transformed_text)

    # Decide where to stage
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    staged_path = STAGING_DIR / f"{src.stem}.{target_tier_str}.md"

    # Write staged file (always — even if checks failed, so James can review)
    staged_path.write_text(transformed_text)

    # Build audit record
    audit_record = {
        "timestamp": cl.utc_now().isoformat(),
        "source_path": str(src),
        "source_classification": source_classification,
        "target_classification": target_tier_str,
        "source_hash_sha256": source_hash,
        "proposed_hash_sha256": proposed_hash,
        "redactions": redaction_records,
        "staged_path": str(staged_path),
        "curate": args.curate,
        "voice_check_passed": voice_passed,
        "voice_check_reasons": voice_reasons,
        "adversarial_check_passed": adv_passed,
        "adversarial_check_reasons": adv_reasons,
        "operator": args.operator,
        "committed_to_public": False,
        "final_status": "STAGED",
    }

    # Final-status logic
    if args.curate and (not voice_passed or not adv_passed):
        audit_record["final_status"] = "CHECKS_FAILED"
        cl.write_audit(AUDIT_DIR, audit_record)
        print(f"STAGED with FAILED checks at: {staged_path}", file=sys.stderr)
        print(f"  Voice check passed: {voice_passed} {voice_reasons}", file=sys.stderr)
        print(f"  Adversarial check passed: {adv_passed} {adv_reasons}", file=sys.stderr)
        print(f"  Content stays at Tier 2 until issues resolved.", file=sys.stderr)
        return 4

    # Commit to public_curated (only with --commit + --curate + target=PUBLIC + checks passed)
    if args.commit:
        if target_tier_str != "PUBLIC" or not args.curate:
            print("ERROR: --commit requires --target=PUBLIC and --curate", file=sys.stderr)
            return 1
        PUBLIC_CURATED_DIR.mkdir(parents=True, exist_ok=True)
        public_path = PUBLIC_CURATED_DIR / f"{src.stem}.md"
        public_path.write_text(transformed_text)
        cl.log_tier3_publish(TIER3_LOG, src.stem, proposed_hash, str(src))
        audit_record["committed_to_public"] = True
        audit_record["public_path"] = str(public_path)
        audit_record["final_status"] = "PUBLISHED"
        print(f"PUBLISHED to: {public_path}", file=sys.stderr)
        print(f"Logged to: {TIER3_LOG}", file=sys.stderr)

    audit_path = cl.write_audit(AUDIT_DIR, audit_record)
    print(f"AUDIT: {audit_path}")
    print(f"STAGED: {staged_path}")
    print(f"Redactions applied: {len(redaction_records)}")
    for r in redaction_records:
        print(f"  - {r['pattern']}: {r['example']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
