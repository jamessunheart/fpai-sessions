"""
Service catalog — Priority view.

Scans SERVICES/ on disk, joins to engine-role tags from core/STATE/catalog.json,
returns a cross-system Priority view answering "where should resources go?".
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from app.config import settings
from app.models import EngineRole, PriorityView, ServiceCard

logger = logging.getLogger(__name__)


def _services_root() -> Path:
    return Path(settings.COCKPIT_ROOT) / settings.SERVICES_SUBDIR


def _catalog_path() -> Path:
    return Path(settings.COCKPIT_ROOT) / settings.STATE_SUBDIR / "catalog.json"


def _load_tags() -> Dict[str, str]:
    """Load name -> engine_role tag map from catalog.json"""
    path = _catalog_path()
    if not path.exists():
        logger.warning("catalog.json not found at %s — all services will be UNKNOWN", path)
        return {}
    try:
        data = json.loads(path.read_text())
        return data.get("tags", {})
    except Exception as e:
        logger.error("Failed to read %s: %s", path, e)
        return {}


def _last_touched(service_dir: Path) -> Optional[datetime]:
    """Most recent mtime of any file in the service dir (depth-1 only — fast)"""
    try:
        latest = max(
            (p.stat().st_mtime for p in service_dir.iterdir() if p.is_file()),
            default=None,
        )
        return datetime.fromtimestamp(latest) if latest else None
    except Exception:
        return None


def _read_purpose(service_dir: Path) -> Optional[str]:
    """First non-empty line of SPECS.md / README.md, if present"""
    for fname in ("SPECS.md", "README.md"):
        f = service_dir / fname
        if not f.exists():
            continue
        try:
            for line in f.read_text(errors="ignore").splitlines():
                line = line.strip().lstrip("#").strip()
                if line:
                    return line[:120]
        except Exception:
            pass
    return None


def _cost_lookup() -> Dict[str, float]:
    """Map service-name-ish key -> monthly_usd from ledger.json (best effort)"""
    ledger_path = Path(settings.COCKPIT_ROOT) / settings.STATE_SUBDIR / "ledger.json"
    if not ledger_path.exists():
        return {}
    try:
        data = json.loads(ledger_path.read_text())
        result = {}
        for item in data.get("costs_monthly_usd", []):
            for key in (item.get("id"), item.get("name", "").lower()):
                if key:
                    result[str(key).lower()] = float(item.get("monthly_usd", 0))
        return result
    except Exception as e:
        logger.error("Failed to read ledger.json for cost lookup: %s", e)
        return {}


def _snapshot_path() -> Path:
    return Path(settings.COCKPIT_ROOT) / settings.STATE_SUBDIR / "priority_snapshot.json"


def _load_snapshot() -> Optional[PriorityView]:
    """Fall back to a pre-built snapshot when live scanning isn't possible."""
    path = _snapshot_path()
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text())
        services = [ServiceCard(**s) for s in raw.get("services", [])]
        return PriorityView(
            timestamp=datetime.fromisoformat(raw["timestamp"]) if raw.get("timestamp") else datetime.utcnow(),
            total_services=raw.get("total_services", len(services)),
            by_role=raw.get("by_role", {}),
            services=services,
            decision_filter=raw.get("decision_filter", PriorityView.model_fields["decision_filter"].default),
        )
    except Exception as e:
        logger.error("Failed to load priority snapshot at %s: %s", path, e)
        return None


def dump_snapshot() -> Path:
    """Write the live priority view to disk. Called from a build step on the dev box."""
    view = _build_priority_view_live()
    path = _snapshot_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(view.model_dump_json(indent=2))
    return path


def _build_priority_view_live() -> PriorityView:
    """Live SERVICES/ scan implementation — used by dump_snapshot and as primary path."""
    root = _services_root()
    tags = _load_tags()
    costs = _cost_lookup()

    services: list[ServiceCard] = []
    if not root.exists():
        return PriorityView(total_services=0)

    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name.startswith(".") or name.startswith("_"):
            continue

        role_str = tags.get(name, "unknown")
        try:
            role = EngineRole(role_str)
        except ValueError:
            role = EngineRole.UNKNOWN

        services.append(
            ServiceCard(
                name=name,
                path=str(entry),
                engine_role=role,
                last_touched=_last_touched(entry),
                purpose=_read_purpose(entry),
                monthly_usd=costs.get(name.lower()),
            )
        )

    by_role: Dict[str, int] = {}
    for s in services:
        by_role[s.engine_role.value] = by_role.get(s.engine_role.value, 0) + 1

    role_order = {
        EngineRole.P1: 0,
        EngineRole.P2: 1,
        EngineRole.INFRA: 2,
        EngineRole.UNKNOWN: 3,
        EngineRole.CRUFT: 4,
    }
    services.sort(key=lambda s: (role_order.get(s.engine_role, 99), s.name))

    return PriorityView(
        total_services=len(services),
        by_role=by_role,
        services=services,
    )


def build_priority_view() -> PriorityView:
    """Live scan when SERVICES/ is reachable; otherwise load snapshot."""
    if _services_root().exists():
        return _build_priority_view_live()
    snap = _load_snapshot()
    if snap:
        return snap
    logger.warning("SERVICES root and snapshot both missing — returning empty view")
    return PriorityView(total_services=0)
