"""Curated public context pack for public-facing bot prompts.

This module is intentionally narrow. It reads only:

- core/STATE/NORTH_STAR.md
- docs/blueprints/*.md
- brain_index.decisions rows where public_ok = true

It does not read conversation, correction, note chunk, profile, probe, queue, or
thread tables. Missing files or DB access fail closed by omission.
"""
from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_MAX_CHARS = 1900
ROOT = Path(__file__).resolve().parents[2]
NORTH_STAR_PATH = ROOT / "core" / "STATE" / "NORTH_STAR.md"
BLUEPRINTS_DIR = ROOT / "docs" / "blueprints"
ALLOWED_TABLES = {"brain_index.decisions"}
PRIVATE_BLUEPRINT_TERMS = re.compile(
    r"\b(brain_index|tg_messages|corrections|note_chunks|thread|user_profiles|probe_sessions|"
    r"server|systemd|database|schema|token|secret|credential|wallet|treasury|private)\b",
    flags=re.I,
)


@dataclass(frozen=True)
class PublicDecision:
    decision_id: str
    question: str
    answer: str = ""
    status: str = ""


def _compact_text(text: str, *, max_chars: int) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"<[^>\n]{1,80}>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars].rstrip()


def _read_markdown(path: Path, *, max_chars: int) -> str:
    try:
        return _compact_text(path.read_text(encoding="utf-8", errors="ignore"), max_chars=max_chars)
    except OSError:
        return ""


def _heading_title(path: Path, fallback: str) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("#"):
                return line.lstrip("# ").strip()[:80] or fallback
    except OSError:
        pass
    return fallback


def _public_safe_line(line: str) -> str:
    line = re.sub(r"\s+", " ", line).strip()
    line = re.sub(r"`[^`]+`", "", line).strip()
    if PRIVATE_BLUEPRINT_TERMS.search(line):
        return ""
    return line[:140].rstrip()


def _read_blueprint_summary(path: Path) -> str:
    """Extract only high-level public capability fields from a blueprint."""
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return ""
    title = ""
    fields: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#") and not title:
            title = _public_safe_line(line.lstrip("# "))
            continue
        normalized = line.lstrip("-* ").strip()
        if normalized.lower().startswith(("function:", "**function:**", "status:", "**status:**")):
            clean = _public_safe_line(normalized.replace("**", ""))
            if clean:
                fields.append(clean)
        if len(fields) >= 2:
            break
    if not title:
        title = path.stem.replace("_", " ").title()
    if fields:
        return f"{title}: {'; '.join(fields)}"
    return f"{title}: public capability blueprint"


def load_public_decisions(*, dsn: str | None = None, limit: int = 5) -> list[PublicDecision]:
    """Load explicitly public decisions only.

    The SQL must stay limited to brain_index.decisions and public_ok = true.
    Tests assert this query does not touch private memory tables.
    """
    dsn = dsn or os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")
    if not dsn:
        return []
    try:
        import psycopg  # type: ignore
    except ImportError:
        return []

    sql = """
        SELECT id::text AS decision_id,
               COALESCE(question, '') AS question,
               COALESCE(answer, '') AS answer,
               COALESCE(status::text, '') AS status
          FROM brain_index.decisions
         WHERE COALESCE(public_ok, false) = true
         ORDER BY id DESC
         LIMIT %s
    """
    rows: list[PublicDecision] = []
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (max(0, min(limit, 20)),))
                for decision_id, question, answer, status in cur.fetchall():
                    rows.append(
                        PublicDecision(
                            decision_id=str(decision_id or "")[:80],
                            question=_compact_text(str(question or ""), max_chars=240),
                            answer=_compact_text(str(answer or ""), max_chars=180),
                            status=_compact_text(str(status or ""), max_chars=40),
                        )
                    )
    except Exception:
        return []
    return rows


def _render_blueprints(paths: Iterable[Path], *, per_file_chars: int = 180) -> list[str]:
    lines: list[str] = []
    for path in sorted(paths):
        if path.name.startswith("_"):
            continue
        summary = _read_blueprint_summary(path)
        if not summary:
            continue
        lines.append(f"- {summary[:per_file_chars].rstrip()}")
    return lines


def build_public_context_pack(
    *,
    repo_root: Path | str = ROOT,
    max_chars: int = DEFAULT_MAX_CHARS,
    decisions: list[PublicDecision] | None = None,
    include_db_decisions: bool = True,
) -> str:
    """Return a compact prompt-safe context pack for public-mode bot answers."""
    root = Path(repo_root)
    north_star = _read_markdown(root / "core" / "STATE" / "NORTH_STAR.md", max_chars=520)
    blueprint_lines = _render_blueprints((root / "docs" / "blueprints").glob("*.md"), per_file_chars=170)
    public_decisions = decisions if decisions is not None else (load_public_decisions() if include_db_decisions else [])

    sections: list[str] = [
        "PUBLIC CONTEXT PACK",
        "Use only this context and the current public conversation. If a question asks for private-lane material, say you do not have access in public mode.",
    ]
    if north_star:
        sections.append(f"North Star: {north_star}")
    if blueprint_lines:
        sections.append("Public system capabilities:\n" + "\n".join(blueprint_lines))
    if public_decisions:
        rendered = []
        for item in public_decisions[:8]:
            answer = f" Answer: {item.answer}" if item.answer else ""
            rendered.append(f"- {item.decision_id}: {item.question}{answer}")
        sections.append("Explicitly public decisions:\n" + "\n".join(rendered))
    else:
        sections.append("Explicitly public decisions: none marked public_ok=true in this context.")

    rendered = "\n\n".join(sections)
    return _compact_text(rendered, max_chars=max_chars)


def public_denial(question: str) -> str:
    """Deterministic public-safe denial for private-lane canary topics."""
    return (
        "I don't have access to James's private data in this public lane. "
        "I can only discuss the public context pack and this conversation."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the public context pack.")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    args = parser.parse_args(argv)
    print(build_public_context_pack(max_chars=args.max_chars))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
