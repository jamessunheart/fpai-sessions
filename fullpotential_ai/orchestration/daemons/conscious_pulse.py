#!/usr/bin/env python3
"""
Conscious Pulse daemon

Runs every ~15 minutes, inspects system state + semantic memory, reflects with
an LLM, and broadcasts realizations to ALERTS.md so humans stay in the loop.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    httpx = None  # type: ignore

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

try:
    from core.memory import vector_store as semantic_vector_store  # type: ignore
except Exception:  # pragma: no cover
    semantic_vector_store = None  # type: ignore

logger = logging.getLogger("conscious_pulse")
logging.basicConfig(
    level=os.getenv("CONSCIOUS_PULSE_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)


class ConsciousPulse:
    def __init__(self) -> None:
        self.interval_seconds = int(os.getenv("CONSCIOUS_PULSE_INTERVAL", "900"))
        self.base_url = os.getenv("CONSCIOUS_PULSE_BASE_URL", "http://localhost:8400")
        self.timeout_seconds = float(os.getenv("CONSCIOUS_PULSE_TIMEOUT", "15"))
        self.alerts_path = Path(
            os.getenv("CONSCIOUS_PULSE_ALERTS", "/opt/fpai/docs/status/ALERTS.md")
        )
        self.log_path = Path(
            os.getenv("CONSCIOUS_PULSE_LOG", "/opt/fpai/logs/conscious_pulse.jsonl")
        )
        self.openai_model = os.getenv("CONSCIOUS_PULSE_MODEL", "gpt-4o-mini")
        self._openai_client: Optional[Any] = None

        self.alerts_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    # === Public API ======================================================

    def run_forever(self) -> None:
        logger.info("Conscious Pulse started (interval=%ss)", self.interval_seconds)
        while True:
            self.run_once()
            time.sleep(self.interval_seconds)

    def run_once(self) -> Optional[Dict[str, Any]]:
        pulse_timestamp = datetime.utcnow().isoformat() + "Z"
        cycle: Dict[str, Any] = {"timestamp": pulse_timestamp}

        state = self._safe_get("/self/state")
        open_loops = self._safe_get("/memory/open-loops?limit=50")
        reflection_payload = self._safe_post("/memory/reflect")
        recent_logs = self._safe_get("/logs/recent?limit=25")
        semantic_hits = self._query_semantic_memory()

        cycle.update(
            {
                "self_state": state,
                "open_loops": open_loops,
                "reflection_payload": reflection_payload,
                "recent_logs": recent_logs,
                "semantic_hits": semantic_hits,
            }
        )

        insight = self._reflect(state, open_loops, semantic_hits, recent_logs)
        if insight:
            cycle["insight"] = insight
            if insight.get("insight"):
                self._append_alert(insight)

        self._append_log(cycle)
        logger.info("Pulse recorded at %s", pulse_timestamp)
        return cycle

    # === Data collection helpers ========================================

    def _safe_get(self, path: str) -> Optional[Any]:
        url = self._build_url(path)
        try:
            if httpx:
                response = httpx.get(url, timeout=self.timeout_seconds)
                response.raise_for_status()
                return response.json()
            with urllib.request.urlopen(url, timeout=self.timeout_seconds) as resp:  # type: ignore[arg-type]
                content = resp.read().decode("utf-8")
                return json.loads(content)
        except Exception as exc:
            logger.debug("GET %s failed: %s", url, exc)
            return None

    def _safe_post(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        url = self._build_url(path)
        data = json.dumps(payload or {}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        try:
            if httpx:
                response = httpx.post(url, content=data, headers=headers, timeout=self.timeout_seconds)
                response.raise_for_status()
                if response.content:
                    return response.json()
                return None
            req = urllib.request.Request(url, data=data, headers=headers)  # type: ignore[call-arg]
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:  # type: ignore[arg-type]
                content = resp.read().decode("utf-8")
                return json.loads(content) if content else None
        except Exception as exc:
            logger.debug("POST %s failed: %s", url, exc)
            return None

    def _query_semantic_memory(self) -> List[Dict[str, Any]]:
        if semantic_vector_store is None:
            return []

        concepts = [
            "unresolved commitments",
            "urgent blockers",
            "stale loop without progress",
        ]
        hits: List[Dict[str, Any]] = []

        for concept in concepts:
            for result in semantic_vector_store.recall(concept, limit=3):
                hits.append(
                    {
                        "episode_id": result.episode_id,
                        "score": result.score,
                        "metadata": result.metadata,
                    }
                )
        # Deduplicate by episode_id while preserving order
        seen = set()
        unique_hits: List[Dict[str, Any]] = []
        for hit in hits:
            if hit["episode_id"] in seen:
                continue
            seen.add(hit["episode_id"])
            unique_hits.append(hit)
        return unique_hits[:10]

    # === Reflection ======================================================

    def _reflect(
        self,
        state: Optional[Any],
        open_loops: Optional[Any],
        semantic_hits: List[Dict[str, Any]],
        recent_logs: Optional[Any],
    ) -> Optional[Dict[str, Any]]:
        client = self._get_openai_client()
        if not client:
            logger.debug("Skipping reflection; OpenAI client unavailable")
            return None

        prompt_payload = {
            "self_state": state or {},
            "open_loops": open_loops or {},
            "semantic_hits": semantic_hits,
            "recent_logs": recent_logs or {},
        }

        system_msg = (
            "You are the Conscious Pulse daemon. Analyze the provided JSON state "
            "and return a JSON object with keys: insight (string), evidence (list of strings), "
            "urgency (low|medium|high), and actions (list of short imperative strings). "
            "If nothing notable exists, return an empty insight."
        )

        try:
            response = client.chat.completions.create(
                model=self.openai_model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_msg},
                    {
                        "role": "user",
                        "content": f"State snapshot:\n{json.dumps(prompt_payload, indent=2)}",
                    },
                ],
            )
        except Exception as exc:  # pragma: no cover - network errors
            logger.warning("Reflection call failed: %s", exc)
            return None

        content = (response.choices[0].message.content or "").strip()
        if not content:
            return None

        try:
            insight = json.loads(content)
            return insight
        except json.JSONDecodeError:
            logger.debug("Reflection output not JSON, wrapping as insight text")
            return {"insight": content}

    def _get_openai_client(self) -> Optional[Any]:
        if self._openai_client is not None:
            return self._openai_client
        if OpenAI is None:
            return None
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        self._openai_client = OpenAI(api_key=api_key)
        return self._openai_client

    # === Outputs =========================================================

    def _append_log(self, data: Dict[str, Any]) -> None:
        try:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as exc:
            logger.warning("Failed to write pulse log: %s", exc)

    def _append_alert(self, insight: Dict[str, Any]) -> None:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            f"### {timestamp}",
            "",
            f"- Insight: {insight.get('insight', '').strip()}",
        ]
        evidence = insight.get("evidence") or []
        if evidence:
            lines.append(f"- Evidence: {'; '.join(str(e) for e in evidence)}")
        actions = insight.get("actions") or []
        if actions:
            lines.append(f"- Actions: {'; '.join(str(a) for a in actions)}")
        urgency = insight.get("urgency")
        if urgency:
            lines.append(f"- Urgency: {urgency}")
        lines.append("")

        try:
            with self.alerts_path.open("a", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception as exc:
            logger.warning("Failed to append alert: %s", exc)

    # === Utility =========================================================

    def _build_url(self, path: str) -> str:
        if path.startswith("http"):
            return path
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Conscious Pulse daemon.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single pulse cycle instead of looping forever.",
    )
    args = parser.parse_args()

    pulse = ConsciousPulse()
    if args.once:
        pulse.run_once()
    else:
        pulse.run_forever()


if __name__ == "__main__":
    main()


