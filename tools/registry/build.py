#!/usr/bin/env python3
"""
Build the read-only Service Registry / World Map.

Scans SERVICES/* and writes docs/codex/SERVICE_REGISTRY.md.
No service files are modified.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "SERVICES"
REPORT = ROOT / "docs" / "codex" / "SERVICE_REGISTRY.md"
MAX_HINT_LEN = 96


@dataclass
class ServiceRow:
    name: str
    status: str
    status_reason: str
    last_touched: str
    age_days: int | None
    has_systemd_unit: bool
    unit_paths: list[str]
    deploy_target: str
    cost_hint: str
    kill_condition: str
    notes: str


def run_git(args: list[str]) -> str:
    try:
        out = subprocess.check_output(
            ["git", *args],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return ""
    return out.strip()


def iso_now() -> dt.datetime:
    forced = os.environ.get("FPAI_SERVICE_REGISTRY_NOW")
    if forced:
        try:
            parsed = dt.datetime.fromisoformat(forced)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=dt.timezone.utc)
            return parsed
        except ValueError:
            pass
    return dt.datetime.now(dt.timezone.utc)


def service_dirs() -> list[Path]:
    if not SERVICES.exists():
        return []
    return sorted((p for p in SERVICES.iterdir() if p.is_dir()), key=lambda p: p.name.lower())


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def markdown_escape(value: str) -> str:
    value = value.replace("\n", " ").replace("\r", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value.replace("|", "\\|")


def redact(value: str) -> str:
    value = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[redacted-ip]", value)
    value = re.sub(
        r"(?i)\b([A-Z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|PASS|CREDENTIAL)[A-Z0-9_]*)\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s]+)",
        lambda m: f"{m.group(1)}=[redacted]",
        value,
    )
    return value


def shorten(value: str, fallback: str = "—") -> str:
    value = markdown_escape(redact(value))
    if not value:
        return fallback
    if len(value) <= MAX_HINT_LEN:
        return value
    return value[: MAX_HINT_LEN - 1].rstrip() + "…"


def last_commit(path: Path) -> tuple[str, int | None]:
    raw = run_git(["log", "-1", "--format=%cI", "--", rel(path)])
    if not raw:
        return "❓ no git signal", None
    try:
        when = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        age = (iso_now() - when).days
        return when.date().isoformat(), max(age, 0)
    except ValueError:
        return raw[:10], None


def metadata_files(path: Path) -> list[Path]:
    names = {
        "README.md",
        "README_OLD.md",
        "package.json",
        "pyproject.toml",
        "docker-compose.yml",
        "docker-compose.yaml",
        "Dockerfile",
        "Procfile",
        "vercel.json",
        "wrangler.toml",
        "fly.toml",
        "app.json",
    }
    out: list[Path] = []
    for child in sorted(path.iterdir(), key=lambda p: p.name.lower()):
        if child.is_file() and child.name in names:
            out.append(child)
    return out


def safe_read_text(path: Path, limit: int = 80_000) -> str:
    try:
        data = path.read_text(errors="ignore")
    except Exception:
        return ""
    return data[:limit]


def service_units(path: Path) -> list[Path]:
    return sorted(path.rglob("*.service"), key=lambda p: rel(p).lower())


def find_first_line(text: str, patterns: list[str]) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if not line or len(line) > 220:
            continue
        lowered = line.lower()
        if any(p in lowered for p in patterns):
            return line
    return ""


def package_hint(path: Path) -> tuple[str, str]:
    pkg = path / "package.json"
    if not pkg.exists():
        return "", ""
    try:
        data = json.loads(pkg.read_text(errors="ignore"))
    except Exception:
        return "", ""
    scripts = data.get("scripts") or {}
    deps = set((data.get("dependencies") or {}).keys())
    deps.update((data.get("devDependencies") or {}).keys())
    deploy = ""
    if "start" in scripts:
        deploy = f"npm start: {scripts['start']}"
    elif "dev" in scripts:
        deploy = f"npm dev: {scripts['dev']}"
    notes = []
    for key in ("next", "vite", "express", "fastify", "@vercel/node"):
        if key in deps:
            notes.append(key)
    return deploy, ", ".join(notes)


def extract_hints(path: Path) -> tuple[str, str, str, str]:
    deploy_target = ""
    cost_hint = ""
    kill_condition = ""
    notes: list[str] = []

    pkg_deploy, pkg_notes = package_hint(path)
    if pkg_deploy:
        deploy_target = pkg_deploy
    if pkg_notes:
        notes.append(pkg_notes)

    for meta in metadata_files(path):
        text = safe_read_text(meta)
        if not text:
            continue
        if not deploy_target:
            deploy_target = find_first_line(
                text,
                ["https://", "http://", "localhost:", "port ", "deploy", "vercel", "fly.io", "wpengine"],
            )
        if not cost_hint:
            cost_hint = find_first_line(text, ["cost", "$", "billing", "price", "monthly", "/mo"])
        if not kill_condition:
            kill_condition = find_first_line(
                text,
                ["kill condition", "retire", "archive", "delete when", "stop when", "pause when"],
            )
        if meta.name.lower().startswith("readme"):
            notes.append(f"readme:{meta.name}")

    if (path / "docker-compose.yml").exists() or (path / "docker-compose.yaml").exists():
        notes.append("docker-compose")
    if (path / "Dockerfile").exists():
        notes.append("Dockerfile")
    if (path / "pyproject.toml").exists():
        notes.append("python")

    return (
        shorten(deploy_target),
        shorten(cost_hint),
        shorten(kill_condition),
        shorten(", ".join(dict.fromkeys(n for n in notes if n))),
    )


def classify(name: str, age_days: int | None, unit_paths: list[str], hints: tuple[str, str, str, str]) -> tuple[str, str]:
    deploy_target, _cost_hint, kill_condition, notes = hints
    joined = " ".join([deploy_target, kill_condition, notes]).lower()

    if name.startswith("_"):
        return "❓ needs-human-classify", "template/special directory"
    if "archive" in joined or "retire" in joined:
        return "archived", "metadata says archive/retire"
    if "pause" in joined:
        return "paused", "metadata says pause"
    if unit_paths:
        return "live", "systemd unit present"
    if age_days is None:
        return "❓ needs-human-classify", "no git recency signal"
    if age_days <= 45:
        return "live", f"touched {age_days}d ago"
    if age_days <= 180:
        return "paused", f"touched {age_days}d ago"
    return "archived", f"stale {age_days}d"


def build_rows() -> list[ServiceRow]:
    rows: list[ServiceRow] = []
    for path in service_dirs():
        last, age = last_commit(path)
        units = [rel(p) for p in service_units(path)]
        hints = extract_hints(path)
        status, reason = classify(path.name, age, units, hints)
        rows.append(
            ServiceRow(
                name=path.name,
                status=status,
                status_reason=reason,
                last_touched=last,
                age_days=age,
                has_systemd_unit=bool(units),
                unit_paths=units,
                deploy_target=hints[0],
                cost_hint=hints[1],
                kill_condition=hints[2],
                notes=hints[3],
            )
        )
    return rows


def status_counts(rows: list[ServiceRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    return counts


def retire_candidates(rows: list[ServiceRow]) -> list[ServiceRow]:
    cands = [
        row
        for row in rows
        if row.status == "archived"
        and not row.has_systemd_unit
        and (row.age_days is None or row.age_days >= 180)
    ]
    return sorted(cands, key=lambda r: (r.age_days is None, -(r.age_days or 0), r.name.lower()))[:25]


def render(rows: list[ServiceRow]) -> str:
    now = iso_now()
    counts = status_counts(rows)
    scanned = len(service_dirs())
    count_bits = " · ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    lines = [
        "---",
        "generated: true",
        "source: tools/registry/build.py",
        f"last_generated: {now.strftime('%Y-%m-%d %H:%M %Z')}",
        "edit_policy: regenerate, do not hand-edit",
        "---",
        "",
        "# Service Registry / World Map",
        "",
        "Read-only map of `SERVICES/*`. This report never stops, deletes, archives, deploys, or mutates a service.",
        "",
        "## Summary",
        "",
        f"- Services directory entries scanned: **{scanned}**",
        f"- Registry rows written: **{len(rows)}**",
        f"- Status counts: {count_bits or '—'}",
        "- Safety: report only; cleanup requires a separate James-approved spec.",
        "- Redaction: raw IPs and secret-like env values are redacted in extracted hints.",
        "",
        "## Classification Rules",
        "",
        "- `live`: systemd unit present or touched within 45 days.",
        "- `paused`: no unit, touched within 46-180 days, or metadata says pause.",
        "- `archived`: no unit and stale beyond 180 days, or metadata says archive/retire.",
        "- `❓ needs-human-classify`: template/special directory or missing recency signal.",
        "",
        "## Obvious Retire-Candidates",
        "",
    ]
    cands = retire_candidates(rows)
    if cands:
        for row in cands:
            age = f"{row.age_days}d stale" if row.age_days is not None else "no age signal"
            lines.append(f"- `{row.name}` — {age}; reason: {row.status_reason}")
    else:
        lines.append("- None from the current rules.")

    lines.extend(
        [
            "",
            "## Registry",
            "",
            "| Service | Status | Last touched | Systemd unit | URL/deploy target | Cost hint | Kill condition | Notes |",
            "|---|---|---:|---|---|---|---|---|",
        ]
    )
    for row in rows:
        unit = "yes" if row.has_systemd_unit else "no"
        if row.has_systemd_unit:
            unit = "yes: " + shorten(", ".join(row.unit_paths), fallback="yes")
        notes = "; ".join(part for part in [row.status_reason, row.notes] if part and part != "—")
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{markdown_escape(row.name)}`",
                    markdown_escape(row.status),
                    markdown_escape(row.last_touched),
                    markdown_escape(unit),
                    row.deploy_target,
                    row.cost_hint,
                    row.kill_condition,
                    shorten(notes),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    rows = build_rows()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render(rows))
    counts = status_counts(rows)
    print(
        f"service-registry: wrote {rel(REPORT)} "
        f"rows={len(rows)} scanned={len(service_dirs())} counts={counts}"
    )
    if len(rows) != len(service_dirs()):
        print("ERROR: row count does not reconcile with SERVICES/* directories")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
