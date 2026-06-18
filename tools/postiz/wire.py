"""Repo-side Postiz MCP wiring and dry-run scheduling payloads.

This module deliberately does not call Postiz. Live scheduling is a public-send
edge and stays behind the activation/proof handoff.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
from pathlib import Path
from typing import Any


POSTIZ_MCP_TOOLS = (
    "integrationList",
    "groupList",
    "integrationSchema",
    "triggerTool",
    "schedulePostTool",
    "generateImageTool",
    "generateVideoOptions",
    "videoFunctionTool",
    "generateVideoTool",
)

SAFE_POST_TYPES = {"draft", "schedule", "now"}
_UTC_Z_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")


def normalize_base_url(base_url: str) -> str:
    base = base_url.strip().rstrip("/")
    if not base.startswith(("https://", "http://")):
        raise ValueError("Postiz base URL must include http:// or https://")
    return base


def mcp_url(base_url: str, api_key_ref: str | None = None) -> str:
    base = normalize_base_url(base_url)
    if api_key_ref:
        return f"{base}/mcp/{api_key_ref.strip()}"
    return f"{base}/mcp"


def mcp_config_fragment(
    *,
    base_url: str,
    server_name: str = "postiz",
    api_key_ref: str = "${POSTIZ_API_KEY}",
) -> dict[str, Any]:
    return {
        "mcpServers": {
            server_name: {
                "url": mcp_url(base_url, api_key_ref),
                "transport": "http",
                "notes": "Replace POSTIZ_API_KEY with the self-hosted Postiz Public API key from Settings > Developers > Public API.",
            }
        }
    }


def _parse_utc_z(value: str) -> str:
    candidate = value.strip()
    if not _UTC_Z_RE.match(candidate):
        raise ValueError("date must be a UTC ISO timestamp ending in Z")
    normalized = candidate.replace("Z", "+00:00")
    parsed = dt.datetime.fromisoformat(normalized)
    if parsed.tzinfo != dt.timezone.utc:
        raise ValueError("date must be UTC")
    return candidate


def html_paragraphs(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("post content cannot be empty")
    return "".join(f"<p>{html.escape(line)}</p>" for line in lines)


def default_settings(platform: str) -> list[dict[str, Any]]:
    platform_key = platform.lower().strip()
    if platform_key in {"x", "twitter"}:
        return [{"key": "who_can_reply_post", "value": "everyone"}]
    return []


def schedule_post_payload(
    *,
    integration_id: str,
    platform: str,
    content: str,
    date: str,
    post_type: str = "schedule",
    is_premium: bool = False,
    short_link: bool = False,
    settings: list[dict[str, Any]] | None = None,
    attachments: list[str] | None = None,
) -> dict[str, Any]:
    post_type = post_type.strip()
    if post_type not in SAFE_POST_TYPES:
        raise ValueError(f"post_type must be one of {sorted(SAFE_POST_TYPES)}")
    if not integration_id.strip():
        raise ValueError("integration_id is required")
    payload = {
        "socialPost": [
            {
                "integrationId": integration_id.strip(),
                "isPremium": bool(is_premium),
                "date": _parse_utc_z(date),
                "shortLink": bool(short_link),
                "type": post_type,
                "postsAndComments": [
                    {
                        "content": html_paragraphs(content),
                        "attachments": list(attachments or []),
                    }
                ],
                "settings": list(settings if settings is not None else default_settings(platform)),
            }
        ]
    }
    validate_schedule_payload(payload)
    return payload


def validate_schedule_payload(payload: dict[str, Any]) -> None:
    posts = payload.get("socialPost")
    if not isinstance(posts, list) or not posts:
        raise ValueError("payload.socialPost must be a non-empty list")
    for post in posts:
        if post.get("type") not in SAFE_POST_TYPES:
            raise ValueError("payload contains an invalid post type")
        _parse_utc_z(str(post.get("date", "")))
        content_items = post.get("postsAndComments")
        if not isinstance(content_items, list) or not content_items:
            raise ValueError("postsAndComments must be a non-empty list")
        for item in content_items:
            content = str(item.get("content", ""))
            lowered = content.lower()
            if "<script" in lowered or "javascript:" in lowered:
                raise ValueError("unsafe HTML is not allowed in post content")
            if "<p>" not in lowered:
                raise ValueError("Postiz MCP content should use paragraph HTML")


def _write_json(path: Path | None, obj: dict[str, Any]) -> None:
    text = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    if path:
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def _cmd_mcp_config(args: argparse.Namespace) -> int:
    _write_json(
        args.output,
        mcp_config_fragment(
            base_url=args.base_url,
            server_name=args.server_name,
            api_key_ref=args.api_key_ref,
        ),
    )
    return 0


def _cmd_payload(args: argparse.Namespace) -> int:
    _write_json(
        args.output,
        schedule_post_payload(
            integration_id=args.integration_id,
            platform=args.platform,
            content=args.content,
            date=args.date,
            post_type=args.post_type,
            is_premium=args.is_premium,
            short_link=args.short_link,
        ),
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    config = sub.add_parser("mcp-config", help="emit a Postiz MCP config fragment")
    config.add_argument("--base-url", required=True)
    config.add_argument("--server-name", default="postiz")
    config.add_argument("--api-key-ref", default="${POSTIZ_API_KEY}")
    config.add_argument("--output", type=Path)
    config.set_defaults(func=_cmd_mcp_config)

    payload = sub.add_parser("schedule-payload", help="emit a dry-run schedulePostTool payload")
    payload.add_argument("--integration-id", required=True)
    payload.add_argument("--platform", required=True)
    payload.add_argument("--content", required=True)
    payload.add_argument("--date", required=True)
    payload.add_argument("--post-type", default="schedule", choices=sorted(SAFE_POST_TYPES))
    payload.add_argument("--is-premium", action="store_true")
    payload.add_argument("--short-link", action="store_true")
    payload.add_argument("--output", type=Path)
    payload.set_defaults(func=_cmd_payload)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

