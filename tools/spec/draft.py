#!/usr/bin/env python3
"""Draft review-gated Codex specs from buildstream intents.

Generated specs are proposals only. This module never dispatches, builds, or
promotes a draft; humans promote by reviewing and renaming the file.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.apprentice.select import DEFAULT_BUILDSTREAM, load_intents

DEFAULT_SPECS_DIR = REPO_ROOT / "docs" / "codex" / "specs"


class SpecDraftError(RuntimeError):
    """Base error for draft generation failures."""


class SpecAlreadyExistsError(SpecDraftError):
    """Raised when a promoted spec already exists for the slug."""


def slugify(value: str) -> str:
    """Return a stable spec slug from an id or title."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug or "intent"


def draft_path_for(intent: dict[str, Any], specs_dir: Path | str = DEFAULT_SPECS_DIR) -> Path:
    """Return the canonical `.draft.md` path for an intent."""
    ident = str(intent.get("id") or intent.get("ident") or intent.get("title") or "intent")
    return Path(specs_dir) / f"SPEC_{slugify(ident)}.draft.md"


def promoted_path_for(intent: dict[str, Any], specs_dir: Path | str = DEFAULT_SPECS_DIR) -> Path:
    """Return the promoted non-draft spec path that must not be overwritten."""
    ident = str(intent.get("id") or intent.get("ident") or intent.get("title") or "intent")
    return Path(specs_dir) / f"SPEC_{slugify(ident)}.md"


def draft_spec(
    intent: dict[str, Any],
    *,
    specs_dir: Path | str = DEFAULT_SPECS_DIR,
    dry_run: bool = False,
) -> Path:
    """Write a review-gated draft spec and return its path.

    Dry-run returns the intended path without writing. Existing promoted specs
    are never overwritten. Existing drafts are also preserved on real writes so
    review work cannot be silently replaced.
    """
    specs_path = Path(specs_dir)
    promoted = promoted_path_for(intent, specs_path)
    draft = draft_path_for(intent, specs_path)
    if promoted.exists():
        raise SpecAlreadyExistsError(f"promoted spec already exists: {promoted}")
    if draft.exists() and not dry_run:
        raise FileExistsError(f"draft spec already exists: {draft}")
    if dry_run:
        return draft
    specs_path.mkdir(parents=True, exist_ok=True)
    draft.write_text(render_spec(intent), encoding="utf-8")
    return draft


def render_spec(intent: dict[str, Any]) -> str:
    """Render a house-format draft spec body from an intent dictionary."""
    normalized = normalize_intent(intent)
    slug = slugify(normalized["id"])
    title = normalized["title"]
    next_move = normalized["next"]
    stream = normalized["stream"]
    weight = normalized["weight"]
    notes = normalized["notes"]
    dependency = normalized["dependency"]
    landing_target = normalized["landing_target"]

    return f"""# SPEC_{slug}

> DRAFT - review before dispatch.
> This file is a proposal generated from a buildstream intent. Do not auto-dispatch,
> auto-build, kickoff, merge, deploy, move money, touch secrets, or treat it as
> approved until Ember/James reviews and promotes it from `.draft.md` to `.md`.

*Draft generated for intent `{normalized["id"]}` in stream `{stream}`. Weight: {weight}.*

## Source / why
Buildstream intent: **{title}**

Next move from intent:
```text
{next_move}
```

Notes:
```text
{notes}
```

## The three declarations
- **Milestone (DoD):** TODO(review): turn `{next_move}` into one concrete, testable milestone.
- **Dependency:** {dependency}
- **Landing target:** {landing_target}

## Definition of Done
1. TODO(review): name the exact artifact, function, command, or document this spec will produce.
2. TODO(review): list the observable behavior that proves the artifact works.
3. TODO(review): list the narrow test command(s), dry-run command(s), or review checks.
4. TODO(review): confirm no Reserved-Class action is executed by this spec.

## Files
- **Files ALLOWED:** TODO(review): list exact paths or globs the builder may touch.
- **Files FORBIDDEN:** production deploy state; secrets; money movement; public sends; non-draft specs unless explicitly promoted by Ember/James; unrelated refactors.

## Safety
- This draft is not dispatchable until human review promotes it.
- Unknowns stay as `TODO(review):` markers.
- No live autoloop wiring, sends, money movement, deploys, secrets, merges, or approvals.
- If the implementation reaches a Reserved-Class boundary, stop and write a human-edge gate instead of proceeding.

## Tests
- TODO(review): add focused unit tests for the artifact.
- TODO(review): add a dry-run or fixture check that writes no live state.
- `git diff --check` scoped to the allowed files.

## Rollback
- Delete the files created by this future spec.
- Remove any draft/review artifacts it writes.
- Remove this draft if Ember/James rejects it.

## Close-out
- Update `docs/codex/HANDOFF.md` in the Codex -> Ember lane.
- Report files changed, summary, tests, risks, rollback, intent solved, downstream intent unlocked.
- Do not merge or dispatch without James/Ember review.
"""


def normalize_intent(intent: dict[str, Any]) -> dict[str, str]:
    """Coerce intent metadata into explicit reviewable strings."""
    ident = _field(intent, "id", "ident", "title", fallback="TODO(review): assign intent id")
    title = _field(intent, "title", fallback=ident)
    next_move = _field(intent, "next", "next_move", fallback="TODO(review): define next move")
    stream = _field(intent, "stream", fallback="TODO(review): choose stream")
    weight = _field(intent, "weight", "value", fallback="TODO(review): set weight")
    notes = _field(intent, "notes", "why", "source", fallback="TODO(review): add source notes")
    dependency = _field(
        intent,
        "dependency",
        "depends_on",
        fallback="TODO(review): confirm dependency before build",
    )
    landing_target = _field(
        intent,
        "landing_target",
        "branch",
        fallback="TODO(review): choose landing target branch; never main without explicit review",
    )
    return {
        "id": ident,
        "title": title,
        "next": next_move,
        "stream": stream,
        "weight": weight,
        "notes": notes,
        "dependency": dependency,
        "landing_target": landing_target,
    }


def find_intent(intent_id: str, buildstream_path: Path | str = DEFAULT_BUILDSTREAM) -> dict[str, Any]:
    """Load one intent by id from the pipe-style buildstream."""
    for intent in load_intents(buildstream_path):
        if str(intent.get("id")) == intent_id:
            return intent
    raise KeyError(f"intent not found: {intent_id}")


def _field(intent: dict[str, Any], *keys: str, fallback: str) -> str:
    for key in keys:
        value = intent.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return fallback


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Draft a review-gated SPEC_*.draft.md from an intent.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--intent-json", help="JSON object with id/title/next metadata")
    source.add_argument("--id", dest="intent_id", help="intent id to load from the buildstream")
    parser.add_argument("--buildstream", type=Path, default=DEFAULT_BUILDSTREAM)
    parser.add_argument("--specs-dir", type=Path, default=DEFAULT_SPECS_DIR)
    parser.add_argument("--dry-run", action="store_true", help="perform checks and print target; write nothing")
    parser.add_argument("--print-content", action="store_true", help="print rendered draft content")
    parser.add_argument("--json", action="store_true", help="print machine-readable result")
    args = parser.parse_args(argv)

    intent = json.loads(args.intent_json) if args.intent_json else find_intent(args.intent_id, args.buildstream)
    path = draft_spec(intent, specs_dir=args.specs_dir, dry_run=args.dry_run)
    payload = {
        "path": str(path),
        "dry_run": args.dry_run,
        "wrote": not args.dry_run,
        "intent_id": intent.get("id") or intent.get("ident") or intent.get("title"),
    }
    if args.print_content:
        payload["content"] = render_spec(intent)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        action = "would write" if args.dry_run else "wrote"
        print(f"{action}: {path}")
        if args.print_content:
            print(render_spec(intent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
