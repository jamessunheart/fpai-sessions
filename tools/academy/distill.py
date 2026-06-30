#!/usr/bin/env python3
"""Distill proof, correction, outcome, and consequence evidence into ACADEMY.md."""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROOFS = REPO_ROOT / "core" / "INTENT" / "AGREEMENTS" / "proofs"
DEFAULT_CONSEQUENCE = REPO_ROOT / "docs" / "codex" / "CONSEQUENCE_REPORT.md"
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_OUTPUT = REPO_ROOT / "core" / "STATE" / "ACADEMY.md"


@dataclasses.dataclass(frozen=True)
class Evidence:
    kind: str
    title: str
    summary: str
    verdict: str
    source: str
    spec_id: str = ""
    metric_name: str = ""

    def trace(self) -> str:
        return self.source


def distill_academy(
    *,
    proofs_dir: Path = DEFAULT_PROOFS,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    consequence_report: Path = DEFAULT_CONSEQUENCE,
    corrections: Iterable[dict[str, Any]] = (),
    output: Path = DEFAULT_OUTPUT,
) -> str:
    evidence = collect_evidence(
        proofs_dir=proofs_dir,
        ops_ledger=ops_ledger,
        consequence_report=consequence_report,
        corrections=corrections,
    )
    text = render_academy(evidence)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    return text


def collect_evidence(
    *,
    proofs_dir: Path = DEFAULT_PROOFS,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    consequence_report: Path = DEFAULT_CONSEQUENCE,
    corrections: Iterable[dict[str, Any]] = (),
) -> list[Evidence]:
    rows: list[Evidence] = []
    rows.extend(load_proofs(proofs_dir))
    rows.extend(load_feature_outcomes(ops_ledger))
    rows.extend(load_consequence_report(consequence_report))
    rows.extend(evidence_from_corrections(corrections))
    return rows


def load_proofs(path: Path) -> list[Evidence]:
    if not path.exists():
        return []
    evidence: list[Evidence] = []
    for proof in sorted(path.glob("*.md")):
        text = proof.read_text(encoding="utf-8", errors="replace")
        title = _first_heading(text) or proof.stem
        summary = _first_labeled_value(text, ("Intent solved", "intent solved", "Summary", "summary")) or _first_substantive_line(text)
        if not summary:
            continue
        verdict = "improved" if _looks_positive_proof(text) else "unknown"
        evidence.append(Evidence("proof", title, summary, verdict, _rel(proof)))
    return evidence


def load_feature_outcomes(path: Path) -> list[Evidence]:
    evidence: list[Evidence] = []
    for line_no, row in enumerate(_read_jsonl(path), start=1):
        if row.get("event") != "feature_outcome" and row.get("signal_type") != "feature_outcome":
            continue
        spec_id = _clean(row.get("spec_id") or row.get("spec") or row.get("id"))
        metric = _clean(row.get("metric_name") or row.get("metric") or "runtime quality")
        verdict = _feature_verdict(row.get("verdict") or row.get("outcome"))
        if not spec_id:
            continue
        baseline = _clean(row.get("baseline"))
        observed = _clean(row.get("observed"))
        delta = _clean(row.get("delta"))
        summary = f"{metric}: {baseline or 'unknown'} -> {observed or 'unknown'}"
        if delta:
            summary = f"{summary}; delta={delta}"
        evidence.append(
            Evidence(
                "feature_outcome",
                spec_id,
                summary,
                verdict,
                f"{path}:{line_no}",
                spec_id=spec_id,
                metric_name=metric,
            )
        )
    return evidence


def load_consequence_report(path: Path) -> list[Evidence]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    evidence: list[Evidence] = []
    for match in re.finditer(r"^### (?P<title>.+?)\n(?P<body>.*?)(?=^### |\Z)", text, flags=re.M | re.S):
        title = _clean(match.group("title"))
        body = match.group("body")
        verdict = _extract_backtick_label(body, "verdict") or "unknown"
        intent = _extract_label(body, "intent solved") or _first_substantive_line(body)
        if not intent:
            continue
        normalized = "improved" if verdict == "realized" else "regressed" if verdict == "no" else "unknown"
        evidence.append(Evidence("consequence", title, intent, normalized, f"{_rel(path)}#{_anchor(title)}"))
    return evidence


def load_live_corrections(limit: int = 200) -> list[dict[str, Any]]:
    """Read recent brain_index.corrections rows when a DSN/dependency is available."""
    dsn = os.environ.get("BRAIN_INDEX_DSN") or os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        return []
    try:
        import psycopg  # type: ignore
    except ImportError:
        try:
            import psycopg2 as psycopg  # type: ignore
        except ImportError:
            return []
    try:
        with psycopg.connect(dsn) as conn:  # type: ignore[attr-defined]
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT row_to_json(t)
                    FROM (
                      SELECT id::text, conversation_id, original_response,
                             james_correction, captured_at::text
                      FROM brain_index.corrections
                      ORDER BY captured_at DESC
                      LIMIT %s
                    ) AS t
                    """,
                    (limit,),
                )
                return [row[0] for row in cur.fetchall() if isinstance(row[0], dict)]
    except Exception:
        return []


def load_corrections_jsonl(path: Path | None) -> list[dict[str, Any]]:
    return _read_jsonl(path) if path else []


def evidence_from_corrections(rows: Iterable[dict[str, Any]]) -> list[Evidence]:
    evidence: list[Evidence] = []
    for idx, row in enumerate(rows, start=1):
        correction = _clean(_first(row, "james_correction", "corrected_response", "correction", "chosen"))
        original = _clean(_first(row, "original_response", "rejected", "original"))
        if not correction:
            continue
        summary = correction if not original else f"Corrected '{original[:90]}' -> '{correction[:140]}'"
        captured = _clean(row.get("captured_at") or row.get("timestamp") or idx)
        evidence.append(Evidence("correction", f"Correction {idx}", summary, "regressed", f"brain_index.corrections:{captured}"))
    return evidence


def render_academy(evidence: list[Evidence]) -> str:
    improved = [item for item in evidence if item.verdict == "improved"]
    regressed = [item for item in evidence if item.verdict == "regressed"]
    unknown = [item for item in evidence if item.verdict == "unknown"]

    lines = [
        "# Academy",
        "",
        "<!-- AUTO-GENERATED by tools/academy/distill.py. Do not hand-edit. -->",
        "",
        "## Principles (worked)",
        "",
    ]
    if improved:
        for item in improved[:20]:
            lines.append(f"- {principle_text(item)} [evidence: {item.trace()}]")
    else:
        lines.append("- No principles yet. Runtime-improved or consequence-realized evidence is required.")
    lines.extend(["", "## Cautions (regressed)", ""])
    if regressed:
        for item in regressed[:20]:
            lines.append(f"- {caution_text(item)} [evidence: {item.trace()}]")
    else:
        lines.append("- No regressed evidence found.")
    lines.extend(["", "## Playbooks (reusable)", ""])
    playbooks = playbook_lines(improved)
    if playbooks:
        lines.extend(playbooks)
    else:
        lines.append("- No reusable playbooks yet. Add traced improved feature outcomes first.")
    lines.extend(["", "## Evidence Waiting For Stronger Signal", ""])
    if unknown:
        for item in unknown[:20]:
            lines.append(f"- {item.title}: {item.summary} [evidence: {item.trace()}]")
    else:
        lines.append("- None.")
    lines.append("")
    return _ascii("\n".join(lines))


def principle_text(item: Evidence) -> str:
    if item.kind == "feature_outcome":
        return f"Reuse {item.title} only where `{item.metric_name}` can be measured again; observed result: {item.summary}."
    if item.kind == "consequence":
        return f"Treat this consequence pattern as worked: {item.summary}"
    return f"Keep this proven pattern: {item.summary}"


def caution_text(item: Evidence) -> str:
    if item.kind == "feature_outcome":
        return f"Do not generalize {item.title} until `{item.metric_name}` is repaired; observed result: {item.summary}."
    if item.kind == "correction":
        return f"James correction to preserve: {item.summary}"
    return f"Bound or repair this pattern before reuse: {item.summary}"


def playbook_lines(improved: list[Evidence]) -> list[str]:
    lines: list[str] = []
    feature_items = [item for item in improved if item.kind == "feature_outcome"]
    for item in feature_items[:10]:
        lines.append(
            f"- {item.title}: define the metric, record baseline before activation, compare observed runtime after activation, "
            f"then log `feature_outcome` before calling it learned. [evidence: {item.trace()}]"
        )
    consequence_items = [item for item in improved if item.kind == "consequence"]
    for item in consequence_items[:5]:
        lines.append(f"- {item.title}: reuse the claim -> evidence -> proposal loop when proof is observable. [evidence: {item.trace()}]")
    return lines


def _read_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def _first(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return ""


def _first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return _clean(line.lstrip("# "))
    return ""


def _first_labeled_value(text: str, labels: tuple[str, ...]) -> str:
    for label in labels:
        value = _extract_label(text, label)
        if value:
            return value
    return ""


def _extract_label(text: str, label: str) -> str:
    match = re.search(rf"^\s*-?\s*{re.escape(label)}\s*:\s*(.+)$", text, flags=re.I | re.M)
    return _clean(match.group(1)) if match else ""


def _extract_backtick_label(text: str, label: str) -> str:
    match = re.search(rf"-\s*{re.escape(label)}:\s*`([^`]+)`", text, flags=re.I)
    return _clean(match.group(1)).lower() if match else ""


def _first_substantive_line(text: str) -> str:
    for line in text.splitlines():
        clean = _clean(line.strip("- "))
        if clean and not clean.startswith("#") and not clean.startswith("---") and not clean.startswith("generated:"):
            return clean
    return ""


def _looks_positive_proof(text: str) -> bool:
    lower = text.lower()
    return any(token in lower for token in ("intent solved", "verified", "passed", "realized", "proof"))


def _feature_verdict(value: Any) -> str:
    text = _clean(value).lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "better": "improved",
        "pass": "improved",
        "passed": "improved",
        "success": "improved",
        "same": "flat",
        "neutral": "flat",
        "failed": "regressed",
        "fail": "regressed",
        "worse": "regressed",
    }
    verdict = aliases.get(text, text)
    return verdict if verdict in {"improved", "flat", "regressed", "unknown"} else "unknown"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def _anchor(title: str) -> str:
    return re.sub(r"[^a-z0-9 -]", "", title.lower()).replace(" ", "-")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return " ".join(str(value).split())


def _ascii(text: str) -> str:
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2192": "->",
        "\u00b7": "-",
        "\u03a3": "sum",
        "\u2705": "[done]",
        "\ud83d\udccb": "[reference]",
        "\ud83d\udd34": "[red]",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("ascii", errors="ignore").decode("ascii")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Distill traced learning evidence into core/STATE/ACADEMY.md.")
    parser.add_argument("--proofs-dir", type=Path, default=DEFAULT_PROOFS)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--consequence-report", type=Path, default=DEFAULT_CONSEQUENCE)
    parser.add_argument("--corrections-jsonl", type=Path)
    parser.add_argument("--from-live-db", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    corrections = load_corrections_jsonl(args.corrections_jsonl)
    if args.from_live_db:
        corrections.extend(load_live_corrections())
    text = distill_academy(
        proofs_dir=args.proofs_dir,
        ops_ledger=args.ops_ledger,
        consequence_report=args.consequence_report,
        corrections=corrections,
        output=args.output,
    )
    print(json.dumps({"ok": True, "output": str(args.output), "bytes": len(text.encode("utf-8"))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
