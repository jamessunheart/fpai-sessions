#!/usr/bin/env python3
"""Generate traceability + assignment reports for specs.

Outputs:
- specs/_meta/traceability.json : machine-readable mapping
- orchestration/missions/reports/spec_task_report.md : human summary
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
SPECS_DIR = ROOT / "specs"
TRACE_FILE = ROOT / "specs" / "_meta" / "traceability.json"
REPORT_FILE = ROOT / "orchestration" / "missions" / "reports" / "spec_task_report.md"

IMPLEMENTATION_BASES = [
    (Path("agents/services"), "agent_service"),
    (Path("core/applications"), "application"),
    (Path("droplets/claude1"), "droplet_claude1"),
    (Path("droplets/hteam"), "droplet_hteam"),
]

MISSION_DOMAINS = {"coordination", "treasury", "udc"}


def slugify(name: str) -> str:
    return name.lower().replace(" ", "-")


def probable_impl_paths(service_slug: str) -> List[str]:
    paths: List[str] = []
    for base, _ in IMPLEMENTATION_BASES:
        candidate = ROOT / base / service_slug
        if candidate.exists():
            paths.append(str(candidate.relative_to(ROOT)))
    return paths or ["unknown"]


def classify_assignment(domain: str) -> Dict[str, str]:
    if domain in MISSION_DOMAINS:
        return {"assignment": "mission", "reason": f"domain '{domain}' typically needs internal coordination"}
    return {"assignment": "sprint", "reason": f"domain '{domain}' suitable for apprentice sprint work"}


def main() -> None:
    entries = []
    for spec_path in sorted(SPECS_DIR.rglob("*.md")):
        if "_meta" in spec_path.parts:
            continue
        rel = spec_path.relative_to(ROOT)
        parts = rel.parts
        domain = parts[1] if len(parts) > 1 else "unknown"
        service_slug = slugify(parts[-2]) if len(parts) >= 2 else slugify(spec_path.stem)
        impls = probable_impl_paths(service_slug)
        classification = classify_assignment(domain)
        entries.append({
            "spec": str(rel),
            "domain": domain,
            "service_slug": service_slug,
            "probable_impl_paths": impls,
            **classification,
        })

    TRACE_FILE.write_text(json.dumps(entries, indent=2))

    rows = [
        "# Spec → Task Assignment Report",
        "",
        f"Total specs scanned: {len(entries)}",
        "",
        "| Spec | Domain | Assignment | Probable Implementation |",
        "| --- | --- | --- | --- |",
    ]
    for item in entries:
        impl = "<br/>".join(item["probable_impl_paths"])
        rows.append(
            f"| `{item['spec']}` | {item['domain']} | {item['assignment']} | {impl} |")
    REPORT_FILE.write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    main()
