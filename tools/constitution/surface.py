#!/usr/bin/env python3
"""Surface the current repo constitution into James's Telegram chat."""
from __future__ import annotations

import argparse
import os
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


DEFAULT_SOURCE_CANDIDATES = (
    "core/INTENT/AGREEMENTS/CONSTITUTION_v1.md",
    "core/knowledge/CONSTITUTION.md",
)
MAX_TELEGRAM_CHARS = 3900


@dataclass(frozen=True)
class ConstitutionSource:
    path: Path
    relative_path: str
    title: str
    text: str


def repo_root_from(path: Path | None = None) -> Path:
    if path is not None:
        return path.resolve()
    env = os.environ.get("FPAI_REPO_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[2]


def _first_markdown_heading(text: str) -> str:
    for line in text.splitlines():
        clean = line.strip()
        if clean.startswith("# "):
            return clean[2:].strip()
    return "Full Potential Constitution"


def resolve_source(repo_root: Path | None = None, source: str | None = None) -> ConstitutionSource:
    root = repo_root_from(repo_root)
    candidates: list[str] = []
    override = (source or os.environ.get("FPAI_CONSTITUTION_PATH", "")).strip()
    if override:
        candidates.append(override)
    candidates.extend(DEFAULT_SOURCE_CANDIDATES)

    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        path = Path(candidate)
        if not path.is_absolute():
            path = root / path
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            rel = str(path)
        return ConstitutionSource(
            path=path,
            relative_path=rel,
            title=_first_markdown_heading(text),
            text=text,
        )
    raise FileNotFoundError("no constitution source found in repo")


def html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def chunk_text(text: str, limit: int = MAX_TELEGRAM_CHARS) -> list[str]:
    if limit < 500:
        raise ValueError("chunk limit must leave room for Telegram headers")
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = paragraph if not current else current + "\n\n" + paragraph
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(paragraph) > limit:
            chunks.append(paragraph[:limit])
            paragraph = paragraph[limit:]
        current = paragraph
    if current:
        chunks.append(current)
    return chunks


def telegram_messages(source: ConstitutionSource, *, limit: int = MAX_TELEGRAM_CHARS) -> list[str]:
    body_limit = max(500, limit - 500)
    body_chunks = chunk_text(source.text, body_limit)
    total = len(body_chunks)
    messages: list[str] = []
    for index, body in enumerate(body_chunks, start=1):
        header = (
            f"<b>{html_escape(source.title)}</b>\n"
            f"<code>{html_escape(source.relative_path)}</code>\n"
            f"<i>Live repo constitution - part {index}/{total}</i>\n\n"
        )
        messages.append(header + "<pre>" + html_escape(body) + "</pre>")
    return messages


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def telegram_credentials(creds_path: Path | None = None) -> tuple[str, str]:
    env_values: dict[str, str] = {}
    default_creds = Path.home() / ".config" / "fpai" / "tg_brain" / "creds.cache"
    path = creds_path or Path(os.environ.get("TG_CREDS", str(default_creds)))
    env_values.update(_load_env_file(path))
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or env_values.get("TELEGRAM_BOT_TOKEN") or ""
    chat_id = (
        os.environ.get("TELEGRAM_CHAT_ID")
        or os.environ.get("OWNER_TG_ID")
        or env_values.get("TELEGRAM_CHAT_ID")
        or env_values.get("OWNER_TG_ID")
        or ""
    )
    return token.strip(), chat_id.strip()


def send_message(token: str, chat_id: str, text: str) -> None:
    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
            "text": text,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        if response.status >= 300:
            raise RuntimeError(f"telegram send failed with HTTP {response.status}")


def surface_to_telegram(
    *,
    repo_root: Path | None = None,
    source: str | None = None,
    send: bool = False,
    creds_path: Path | None = None,
    state_file: Path | None = None,
    force: bool = False,
) -> list[str]:
    constitution = resolve_source(repo_root=repo_root, source=source)
    messages = telegram_messages(constitution)
    if not send:
        return messages
    if state_file and state_file.exists() and not force:
        print(f"constitution surface skipped; already sent marker exists at {state_file}")
        return messages
    token, chat_id = telegram_credentials(creds_path)
    if not token or not chat_id:
        print("constitution surface skipped; Telegram credentials missing")
        return messages
    for message in messages:
        send_message(token, chat_id, message)
    if state_file:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(f"{constitution.relative_path}\n", encoding="utf-8")
    return messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--source", help="Repo-relative constitution source override")
    parser.add_argument("--send", action="store_true", help="Send to Telegram. Default is dry-run.")
    parser.add_argument("--creds", type=Path, help="Telegram creds env file")
    parser.add_argument("--state-file", type=Path, help="One-time send marker")
    parser.add_argument("--force", action="store_true", help="Ignore existing state marker")
    args = parser.parse_args(argv)

    messages = surface_to_telegram(
        repo_root=args.repo_root,
        source=args.source,
        send=args.send,
        creds_path=args.creds,
        state_file=args.state_file,
        force=args.force,
    )
    if not args.send:
        for i, message in enumerate(messages, start=1):
            print(f"--- message {i}/{len(messages)} ---")
            print(message)
    else:
        print(f"constitution surface prepared {len(messages)} Telegram message(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
