#!/usr/bin/env python3
"""
new_agreement.py — The Agreement Builder.

The first module of the World Peace Agreements Protocol (WPAP, Layer 5
of the World Peace Ecosystem — see core/INTENT/WORLD_PEACE_AGREEMENTS_PROTOCOL.md).

Walks a user through forming a specific World Peace Agreement under the
Coherent Champions of CHRIST Manifesto, generates the markdown file with
proper YAML front-matter, and regenerates the public registry.

Usage:
  python tools/registry/new_agreement.py             # interactive
  python tools/registry/new_agreement.py --detailed  # also prompt for per-party commitments
  python tools/registry/new_agreement.py --help

Output:
  core/INTENT/AGREEMENTS/{YYYY-MM-DD}_{SLUG}.md

Standalone — no external dependencies (Python stdlib only).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AGREEMENTS_DIR = REPO_ROOT / "core" / "INTENT" / "AGREEMENTS"
TOOLS_DIR = REPO_ROOT / "tools" / "registry"

VALID_PARTY_TYPES = {"human", "ai", "organization", "community", "land", "system"}
VALID_STATUSES = {"proposed", "active", "breached", "repairing", "repaired", "withdrawn", "archived"}

# Standard seven clauses from the canonical World Peace Agreement
STANDARD_COMMITMENTS = [
    "I agree to practice peace in thought, word, and action.",
    "I agree to reduce unnecessary suffering.",
    "I agree to seek understanding before hatred.",
    "I agree to repair where I have caused harm.",
    "I agree to protect life, truth, beauty, and future generations.",
    "I agree to become trustworthy with intelligence, influence, and resources.",
    "I agree that peace must become visible through action.",
]


# ───────────────────────────── Prompting ─────────────────────────────

def prompt(label: str, default: str = "") -> str:
    """Prompt with optional default. Empty input returns default."""
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"{label}{suffix}: ").strip()
    except EOFError:
        return default
    return val if val else default


def prompt_yes_no(label: str, default: bool = True) -> bool:
    default_str = "yes" if default else "no"
    while True:
        ans = prompt(label, default_str).lower()
        if ans in ("y", "yes", "true", "1"):
            return True
        if ans in ("n", "no", "false", "0"):
            return False
        print(f"  please answer yes or no")


def prompt_choice(label: str, choices: set[str], default: str) -> str:
    while True:
        val = prompt(label, default)
        if val in choices:
            return val
        print(f"  must be one of: {', '.join(sorted(choices))}")


def prompt_parties() -> list[dict]:
    print()
    print("Parties — enter one per line as:  Name | Role | type")
    print(f"   types: {', '.join(sorted(VALID_PARTY_TYPES))}")
    print(f"   (empty line to finish — minimum 2 parties)")
    parties = []
    while True:
        line = prompt(f"  party {len(parties)+1}", "")
        if not line:
            if len(parties) >= 2:
                return parties
            print(f"  need at least 2 parties (have {len(parties)})")
            continue
        bits = [b.strip() for b in line.split("|")]
        if len(bits) != 3:
            print(f"  format: Name | Role | type")
            continue
        name, role, ptype = bits
        if ptype not in VALID_PARTY_TYPES:
            print(f"  type must be one of: {', '.join(sorted(VALID_PARTY_TYPES))}")
            continue
        parties.append({"name": name, "role": role, "party_type": ptype})


def prompt_specific_commitments(party_name: str) -> list[str]:
    """Optionally collect commitments specific to one party."""
    print(f"\n  Specific commitments for {party_name} (one per line, empty to finish):")
    commits = []
    while True:
        line = prompt(f"    +", "")
        if not line:
            return commits
        commits.append(line)


# ───────────────────────────── Slug + Path ─────────────────────────────

def slugify_party(name: str) -> str:
    """Make a filename-safe slug from a party name."""
    s = re.sub(r"\([^)]*\)", "", name)  # drop parenthetical
    s = re.sub(r"[^A-Za-z0-9]+", "_", s)
    s = s.strip("_").upper()
    return s or "PARTY"


def build_filename(date_str: str, parties: list[dict]) -> str:
    party_slugs = [slugify_party(p["name"]) for p in parties[:3]]  # cap at 3
    if len(parties) > 3:
        party_slugs.append("ETAL")
    return f"{date_str}_{('_AND_').join(party_slugs)}.md"


# ───────────────────────────── YAML / Markdown ─────────────────────────────

def yaml_str(s: str) -> str:
    """Quote a string for YAML if needed; otherwise return bare."""
    if not s:
        return '""'
    needs_quote = any(c in s for c in ":#&*!|>'\"%@`") or s.strip() != s
    if needs_quote:
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return s


def build_frontmatter(meta: dict) -> str:
    lines = ["---"]
    lines.append(f"agreement_id: {meta['agreement_id']}")
    lines.append(f"date_formed: {meta['date_formed']}")
    lines.append("parties:")
    for p in meta["parties"]:
        lines.append(f"  - name: {yaml_str(p['name'])}")
        lines.append(f"    role: {yaml_str(p['role'])}")
        lines.append(f"    party_type: {p['party_type']}")
    lines.append(f"context: {yaml_str(meta['context'])}")
    if meta.get("scope_tags"):
        lines.append("scope_tags:")
        for t in meta["scope_tags"]:
            lines.append(f"  - {t}")
    else:
        lines.append("scope_tags: []")
    lines.append(f"status: {meta['status']}")
    lines.append(f"public: {'true' if meta['public'] else 'false'}")
    lines.append("witness:")
    lines.append(f"  type: {meta['witness_type']}")
    lines.append(f"  reference: {yaml_str(meta['witness_reference'])}")
    lines.append(f"canonical_record: {meta['canonical_record']}")
    lines.append("amendments: []")
    lines.append("repairs: []")
    if meta.get("proposed_by"):
        lines.append(f"proposed_by: {yaml_str(meta['proposed_by'])}")
        lines.append(f"proposed_on: {meta['date_formed']}")
    lines.append("---")
    return "\n".join(lines)


def build_party_commitments_section(parties: list[dict], specific: dict[str, list[str]]) -> str:
    """Render commitments — standard seven plus optional party-specific."""
    out = []
    for p in parties:
        out.append(f"### {p['name']}'s Commitments\n")
        out.append("From the canonical World Peace Agreement template:\n")
        for c in STANDARD_COMMITMENTS:
            out.append(f"- {c}")
        out.append("")
        sp = specific.get(p["name"], [])
        if sp:
            out.append(f"**Specific to this Agreement:**\n")
            for c in sp:
                out.append(f"- {c}")
            out.append("")
    return "\n".join(out)


def build_title_and_party_block(parties: list[dict]) -> tuple[str, str]:
    names = [p["name"] for p in parties[:3]]
    if len(parties) > 3:
        names.append("others")
    title = "WORLD PEACE AGREEMENT — " + " AND ".join(n.upper() for n in names)
    party_block_lines = ["**Parties:**"]
    for p in parties:
        party_block_lines.append(f"- **{p['name']}** — {p['role']} *(party type: {p['party_type']})*")
    return title, "\n".join(party_block_lines)


def build_markdown(meta: dict, specific: dict[str, list[str]], drafted_by_third_party: bool) -> str:
    title, party_block = build_title_and_party_block(meta["parties"])
    drafting_note = ""
    if drafted_by_third_party:
        drafting_note = (
            f"> **Drafting note:** This Agreement was drafted by {meta.get('proposed_by','a non-party')} "
            f"on {meta['date_formed']}. Status is `proposed`, not yet binding. The named parties must "
            f"ratify (by editing status to `active`, setting witness, removing this drafting note) for "
            f"the Agreement to take effect.\n"
        )

    body = f"""---
{build_frontmatter(meta).split(chr(10), 1)[1].rsplit(chr(10), 1)[0]}
---

# {title}

{drafting_note}**Date formed:** {meta['date_formed']}

{party_block}

**Context:** {meta['context']}

**Witness:** {meta['witness_type']} · `{meta['witness_reference']}`

---

## Basis

This Agreement is founded on the seven CHRIST principles of the Coherent Champions of CHRIST Manifesto:

- **Coherence** — alignment between thought, word, action, and consequence
- **Healing** — work that heals rather than harms
- **Regeneration** — building systems that restore more than they consume
- **Intelligence** — guided by wisdom, humility, discernment, and care
- **Service** — gifts in service to the flourishing of life
- **Truth** — sought courageously, held compassionately

---

## Commitments

{build_party_commitments_section(meta['parties'], specific)}
---

## Scope

**This Agreement governs:** the cooperation between the named parties on the matter described in *Context* above.

**This Agreement does not govern:** other relationships of the parties; matters not named in scope; force majeure beyond reasonable stewardship.

If the parties wish to bind a broader or narrower scope, they should amend the Agreement and record the change in the `amendments` field of the front-matter.

---

## Repair Process

When any party breaks this Agreement:

1. **Notice** — the other party (or any witness) names the break
2. **Acknowledge** — the breaking party acknowledges without rationalization
3. **Understand** — both parties name what happened and what conditions made the break likely
4. **Restore** — where possible, the harm is repaired; where impossible, it is named honestly in the record
5. **Update** — if the Agreement was insufficient, it is amended (recorded in `repairs[]` and/or a new dated file)

A broken Agreement that is repaired strengthens the practice. A broken Agreement that is hidden weakens it.

---

## Renewal

This Agreement is renewed every time it is lived. It is not re-signed each interaction. A breach without repair effectively withdraws the breaching party. The Agreement protects all parties from drift — including drift in the form of urgency, charisma, or claimed authority pushing one party past coherent action.

---

## Signing

*Signed not in perfection, but in sincere participation.*

"""
    for p in meta["parties"]:
        body += f"— **{p['name']}** ({p['role']}). The act of forming this Agreement is the signature.\n\n"

    body += f"""---

## Reference

- Founding document: [`../COHERENT_CHAMPIONS_MANIFESTO.md`](../COHERENT_CHAMPIONS_MANIFESTO.md)
- Template: [`../WORLD_PEACE_AGREEMENT.md`](../WORLD_PEACE_AGREEMENT.md)
- Forming protocol: [`../FORMING_AGREEMENTS.md`](../FORMING_AGREEMENTS.md)
- WPAP roadmap: [`../WORLD_PEACE_AGREEMENTS_PROTOCOL.md`](../WORLD_PEACE_AGREEMENTS_PROTOCOL.md)
- Public roll (if `public: true`): https://zenvillage.live/peace/registry/
"""
    return body


# ───────────────────────────── Registry Regen ─────────────────────────────

def regenerate_registry(also_public_roll: bool) -> None:
    print()
    print("→ regenerating registry…")
    subprocess.run([sys.executable, str(TOOLS_DIR / "build_index.py")], check=True)
    if also_public_roll:
        print("→ regenerating public roll…")
        subprocess.run([sys.executable, str(TOOLS_DIR / "build_public_roll.py")], check=True)


# ───────────────────────────── Main ─────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Interactive Agreement Builder (WPAP Module 1)")
    ap.add_argument("--detailed", action="store_true", help="also prompt for per-party specific commitments")
    ap.add_argument("--no-regen", action="store_true", help="don't regenerate registry after creating")
    ap.add_argument("--no-public-roll", action="store_true", help="regenerate registry but skip public roll")
    args = ap.parse_args()

    print()
    print("═══════════════════════════════════════════════════════════════")
    print("  THE AGREEMENT BUILDER")
    print("  WPAP Module 1 — first module of the World Peace Agreements")
    print("  Protocol. Coherence layer for forming agreements.")
    print("═══════════════════════════════════════════════════════════════")
    print()

    today = date.today().isoformat()
    date_formed = prompt("Date formed", today)

    parties = prompt_parties()

    print()
    context = prompt("Context (one line — what this Agreement is for)")
    if not context:
        print("ERROR: context required")
        return 2

    print()
    print("Scope tags — comma-separated keywords (e.g. cooperation, founding, working_relationship).")
    tags_raw = prompt("  tags", "")
    scope_tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    print()
    public = prompt_yes_no("Public (include in public roll)?", True)

    print()
    print("Status — typically 'active' if all parties are forming this together,")
    print("         'proposed' if drafted by one party or scribe pending ratification.")
    status = prompt_choice("  status", VALID_STATUSES, "active")

    proposed_by = ""
    if status == "proposed":
        proposed_by = prompt("Proposed by (drafter name)")

    print()
    print("Witness — git_commit | gathering | paper | recording | other")
    witness_type = prompt("  type", "git_commit")
    witness_ref_default = "this commit" if witness_type == "git_commit" else date_formed
    witness_reference = prompt("  reference", witness_ref_default)

    canonical_record = prompt("Canonical record (file | paper | recording | external | brain)", "file")

    specific: dict[str, list[str]] = {}
    if args.detailed:
        print()
        print("Per-party specific commitments — additional commitments beyond the standard seven.")
        for p in parties:
            specific[p["name"]] = prompt_specific_commitments(p["name"])

    # Build agreement_id from filename slug
    fname = build_filename(date_formed, parties)
    aid = fname.replace(".md", "").lower()

    meta = {
        "agreement_id": aid,
        "date_formed": date_formed,
        "parties": parties,
        "context": context,
        "scope_tags": scope_tags,
        "status": status,
        "public": public,
        "witness_type": witness_type,
        "witness_reference": witness_reference,
        "canonical_record": canonical_record,
    }
    if proposed_by:
        meta["proposed_by"] = proposed_by

    # Render
    out_path = AGREEMENTS_DIR / fname
    if out_path.exists():
        print(f"\nERROR: file already exists at {out_path.relative_to(REPO_ROOT)}")
        print("       (refusing to overwrite — pick a different date or add suffix)")
        return 2

    drafted_by_third_party = bool(proposed_by) and proposed_by not in {p["name"] for p in parties}
    md = build_markdown(meta, specific, drafted_by_third_party)

    # Confirm before writing
    print()
    print("─── PREVIEW ─────────────────────────────────────────────")
    print(f"file:       {out_path.relative_to(REPO_ROOT)}")
    print(f"parties:    {' ↔ '.join(p['name'] for p in parties)}")
    print(f"context:    {context}")
    print(f"status:     {status} · public: {public}")
    print(f"tags:       {', '.join(scope_tags) if scope_tags else '(none)'}")
    print("─────────────────────────────────────────────────────────")

    if not prompt_yes_no("Write this Agreement?", True):
        print("aborted (no file written)")
        return 1

    AGREEMENTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"\n✓ wrote {out_path.relative_to(REPO_ROOT)}")

    if not args.no_regen:
        regenerate_registry(also_public_roll=not args.no_public_roll)

    print()
    print("✓ done. Next steps:")
    print(f"  1. Review the generated file (look for 'TODO' if any).")
    print(f"  2. If status is 'proposed', the named parties must ratify.")
    print(f"  3. git add . && git commit -m 'Form Agreement: …' to preserve.")
    if public and not args.no_public_roll and not args.no_regen:
        print(f"  4. Deploy site to update public roll: ./sites/zenvillage-peace/deploy.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
