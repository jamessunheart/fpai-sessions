#!/usr/bin/env python3
"""Build a deterministic, read-only Current Reality Card.

This tool is deliberately a lens, not an authority. It performs literal evidence
checks and exact comparisons of curator-supplied normalized values. It does not
attempt semantic contradiction detection and has no actuation path.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DIMENSIONS = {
    "freshness": {"fresh", "stale"},
    "agreement": {"clear", "conflict", "unknown"},
    "evidence": {"verified", "claimed", "none"},
}


class ManifestError(ValueError):
    """Raised when the explicit card manifest is unsafe or invalid."""


def parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ManifestError(f"invalid ISO-8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ManifestError(f"timestamp must include a timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def resolve_source(repo_root: Path, relative: str) -> Path:
    if not relative or Path(relative).is_absolute():
        raise ManifestError(f"source must be repo-relative: {relative!r}")
    root = repo_root.resolve()
    source = (root / relative).resolve()
    try:
        source.relative_to(root)
    except ValueError as exc:
        raise ManifestError(f"source escapes repository: {relative!r}") from exc
    if not source.is_file():
        raise ManifestError(f"source does not exist: {relative!r}")
    return source


def evidence_rollup(states: list[str]) -> str:
    if states and all(state == "verified" for state in states):
        return "verified"
    if any(state in {"verified", "claimed"} for state in states):
        return "claimed"
    return "none"


def build_card(manifest: dict[str, Any], repo_root: Path, as_of: datetime) -> dict[str, Any]:
    card = manifest.get("card")
    if not isinstance(card, dict):
        raise ManifestError("manifest.card must be an object")
    if card.get("authority") != "lens_only" or card.get("actuation") is not False:
        raise ManifestError("card must declare authority=lens_only and actuation=false")

    fresh_hours = manifest.get("fresh_hours")
    if not isinstance(fresh_hours, (int, float)) or fresh_hours <= 0:
        raise ManifestError("fresh_hours must be a positive number")

    topics = manifest.get("topics")
    if not isinstance(topics, list) or not topics:
        raise ManifestError("manifest.topics must be a non-empty list")

    rendered_topics: list[dict[str, Any]] = []
    for topic in topics:
        observations = topic.get("observations") if isinstance(topic, dict) else None
        if not isinstance(observations, list) or not observations:
            raise ManifestError("each topic needs at least one observation")
        rendered_observations = []
        verified_values: set[str] = set()
        freshness_states: list[str] = []
        evidence_states: list[str] = []

        for observation in observations:
            required = {"id", "value", "source", "source_updated_at", "evidence_text"}
            if not isinstance(observation, dict) or not required.issubset(observation):
                raise ManifestError(f"observation missing fields: {sorted(required)}")
            source = resolve_source(repo_root, str(observation["source"]))
            source_bytes = source.read_bytes()
            source_text = source_bytes.decode("utf-8")
            evidence_text = str(observation["evidence_text"])
            evidence = "verified" if evidence_text in source_text else "none"
            observed_at = parse_time(str(observation["source_updated_at"]))
            age_hours = max(0.0, (as_of - observed_at).total_seconds() / 3600)
            freshness = "fresh" if age_hours <= float(fresh_hours) else "stale"
            normalized_value = json.dumps(observation["value"], sort_keys=True)
            if evidence == "verified":
                verified_values.add(normalized_value)
            freshness_states.append(freshness)
            evidence_states.append(evidence)
            rendered_observations.append(
                {
                    "age_hours": round(age_hours, 2),
                    "evidence": evidence,
                    "evidence_text": evidence_text,
                    "freshness": freshness,
                    "id": observation["id"],
                    "source": observation["source"],
                    "source_sha256": digest_bytes(source_bytes),
                    "source_updated_at": observed_at.isoformat().replace("+00:00", "Z"),
                    "value": observation["value"],
                }
            )

        if len(verified_values) > 1:
            agreement = "conflict"
        elif len(verified_values) == 1 and all(state == "verified" for state in evidence_states):
            agreement = "clear"
        else:
            agreement = "unknown"
        freshness = "fresh" if freshness_states and all(v == "fresh" for v in freshness_states) else "stale"
        evidence = evidence_rollup(evidence_states)
        rendered_topics.append(
            {
                "agreement": agreement,
                "evidence": evidence,
                "freshness": freshness,
                "id": topic.get("id"),
                "observations": rendered_observations,
                "title": topic.get("title"),
            }
        )

    summary = {
        dimension: {state: 0 for state in sorted(states)}
        for dimension, states in DIMENSIONS.items()
    }
    for topic in rendered_topics:
        for dimension in DIMENSIONS:
            summary[dimension][topic[dimension]] += 1

    return {
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "card": card,
        "contract": {
            "actuation": False,
            "authority": "lens_only",
            "comparison": "exact_normalized_values_only",
            "semantic_detection": False,
        },
        "summary": summary,
        "topics": rendered_topics,
    }


def render_html(card: dict[str, Any]) -> str:
    payload = stable_json(card).rstrip()
    safe_payload = payload.replace("</", "<\\/")
    rows = []
    for topic in card["topics"]:
        observations = "".join(
            "<li><strong>{}</strong><span>{}</span><small>{} · {} · {}</small></li>".format(
                html.escape(str(item["value"])),
                html.escape(item["evidence_text"]),
                html.escape(item["source"]),
                item["freshness"],
                item["evidence"],
            )
            for item in topic["observations"]
        )
        escaped = {
            key: html.escape(str(topic[key]))
            for key in ("agreement", "freshness", "evidence", "id", "title")
        }
        rows.append(
            '<article class="topic" data-agreement="{agreement}">'
            '<header><div><p>{title}</p><code>{id}</code></div>'
            '<div class="signals"><b class="{agreement}">{agreement}</b>'
            '<b>{freshness}</b><b>{evidence}</b></div></header><ul>{observations}</ul></article>'.format(
                observations=observations, **escaped
            )
        )
    card_name = html.escape(str(card["card"].get("name", "Twin Eyes")))
    purpose = html.escape(str(card["card"].get("purpose", "")))
    as_of = html.escape(card["as_of"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{card_name} · Current Reality Card</title>
<style>
:root{{--ink:#e9ecf2;--muted:#8d95a5;--line:#2a3040;--panel:#151924;--bg:#090b10;--clear:#55d68b;--conflict:#ffbd4a;--unknown:#aab2c0}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 20% 0,#20283b 0,transparent 33%),var(--bg);color:var(--ink);font:15px/1.45 Inter,ui-sans-serif,system-ui,sans-serif;min-height:100vh}}
main{{width:min(1060px,calc(100% - 32px));margin:32px auto}} .eyebrow{{letter-spacing:.16em;text-transform:uppercase;color:#8fa7d8;font-size:11px}}
h1{{font:600 clamp(34px,6vw,68px)/.95 Georgia,serif;margin:10px 0}} .lede{{max-width:650px;color:var(--muted);font-size:17px}}
.contract{{display:flex;gap:8px;flex-wrap:wrap;margin:24px 0}} .contract b,.signals b{{border:1px solid var(--line);border-radius:999px;padding:6px 10px;font-size:11px;text-transform:uppercase;letter-spacing:.08em}}
.deck{{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(260px,.7fr);gap:18px}} .face{{background:linear-gradient(155deg,#191e2b,#10131b);border:1px solid #31394c;border-radius:22px;padding:22px;box-shadow:0 24px 80px #0008}}
.face h2{{font:500 24px Georgia,serif;margin:0}} .topic{{border-top:1px solid var(--line);padding:18px 0}} .topic header{{display:flex;justify-content:space-between;gap:16px;align-items:start}}
.topic p{{margin:0 0 3px;font-weight:650}} code,small{{color:var(--muted);font-size:11px}} .signals{{display:flex;gap:5px;flex-wrap:wrap;justify-content:flex-end}} .signals .conflict{{color:var(--conflict);border-color:#755b2e}} .signals .clear{{color:var(--clear)}} .signals .unknown{{color:var(--unknown)}}
ul{{list-style:none;margin:12px 0 0;padding:0;display:grid;gap:8px}} li{{display:grid;grid-template-columns:110px 1fr;gap:4px 12px;background:#0c0f16;border-radius:10px;padding:10px 12px}} li strong{{grid-row:1/3;color:#dbe5ff}} li span{{font-size:13px}} li small{{overflow-wrap:anywhere}}
.back dl{{display:grid;grid-template-columns:1fr auto;gap:10px;margin:20px 0}} dt{{color:var(--muted)}} dd{{margin:0;font-weight:700}} .warning{{border-left:3px solid var(--conflict);padding:10px 12px;background:#ffbd4a0d;color:#e9d6b6}}
footer{{color:var(--muted);font-size:12px;margin-top:20px}} @media(max-width:760px){{.deck{{grid-template-columns:1fr}}.topic header{{display:block}}.signals{{justify-content:flex-start;margin-top:8px}}li{{grid-template-columns:1fr}}li strong{{grid-row:auto}}}}
</style></head><body><main>
<p class="eyebrow">Current Reality Envelope · read-only experiment</p><h1>{card_name}</h1><p class="lede">{purpose}</p>
<div class="contract"><b>Lens only</b><b>No authority</b><b>No actuation</b><b>No semantic inference</b></div>
<section class="deck"><div class="face front"><h2>What the sources say</h2>{''.join(rows)}</div>
<aside class="face back"><p class="eyebrow">Card back · stats</p><h2>Known corpus</h2><dl>
<dt>Topics</dt><dd>{len(card['topics'])}</dd><dt>Conflicts</dt><dd>{card['summary']['agreement']['conflict']}</dd><dt>Clear</dt><dd>{card['summary']['agreement']['clear']}</dd><dt>Unknown</dt><dd>{card['summary']['agreement']['unknown']}</dd></dl>
<p class="warning">This card cannot decide, block, route, write, send, deploy, or speak for a source. Open the cited source before acting.</p><footer>As of {as_of} · deterministic exact-value comparison</footer></aside></section>
<script type="application/json" id="twin-eyes-data">{safe_payload}</script>
</main></body></html>
"""


def write_if_requested(path: str | None, content: str) -> None:
    if path:
        Path(path).write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--as-of", required=True, help="Explicit ISO-8601 time; never inferred from the clock")
    parser.add_argument("--json-output")
    parser.add_argument("--html-output")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    card = build_card(manifest, Path(args.repo_root), parse_time(args.as_of))
    json_text = stable_json(card)
    write_if_requested(args.json_output, json_text)
    write_if_requested(args.html_output, render_html(card))
    if not args.json_output:
        print(json_text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
