"""Daily Beacon Growth section for the morning digest."""
from __future__ import annotations

from typing import Any

from .campaign import BeaconStore, PsycopgBeaconStore


def render_beacon_growth_section(store: BeaconStore | None = None, pacing: dict[str, Any] | None = None) -> str:
    store = store or PsycopgBeaconStore()
    try:
        summary = store.beacon_summary()
    except Exception as exc:
        return f"BEACON GROWTH\n- unavailable: {exc}"
    pacing = pacing or {"scale": False, "reason": "hold until proof signal is stable", "signal": {}}
    best = summary.get("best")
    best_line = f"{best['campaign_id']} - {best['cost_per_proof']}" if best else "none yet"
    return "\n".join(
        [
            "BEACON GROWTH",
            (
                f"- Active campaigns: {summary.get('active_campaigns', 0)} | "
                f"Total clicks (24h): {summary.get('clicks_24h', 0)} | "
                f"Chat starts: {summary.get('chat_starts_24h', 0)} | "
                f"Proofs: {summary.get('proofs_24h', 0)}"
            ),
            f"- Best performing: {best_line}",
            "- Worst performing: none enough data",
            f"- Pacing signal: {'scale' if pacing.get('scale') else 'hold'} - {pacing.get('reason', '')}",
            f"- Ready for James: {summary.get('ready_for_james', 0)} variants awaiting approval",
            "- Next test recommendation: approve one organic variant and route it through onboarding before any paid spend.",
        ]
    )
