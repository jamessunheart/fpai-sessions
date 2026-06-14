"""High-level system state endpoints backed by SSOT markdown files."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter


router = APIRouter(prefix="/state", tags=["State"])


def _read_file_safe(path: Path) -> str:
    """Read a text file if it exists, otherwise return empty string."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _parse_current_priority(md: str) -> Dict[str, Any]:
    """Extract the current priority block from CURRENT_STATE markdown."""
    if not md:
        return {}

    lines = md.splitlines()
    data: Dict[str, Any] = {}

    # Top-level metadata
    for line in lines[:10]:
        if line.startswith("**Last Updated:**"):
            data["last_updated"] = line.split("**Last Updated:**", 1)[1].strip().strip()
        if line.startswith("**System Status:**"):
            data["system_status"] = line.split("**System Status:**", 1)[1].strip().strip()

    # Current priority section
    in_priority = False
    notes: list[str] = []
    for line in lines:
        if line.startswith("## 🎯 CURRENT PRIORITY"):
            in_priority = True
            continue
        if in_priority and line.startswith("## "):
            # Next top-level section, stop
            break
        if not in_priority:
            continue

        stripped = line.strip()

        if stripped.startswith("### Priority:"):
            data["title"] = stripped.replace("### Priority:", "", 1).strip()
            continue
        if stripped.startswith("**Status:**"):
            data["status"] = stripped.replace("**Status:**", "", 1).strip(" *")
            continue
        if stripped.startswith("**Why:**"):
            data["why"] = stripped.replace("**Why:**", "", 1).strip(" *")
            continue
        if stripped.startswith("**Timeline:**"):
            data["timeline"] = stripped.replace("**Timeline:**", "", 1).strip(" *")
            continue
        if stripped.startswith("**Owner:**"):
            data["owner"] = stripped.replace("**Owner:**", "", 1).strip(" *")
            continue
        if stripped.startswith("**Next Action:**"):
            data["next_action"] = stripped.replace("**Next Action:**", "", 1).strip(" *")
            continue
        # Collect bullet notes under "Ready to Execute" etc. (lightweight, human-facing)
        if stripped.startswith("- "):
            notes.append(stripped[2:])

    if notes:
        data["notes"] = notes

    return data


def _parse_assembly_line(md: str) -> Dict[str, Any]:
    """Parse the assembly line markdown into simple stage statuses."""
    if not md:
        return {}

    lines = md.splitlines()
    stages: Dict[str, Dict[str, Any]] = {}
    current_stage_key: str | None = None

    for line in lines:
        stripped = line.strip()

        # Headline JSON-style summary
        if stripped.startswith("> **Last Audit:**"):
            stages["last_audit_raw"] = stripped
            continue

        # Detect section headers like "## 1. TRAFFIC (Inbound)"
        if stripped.startswith("## 1. TRAFFIC"):
            current_stage_key = "traffic"
            stages[current_stage_key] = {}
            continue
        if stripped.startswith("## 2. STOREFRONT"):
            current_stage_key = "storefront"
            stages[current_stage_key] = {}
            continue
        if stripped.startswith("## 3. CHECKOUT"):
            current_stage_key = "checkout"
            stages[current_stage_key] = {}
            continue
        if stripped.startswith("## 4. FULFILLMENT"):
            current_stage_key = "fulfillment"
            stages[current_stage_key] = {}
            continue
        if stripped.startswith("## 5. RETENTION"):
            current_stage_key = "retention"
            stages[current_stage_key] = {}
            continue

        if not current_stage_key:
            continue

        # Parse status / URL / action lines inside a stage
        if stripped.startswith("- **Status:**"):
            stages[current_stage_key]["status"] = (
                stripped.replace("- **Status:**", "", 1).strip()
            )
            continue
        if stripped.startswith("- **URL:**"):
            stages[current_stage_key]["url"] = (
                stripped.replace("- **URL:**", "", 1).strip()
            )
            continue
        if stripped.startswith("- **Action:**"):
            stages[current_stage_key]["action"] = (
                stripped.replace("- **Action:**", "", 1).strip()
            )
            continue

    return stages


def _parse_live_services(md: str) -> Dict[str, Any]:
    """Extract live services section from CURRENT_STATE markdown."""
    if not md:
        return {}

    lines = md.splitlines()
    services: List[str] = []
    server: str | None = None
    in_services_section = False
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("### Live Services"):
            in_services_section = True
            # e.g. "### Live Services (Server: 198.54.123.234)"
            if "Server:" in stripped:
                try:
                    # Grab text after "Server:"
                    server = stripped.split("Server:", 1)[1].strip(" )")
                except Exception:
                    server = None
            continue

        if not in_services_section:
            continue

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        if not in_code_block:
            # Look for "Last Verified" just after the code block
            if stripped.startswith("Last Verified:"):
                return {
                    "server": server,
                    "services": services,
                    "last_verified": stripped.replace("Last Verified:", "", 1).strip(),
                }
            continue

        # Inside code block: capture non-empty lines as-is
        if stripped:
            services.append(stripped)

    # Fallback if we never saw "Last Verified"
    return {
        "server": server,
        "services": services,
        "last_verified": None,
    }


def _parse_coordination(md: str) -> Dict[str, Any]:
    """Parse STATUS_BOARD for sessions and claims."""
    if not md:
        return {}

    lines = md.splitlines()
    data: Dict[str, Any] = {}

    # Header info
    for line in lines[:15]:
        if line.startswith("**Last Updated:**"):
            data["last_updated"] = line.split("**Last Updated:**", 1)[1].strip().strip()
        if line.startswith("**Active Sessions:**"):
            raw = line.split("**Active Sessions:**", 1)[1].strip()
            try:
                data["active_sessions"] = int(raw)
            except ValueError:
                data["active_sessions"] = raw

    # Active claims summary
    in_claims = False
    total_claims = 0
    mission_claims: List[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## 🔒 Active Claims"):
            in_claims = True
            continue
        if in_claims and stripped.startswith("## "):
            break
        if not in_claims:
            continue

        if stripped.startswith("- **"):
            total_claims += 1
            # Pattern: - **mission/M007_i_match** - session-...
            try:
                name = stripped.split("**", 2)[1]
                if name.startswith("mission/"):
                    mission_claims.append(name)
            except Exception:
                continue

    data["active_claims"] = total_claims
    if mission_claims:
        data["mission_claims"] = mission_claims

    return data


def _resolve_workspace_root() -> Path:
    """
    Walk upwards from this file to find the monorepo root.

    We treat the directory containing either a `.git` folder or `docs/coordination`
    as the root. This is more robust than relying on a fixed parent depth.
    """
    current = Path(__file__).resolve().parent
    while current.parent != current:
        if (current / ".git").exists() or (
            current / "docs" / "coordination" / "sessions" / "CURRENT_STATE.md"
        ).exists():
            return current
        current = current.parent
    return current


@router.get(
    "/overview",
    summary="High-level system overview from CURRENT_STATE and ASSEMBLY_LINE",
)
async def get_system_overview() -> Dict[str, Any]:
    """
    Return a simplified, UI-friendly snapshot of the system's current state.

    This endpoint is intentionally read-only and derived from the markdown SSOT:
    - docs/coordination/sessions/CURRENT_STATE.md
    - core/STATE/ASSEMBLY_LINE.md
    """
    workspace_root = _resolve_workspace_root()
    current_state_path = (
        workspace_root / "docs" / "coordination" / "sessions" / "CURRENT_STATE.md"
    )
    assembly_line_path = workspace_root / "core" / "STATE" / "ASSEMBLY_LINE.md"
    status_board_path = workspace_root / "docs" / "coordination" / "STATUS_BOARD.md"

    current_state_md = _read_file_safe(current_state_path)
    assembly_md = _read_file_safe(assembly_line_path)
    status_board_md = _read_file_safe(status_board_path)

    current_priority = _parse_current_priority(current_state_md)
    assembly_line = _parse_assembly_line(assembly_md)
    live_services = _parse_live_services(current_state_md)
    coordination = _parse_coordination(status_board_md)

    return {
        "current_priority": current_priority,
        "assembly_line": assembly_line,
        "live_services": live_services,
        "coordination": coordination,
        "sources": {
            "current_state": str(current_state_path),
            "assembly_line": str(assembly_line_path),
            "status_board": str(status_board_path),
        },
    }


