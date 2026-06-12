"""brain-curator entry point.

Usage:
    python3 -m curator <job>

Jobs:
    dedup            Find near-duplicate note pairs (0.85-0.95) and propose links/merges
    summarize        Summarize newly-imported conversations
    cluster-tag      Cluster recent notes and propose canonical tags
    triage           Review Personal-tier notes; propose safe promotions
    digest           Daily brain status report
    council          Claude × GPT debate → synthesized weekly action brief
    apply-approved   Apply every ✅ Approved proposal from the queue
    roi              Daily cost-vs-engagement ledger row + alert thresholds
    opportunities    Daily proactive scan → 3 deliverables (silent if nothing)
    all              Run every job in sequence (for --dry-run / first-time)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("curator")


async def _run(job_name: str) -> dict:
    run_id = uuid.uuid4().hex[:12]
    log.info("run=%s job=%s start", run_id, job_name)
    t0 = datetime.now(timezone.utc)

    if job_name == "dedup":
        from .jobs import dedup as m
    elif job_name == "summarize":
        from .jobs import summarize as m
    elif job_name == "cluster-tag":
        from .jobs import cluster_tag as m
    elif job_name == "triage":
        from .jobs import triage as m
    elif job_name == "digest":
        from .jobs import digest as m
    elif job_name == "council":
        from .jobs import council as m
    elif job_name == "tg-capture":
        from .jobs import tg_capture as m
    elif job_name == "apply-approved":
        from .jobs import apply_approved as m
    elif job_name == "roi":
        from .jobs import roi as m
    elif job_name == "opportunities":
        from .jobs import opportunities as m
    else:
        raise SystemExit(f"unknown job: {job_name}")

    try:
        stats = await m.run(run_id)
    except Exception as e:
        log.exception("run=%s job=%s FAILED: %s", run_id, job_name, e)
        raise

    elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
    log.info("run=%s job=%s done in %.1fs  stats=%s", run_id, job_name, elapsed, json.dumps(stats, default=str))
    return stats


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    job = sys.argv[1]
    if job == "tgbot":
        # Long-running poller, not a one-shot job. Bypass _run/asyncio.run.
        from . import tgbot
        return tgbot.main()
    if job == "all":
        async def _all():
            out = {}
            for j in ("dedup", "summarize", "cluster-tag", "triage", "digest", "apply-approved"):
                try:
                    out[j] = await _run(j)
                except Exception as e:
                    out[j] = {"error": str(e)}
            return out
        result = asyncio.run(_all())
    else:
        result = asyncio.run(_run(job))
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
