#!/usr/bin/env python3
"""Generate a clean FPOS starter-kit template from canonical DNA only."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_DNA = REPO_ROOT / "core" / "STATE" / "MODEL_DNA.md"
DEFAULT_DIST = REPO_ROOT / "dist"
PERSONAL_MARKERS = (
    "james",
    "cora",
    "zen village",
    "full potential game",
    "probe_pool",
    "contact profile",
    "personal_dna",
    "identity/personal",
)


class CellSplitBlocked(PermissionError):
    """Raised when a cell split is not explicitly approved or leaks personal data."""


def approved() -> bool:
    return os.environ.get("CELL_SPLIT_APPROVED") == "1"


def generate_template(
    instance_name: str,
    *,
    output_root: Path | str = DEFAULT_DIST,
    model_dna_path: Path | str = MODEL_DNA,
    approved_override: bool = False,
) -> Path:
    """Create a starter kit that excludes personal DNA and James-specific state."""
    if not (approved_override or approved()):
        raise CellSplitBlocked("CELL_SPLIT_APPROVED=1 is required for template export")
    safe_name = _safe_name(instance_name)
    date = dt.datetime.utcnow().strftime("%Y%m%d")
    target = Path(output_root) / f"fpos_template_{date}_{safe_name}"
    target.mkdir(parents=True, exist_ok=True)

    model_dna = Path(model_dna_path)
    if not model_dna.exists():
        raise FileNotFoundError(model_dna)
    canonical = sanitize_model_dna(model_dna.read_text(encoding="utf-8"))
    manifest = {
        "instance_name": instance_name,
        "created_at": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "transfers": [
            "core/STATE/MODEL_DNA.md",
            "canonical routing heuristics",
            "quality-signal weighting rules",
            "cell-split privacy manifest",
        ],
        "stripped": [
            "identity/PERSONAL_DNA.md",
            "founder correction history",
            "relationships and contact profiles",
            "probe_pool and outreach data",
            "domain-specific vocabulary and decisions",
        ],
        "weights": "canonical weights only; no personal adapter bundle included by this repo build",
    }

    (target / "core" / "STATE").mkdir(parents=True, exist_ok=True)
    (target / "core" / "STATE" / "MODEL_DNA.md").write_text(canonical, encoding="utf-8")
    (target / "README.md").write_text(_readme(instance_name), encoding="utf-8")
    (target / "cell_split_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (target / "config.example.env").write_text(
        "LEARNING_ENABLED=0\nFINETUNE_APPROVED=0\nCELL_SPLIT_APPROVED=0\nOLLAMA_ACTIVE_MODEL=llama3.1:8b\n",
        encoding="utf-8",
    )

    leaks = scan_for_personal_markers(target)
    if leaks:
        shutil.rmtree(target)
        raise CellSplitBlocked("personal markers found in template: " + ", ".join(leaks[:10]))
    return target


def scan_for_personal_markers(root: Path | str, *, markers: Iterable[str] = PERSONAL_MARKERS) -> list[str]:
    lowered_markers = tuple(marker.lower() for marker in markers)
    leaks: list[str] = []
    for path in sorted(Path(root).rglob("*")):
        if not path.is_file():
            continue
        if path.name == "cell_split_manifest.json":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for marker in lowered_markers:
            if marker in text:
                leaks.append(f"{path.relative_to(root)}:{marker}")
    return leaks


def sanitize_model_dna(text: str) -> str:
    """Remove source-instance personal names while preserving canonical lessons."""
    replacements = {
        "James's": "the source instance's",
        "James": "the source instance",
        "CORA, Zen Village, Full Potential Game": "source-instance domain vocabulary",
        "CORA, Zen Village, etc.": "source-instance domain vocabulary",
        "CORA": "source-instance domain",
        "Zen Village": "source-instance place",
        "Full Potential Game": "source-instance game",
        "probe_pool": "source-instance outreach pool",
        "Contact profiles": "Relationship profiles",
        "contact profiles": "relationship profiles",
    }
    cleaned = text
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    return cleaned


def _safe_name(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip()).strip("-").lower()
    return safe or "instance"


def _readme(instance_name: str) -> str:
    return f"""# FPOS Starter Kit — {instance_name}

This template contains canonical FPOS learning DNA only. It intentionally omits
personal corrections, relationships, contact data, and founder-specific operating
history. Start from `core/STATE/MODEL_DNA.md`, then build a new personal layer
inside the receiving instance.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a gated FPOS cell-split template.")
    parser.add_argument("instance_name")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_DIST)
    parser.add_argument("--model-dna", type=Path, default=MODEL_DNA)
    parser.add_argument("--approve-for-test", action="store_true", help="Test-only override; do not use for live exports")
    args = parser.parse_args(argv)

    target = generate_template(
        args.instance_name,
        output_root=args.output_root,
        model_dna_path=args.model_dna,
        approved_override=args.approve_for_test,
    )
    print(json.dumps({"ok": True, "template": str(target), "leaks": scan_for_personal_markers(target)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
