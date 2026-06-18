"""Cognee-compatible graph memory over brain_index.

The live memory substrate already has durable facts in ``brain_index``:
``probe_pool`` contacts, ``becoming`` journey state, corrections, and pgvector
chunks. This module adds relationship tissue without replacing those stores.

Runtime posture:
- default backend is local Postgres graph tables in ``brain_index``;
- if Cognee is installed and ``COGNEE_GRAPH_BACKEND=cognee`` is set, callers can
  route through the same normalized graph records with an explicit backend tag;
- all writes are idempotent upserts and are safe to rerun after every session.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

STAGE_NODE_PREFIX = "stage:"
TOPIC_NODE_PREFIX = "topic:"
PERSON_NODE_PREFIX = "person:"
PROOF_NODE_PREFIX = "proof:"
CORRECTION_NODE_PREFIX = "correction:"

DEFAULT_CONTACT_LIMIT = 10
DEFAULT_BACKEND = "postgres"

_WORD_RE = re.compile(r"[^a-z0-9]+")
_SPLIT_RE = re.compile(r"[,;|/\n]+|\band\b|\+")


@dataclass(frozen=True)
class GraphNode:
    node_type: str
    node_key: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)
    source_table: str | None = None
    source_id: str | None = None


@dataclass(frozen=True)
class GraphEdge:
    from_key: tuple[str, str]
    to_key: tuple[str, str]
    relation: str
    evidence: dict[str, Any] = field(default_factory=dict)
    source_table: str | None = None
    source_id: str | None = None


@dataclass(frozen=True)
class GraphBuild:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]


@dataclass(frozen=True)
class ConnectedPerson:
    person_key: str
    label: str
    stage: str = ""
    platform: str = ""
    handle: str = ""
    distance: int = 1
    via: tuple[str, ...] = ()


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _clean_label(value: Any) -> str:
    text = str(value or "").strip()
    return " ".join(text.split())


def _slug(value: str) -> str:
    cleaned = _WORD_RE.sub("-", value.lower()).strip("-")
    return cleaned or "unknown"


def normalize_topic(value: str) -> str:
    """Normalize human topic text into a stable graph key fragment."""
    value = _clean_label(value)
    value = re.sub(r"\b(cities|city)\b", "cities", value, flags=re.I)
    return _slug(value)


def topic_label(topic_key: str) -> str:
    return topic_key.replace("-", " ").strip().title()


def _person_key(row: dict[str, Any]) -> str:
    platform = _slug(str(row.get("platform") or "unknown"))
    handle = _slug(str(row.get("handle") or row.get("person_id") or row.get("id") or "unknown"))
    return f"{PERSON_NODE_PREFIX}{platform}:{handle}"


def _person_label(row: dict[str, Any]) -> str:
    metadata = _json_dict(row.get("metadata"))
    for key in ("name", "display_name", "first_name"):
        if metadata.get(key):
            return _clean_label(metadata[key])
    handle = _clean_label(row.get("handle"))
    if handle:
        return handle.lstrip("@")
    return f"contact {row.get('id')}"


def extract_topics(row: dict[str, Any]) -> tuple[str, ...]:
    """Extract non-sensitive interest/topic labels from probe metadata."""
    metadata = _json_dict(row.get("metadata"))
    raw: list[str] = []
    for key in ("topic_signal", "source"):
        if row.get(key):
            raw.append(str(row[key]))
    for key in ("topics", "interests", "tags", "shared_interests"):
        value = metadata.get(key)
        if isinstance(value, list):
            raw.extend(str(item) for item in value)
        elif isinstance(value, str):
            raw.append(value)
    topics: list[str] = []
    for item in raw:
        for part in _SPLIT_RE.split(item):
            label = _clean_label(part)
            if len(label) < 3:
                continue
            lowered = label.lower()
            if lowered in {"warm", "adjacent", "cold", "telegram", "email", "github"}:
                continue
            topics.append(normalize_topic(label))
    return tuple(sorted(set(topics)))


def build_contact_graph(
    contact_rows: Sequence[dict[str, Any]],
    becoming_rows: Sequence[dict[str, Any]] = (),
    correction_rows: Sequence[dict[str, Any]] = (),
) -> GraphBuild:
    """Build deterministic nodes/edges from brain_index rows."""
    becoming_by_person = {
        str(row.get("person_id")): row for row in becoming_rows if row.get("person_id")
    }
    nodes: dict[tuple[str, str], GraphNode] = {}
    edges: dict[tuple[tuple[str, str], tuple[str, str], str], GraphEdge] = {}

    def add_node(node: GraphNode) -> None:
        nodes[(node.node_type, node.node_key)] = node

    def add_edge(edge: GraphEdge) -> None:
        edges[(edge.from_key, edge.to_key, edge.relation)] = edge

    contact_by_person_key: dict[str, dict[str, Any]] = {}
    topic_to_people: dict[str, set[str]] = {}

    for row in contact_rows:
        person_key = _person_key(row)
        contact_by_person_key[person_key] = row
        label = _person_label(row)
        metadata = _json_dict(row.get("metadata"))
        person_id = str(row.get("person_id") or person_key)
        becoming = becoming_by_person.get(person_id) or becoming_by_person.get(person_key) or {}
        stage = _clean_label(becoming.get("stage") or metadata.get("stage") or row.get("stage") or "")
        properties = {
            "platform": row.get("platform") or "",
            "handle": row.get("handle") or "",
            "pool": row.get("pool") or "",
            "source": row.get("source") or "",
            "stage": stage,
        }
        add_node(
            GraphNode(
                "person",
                person_key,
                label,
                properties=properties,
                source_table="probe_pool",
                source_id=str(row.get("id") or ""),
            )
        )
        if stage:
            stage_key = f"{STAGE_NODE_PREFIX}{_slug(stage)}"
            add_node(GraphNode("becoming_stage", stage_key, stage, {"stage": stage}))
            add_edge(
                GraphEdge(
                    ("person", person_key),
                    ("becoming_stage", stage_key),
                    "AT_STAGE",
                    {"stage": stage},
                    source_table="becoming",
                    source_id=person_id,
                )
            )
        for topic in extract_topics(row):
            topic_key = f"{TOPIC_NODE_PREFIX}{topic}"
            topic_to_people.setdefault(topic_key, set()).add(person_key)
            add_node(GraphNode("topic", topic_key, topic_label(topic), {"topic": topic}))
            add_edge(
                GraphEdge(
                    ("person", person_key),
                    ("topic", topic_key),
                    "INTERESTED_IN",
                    {"topic": topic, "topic_label": topic_label(topic)},
                    source_table="probe_pool",
                    source_id=str(row.get("id") or ""),
                )
            )

    for topic_key, people in topic_to_people.items():
        for left in sorted(people):
            for right in sorted(people):
                if left == right:
                    continue
                add_edge(
                    GraphEdge(
                        ("person", left),
                        ("person", right),
                        "SHARES_INTEREST_WITH",
                        {"topic_key": topic_key, "topic_label": nodes[("topic", topic_key)].label},
                        source_table="probe_pool",
                    )
                )

    for row in correction_rows:
        conversation_id = _clean_label(row.get("conversation_id"))
        correction_id = _clean_label(row.get("id") or conversation_id)
        if not correction_id:
            continue
        proof_key = f"{CORRECTION_NODE_PREFIX}{_slug(correction_id)}"
        add_node(
            GraphNode(
                "correction",
                proof_key,
                "Correction",
                {
                    "conversation_id": conversation_id,
                    "captured_at": str(row.get("captured_at") or ""),
                },
                source_table="corrections",
                source_id=correction_id,
            )
        )

    return GraphBuild(
        nodes=tuple(sorted(nodes.values(), key=lambda node: (node.node_type, node.node_key))),
        edges=tuple(sorted(edges.values(), key=lambda edge: (edge.from_key, edge.relation, edge.to_key))),
    )


def _topic_keys_for_query(graph: GraphBuild, query: str) -> set[str]:
    query_key = normalize_topic(query)
    keys: set[str] = set()
    for node in graph.nodes:
        if node.node_type != "topic":
            continue
        topic_key = node.node_key.removeprefix(TOPIC_NODE_PREFIX)
        if topic_key == query_key or topic_key in query_key or query_key in topic_key:
            keys.add(node.node_key)
    if not keys:
        keys.add(f"{TOPIC_NODE_PREFIX}{query_key}")
    return keys


def query_connected_people(graph: GraphBuild, topic: str) -> list[ConnectedPerson]:
    """Traverse person -> topic -> related person for an interest query."""
    topic_keys = _topic_keys_for_query(graph, topic)
    nodes = {(node.node_type, node.node_key): node for node in graph.nodes}
    direct_people: set[str] = set()
    related_people: dict[str, set[str]] = {}
    for edge in graph.edges:
        if edge.relation == "INTERESTED_IN" and edge.to_key[0] == "topic" and edge.to_key[1] in topic_keys:
            direct_people.add(edge.from_key[1])
        if edge.relation == "SHARES_INTEREST_WITH" and edge.evidence.get("topic_key") in topic_keys:
            related_people.setdefault(edge.from_key[1], set()).add(edge.to_key[1])

    results: dict[str, ConnectedPerson] = {}
    for person_key in sorted(direct_people):
        node = nodes.get(("person", person_key))
        if not node:
            continue
        props = node.properties or {}
        results[person_key] = ConnectedPerson(
            person_key=person_key,
            label=node.label,
            stage=str(props.get("stage") or ""),
            platform=str(props.get("platform") or ""),
            handle=str(props.get("handle") or ""),
            distance=1,
            via=tuple(sorted(topic_keys)),
        )
        for related_key in sorted(related_people.get(person_key, set())):
            related_node = nodes.get(("person", related_key))
            if not related_node:
                continue
            rprops = related_node.properties or {}
            results.setdefault(
                related_key,
                ConnectedPerson(
                    person_key=related_key,
                    label=related_node.label,
                    stage=str(rprops.get("stage") or ""),
                    platform=str(rprops.get("platform") or ""),
                    handle=str(rprops.get("handle") or ""),
                    distance=2,
                    via=(person_key, *tuple(sorted(topic_keys))),
                ),
            )
    return sorted(results.values(), key=lambda item: (item.distance, item.label.lower()))


async def load_contact_rows(limit: int = DEFAULT_CONTACT_LIMIT) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Read the smallest proof slice from brain_index."""
    try:
        from .db import connect
    except ImportError:
        from db import connect  # type: ignore
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, pool, handle, platform, source, topic_signal, metadata
                  FROM brain_index.probe_pool
                 WHERE COALESCE(do_not_contact, false) = false
                 ORDER BY COALESCE(discovery_score, 0.5) DESC, id ASC
                 LIMIT %s
                """,
                (limit,),
            )
            contact_rows = [dict(zip(("id", "pool", "handle", "platform", "source", "topic_signal", "metadata"), row)) for row in await cur.fetchall()]
            person_ids = [_person_key(row) for row in contact_rows]
            await cur.execute(
                """
                SELECT person_id, stage, stated_intent, proofs, current_blocker, next_nurture_action
                  FROM brain_index.becoming
                 WHERE person_id = ANY(%s)
                """,
                (person_ids,),
            )
            becoming_rows = [
                dict(zip(("person_id", "stage", "stated_intent", "proofs", "current_blocker", "next_nurture_action"), row))
                for row in await cur.fetchall()
            ]
            await cur.execute(
                """
                SELECT id::text, conversation_id, captured_at::text
                  FROM brain_index.corrections
                 ORDER BY captured_at DESC
                 LIMIT 20
                """
            )
            correction_rows = [dict(zip(("id", "conversation_id", "captured_at"), row)) for row in await cur.fetchall()]
    return contact_rows, becoming_rows, correction_rows


async def write_graph(graph: GraphBuild, *, backend: str = DEFAULT_BACKEND, query_proof: dict[str, Any] | None = None) -> dict[str, int]:
    """Upsert graph nodes/edges into brain_index graph tables."""
    try:
        from .db import connect
        from psycopg.types.json import Jsonb
    except ImportError:
        from db import connect  # type: ignore
        from psycopg.types.json import Jsonb  # type: ignore
    async with connect() as conn:
        async with conn.cursor() as cur:
            node_ids: dict[tuple[str, str], str] = {}
            for node in graph.nodes:
                await cur.execute(
                    """
                    INSERT INTO brain_index.graph_memory_nodes
                        (node_type, node_key, label, properties, source_table, source_id, backend, updated_at)
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, NOW())
                    ON CONFLICT (node_type, node_key) DO UPDATE SET
                        label = EXCLUDED.label,
                        properties = EXCLUDED.properties,
                        source_table = EXCLUDED.source_table,
                        source_id = EXCLUDED.source_id,
                        backend = EXCLUDED.backend,
                        updated_at = NOW()
                    RETURNING id::text
                    """,
                    (
                        node.node_type,
                        node.node_key,
                        node.label,
                        Jsonb(node.properties),
                        node.source_table,
                        node.source_id,
                        backend,
                    ),
                )
                row = await cur.fetchone()
                node_ids[(node.node_type, node.node_key)] = row[0]
            edges_written = 0
            for edge in graph.edges:
                from_id = node_ids.get(edge.from_key)
                to_id = node_ids.get(edge.to_key)
                if not from_id or not to_id:
                    continue
                await cur.execute(
                    """
                    INSERT INTO brain_index.graph_memory_edges
                        (from_node_id, to_node_id, relation, evidence, source_table, source_id, backend, updated_at)
                    VALUES (%s::uuid, %s::uuid, %s, %s::jsonb, %s, %s, %s, NOW())
                    ON CONFLICT (from_node_id, to_node_id, relation) DO UPDATE SET
                        evidence = EXCLUDED.evidence,
                        source_table = EXCLUDED.source_table,
                        source_id = EXCLUDED.source_id,
                        backend = EXCLUDED.backend,
                        updated_at = NOW()
                    """,
                    (from_id, to_id, edge.relation, Jsonb(edge.evidence), edge.source_table, edge.source_id, backend),
                )
                edges_written += 1
            await cur.execute(
                """
                INSERT INTO brain_index.graph_memory_runs
                    (backend, contacts_seen, nodes_written, edges_written, query_proof, notes)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                """,
                (
                    backend,
                    len([node for node in graph.nodes if node.node_type == "person"]),
                    len(graph.nodes),
                    edges_written,
                    Jsonb(query_proof or {}),
                    "d098 Cognee graph memory sync",
                ),
            )
    return {"nodes_written": len(graph.nodes), "edges_written": edges_written}


def _backend_name() -> str:
    requested = os.environ.get("COGNEE_GRAPH_BACKEND", DEFAULT_BACKEND).strip().lower()
    if requested != "cognee":
        return DEFAULT_BACKEND
    try:
        __import__("cognee")
    except Exception:
        return DEFAULT_BACKEND
    return "cognee"


async def sync_graph(limit: int = DEFAULT_CONTACT_LIMIT, query: str = "regenerative cities") -> dict[str, Any]:
    contacts, becoming, corrections = await load_contact_rows(limit=limit)
    graph = build_contact_graph(contacts, becoming, corrections)
    results = query_connected_people(graph, query)
    proof = {
        "query": query,
        "contacts_seen": len(contacts),
        "results": [person.__dict__ for person in results],
    }
    backend = _backend_name()
    writes = await write_graph(graph, backend=backend, query_proof=proof)
    return {"backend": backend, **proof, **writes}


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync/query d098 Cognee graph memory over brain_index.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sync = sub.add_parser("sync", help="Read probe/becoming rows and upsert graph tables.")
    sync.add_argument("--limit", type=int, default=DEFAULT_CONTACT_LIMIT)
    sync.add_argument("--query", default="regenerative cities")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.cmd == "sync":
        _print_json(asyncio.run(sync_graph(limit=args.limit, query=args.query)))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
