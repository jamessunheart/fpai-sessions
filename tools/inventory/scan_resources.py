#!/usr/bin/env python3
"""Scan local resource affordances into core/STATE/AVAILABLE_RESOURCES.md.

The scanner records names and paths only. Environment variable values are never
written, and secret-shaped variable names are omitted entirely.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
from pathlib import Path
from typing import Mapping, Sequence

import pkg_resources

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "core" / "STATE" / "AVAILABLE_RESOURCES.md"
DEFAULT_SCRIPT_ROOT = Path("/opt/fpai")
DEFAULT_CONTEXT_LIMIT = 24_000
CLI_NAMES = (
    "twilio",
    "stripe",
    "brevo",
    "codex",
    "claude",
    "ffmpeg",
    "imagemagick",
    "psql",
    "redis-cli",
    "git",
    "gh",
    "curl",
)
IMAGEMAGICK_ALIASES = ("imagemagick", "magick", "convert")
SECRET_NAME_RE = re.compile(r"(key|secret|token|pass)", re.IGNORECASE)
API_NAME_RE = re.compile(
    r"^(TWILIO|STRIPE|BREVO|ANTHROPIC|OPENAI|GEMINI|GOOGLE|RUNPOD|"
    r"POSTGRES|PG|REDIS|GITHUB|GH|CODEX|CLAUDE|SUPABASE|TELEGRAM|"
    r"TELETHON|SENDGRID|MAILGUN|AWS|S3|SLACK|DISCORD|NOTION|LINEAR|"
    r"OBSIDIAN|AIRTABLE|HUGGINGFACE|HF|OLLAMA|QDRANT|PINECONE|"
    r"CHROMA|BRAIN|COUNCIL|PROBE|OUTREACH|DISCOVERY|FINETUNE|"
    r"BENCHMARKS|RUNWAY|ELEVENLABS)(_|$)",
    re.IGNORECASE,
)
SCRIPT_SUFFIXES = {".py", ".sh", ".bash", ".zsh", ".js", ".ts", ".mjs", ".cjs"}
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cli_path(name: str) -> str | None:
    if name == "imagemagick":
        for alias in IMAGEMAGICK_ALIASES:
            found = shutil.which(alias)
            if found:
                return found if alias == name else f"{found} ({alias})"
        return None
    return shutil.which(name)


def collect_clis(names: Sequence[str] = CLI_NAMES) -> list[tuple[str, str | None]]:
    return [(name, cli_path(name)) for name in names]


def collect_python_libs() -> list[tuple[str, str]]:
    packages = []
    for dist in pkg_resources.working_set:
        packages.append((dist.project_name, dist.version))
    return sorted(packages, key=lambda item: item[0].lower())


def collect_configured_apis(environ: Mapping[str, str] | None = None) -> list[str]:
    environ = os.environ if environ is None else environ
    names = []
    for name, value in environ.items():
        if not value or SECRET_NAME_RE.search(name):
            continue
        if API_NAME_RE.search(name):
            names.append(name)
    return sorted(set(names), key=str.lower)


def should_skip_dir(path: Path) -> bool:
    return path.name in SKIP_DIRS or path.name.startswith(".")


def looks_like_script(path: Path) -> bool:
    if SECRET_NAME_RE.search(str(path)):
        return False
    try:
        if path.suffix.lower() in SCRIPT_SUFFIXES:
            return True
        return os.access(path, os.X_OK) and path.is_file()
    except OSError:
        return False


def collect_local_scripts(root: Path = DEFAULT_SCRIPT_ROOT, *, limit: int = 1000) -> list[str]:
    if not root.exists():
        return []
    scripts: list[str] = []
    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        dirnames[:] = sorted(d for d in dirnames if not should_skip_dir(current_path / d))
        for filename in sorted(filenames):
            path = current_path / filename
            if looks_like_script(path):
                try:
                    scripts.append(str(path.relative_to(root)))
                except ValueError:
                    scripts.append(str(path))
            if len(scripts) >= limit:
                scripts.append(f"... truncated after {limit} entries")
                return scripts
    return scripts


def bullet_lines(values: Sequence[str], *, empty: str) -> list[str]:
    if not values:
        return [f"- {empty}"]
    return [f"- {value}" for value in values]


def render_inventory(
    *,
    generated_at: str,
    clis: Sequence[tuple[str, str | None]],
    python_libs: Sequence[tuple[str, str]],
    configured_apis: Sequence[str],
    local_scripts: Sequence[str],
    script_root: Path,
) -> str:
    lines: list[str] = [
        "# Available Resources",
        "",
        f"_Generated: {generated_at}_",
        "",
        "Names and paths only. Environment variable values are never written; secret-shaped variables are omitted.",
        "",
        "## CLIs",
        "",
    ]
    for name, path in clis:
        status = path if path else "not found"
        lines.append(f"- {name}: {status}")
    lines.extend(["", "## Python-libs", ""])
    if python_libs:
        for name, version in python_libs:
            lines.append(f"- {name}=={version}")
    else:
        lines.append("- none detected")
    lines.extend(["", "## Configured-APIs", ""])
    lines.extend(bullet_lines(configured_apis, empty="none detected"))
    lines.extend(["", "## Local-scripts", "", f"_Root: `{script_root}`_", ""])
    lines.extend(bullet_lines(local_scripts, empty="none detected"))
    lines.append("")
    return "\n".join(lines)


def write_inventory(
    output: Path = DEFAULT_OUTPUT,
    *,
    script_root: Path = DEFAULT_SCRIPT_ROOT,
    environ: Mapping[str, str] | None = None,
) -> str:
    content = render_inventory(
        generated_at=utc_now(),
        clis=collect_clis(),
        python_libs=collect_python_libs(),
        configured_apis=collect_configured_apis(environ),
        local_scripts=collect_local_scripts(script_root),
        script_root=script_root,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return content


def read_inventory_context(path: Path = DEFAULT_OUTPUT, *, limit: int = DEFAULT_CONTEXT_LIMIT) -> str:
    """Return bounded inventory text for proposal prompts."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + f"\n\n... truncated to {limit} chars"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--script-root", type=Path, default=DEFAULT_SCRIPT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    write_inventory(args.output, script_root=args.script_root)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
