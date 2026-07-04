"""Helpers for parsing machine-oriented Claude responses."""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any


LogFunc = Callable[[str, str], Any]


def _json_object_from_text(text: str) -> Any:
    """Extract the first balanced JSON object from mixed text."""
    raw = text or ""
    for start, char in enumerate(raw):
        if char != "{":
            continue
        depth = 0
        in_string = False
        escaped = False
        for pos in range(start, len(raw)):
            current = raw[pos]
            if in_string:
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    in_string = False
                continue
            if current == '"':
                in_string = True
            elif current == "{":
                depth += 1
            elif current == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(raw[start : pos + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError("response did not contain a JSON object")


def robust_json(text: str, logger: LogFunc | None = None) -> Any:
    """Parse JSON from model output with progressively looser extraction."""
    raw = text or ""
    errors: list[Exception] = []
    for parser in (
        lambda value: json.loads(value),
        _json_object_from_text,
        lambda value: json.loads(re.search(r"\{.*\}", value, re.DOTALL).group(0)),  # type: ignore[union-attr]
    ):
        try:
            return parser(raw)
        except Exception as exc:
            errors.append(exc)
    if logger:
        logger("debate_parse_fail", f"raw: {raw}")
    raise ValueError("response did not contain valid JSON") from errors[-1]
