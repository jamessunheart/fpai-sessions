"""
Autonomous Actions — Do Real Things, Then Tell the Story
=========================================================

The system performs measurable actions and narrates the results.
Not hypothetical. Not "we plan to." Things that happened, with numbers.

Each action:
  1. DOES something (scan, benchmark, audit, measure, test)
  2. MEASURES the result (latency, accuracy, count, delta)
  3. NARRATES via the content actuator (honest build log)

Scheduled alongside scan cycles. The system becomes its own reporter.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from sqlalchemy import select, func, desc

from .models.database import (
    IndexEntryRow, ExecutionBriefRow, PublishedContentRow,
    DailyBriefingRow, async_session,
)

logger = logging.getLogger("fp_index.autonomous_actions")

AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://162.0.208.88:8101")


async def _narrate_action(action_name: str, results: dict) -> Optional[str]:
    """Generate a build-log article about a real action the system just performed."""
    from .budget import check_budget, record_spend

    budget = await check_budget("narrate_action")
    if not budget["allowed"]:
        logger.warning(f"[NARRATE] Budget blocked: {budget['reason']}")
        return None

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or not api_key.startswith("sk-ant"):
        logger.warning("[NARRATE] No Anthropic API key — skipping narration")
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        import json
        results_text = json.dumps(results, indent=2, default=str)

        prompt = f"""You write build logs for Full Potential AI — a team building a self-improving AI system in public.

The system just performed a real action. Here are the actual results:

ACTION: {action_name}
TIMESTAMP: {datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")}

RESULTS (these are real — every number is measured, not estimated):
{results_text}

Write a short build log (300-500 words) about what happened.

RULES:
1. Every number in the article MUST come from the results above. Do not invent metrics.
2. First person plural ("we"). Build log voice.
3. Lead with the most interesting finding. What surprised us?
4. Be honest about what didn't work or what was worse than expected.
5. End with what this means for the next iteration.
6. HEADLINE: Under 70 chars. Specific. "We Benchmarked 5 AI Providers — One Was 47x Faster" > "AI Performance Update"

FORMAT:
TITLE: [headline]

[body with ## headers and - bullets]"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        await record_spend(
            "narrate_action", "anthropic", "claude-sonnet-4-20250514",
            tokens_in=getattr(response.usage, "input_tokens", 0),
            tokens_out=getattr(response.usage, "output_tokens", 0),
            description=f"Narrate: {action_name}",
        )

        lines = text.split("\n")
        title = ""
        body_lines = []
        for line in lines:
            stripped = line.strip()
            if not title and stripped.upper().startswith("TITLE:"):
                title = stripped.split(":", 1)[1].strip().strip('"')
            elif not title and stripped.startswith("# ") and len(stripped) < 100:
                title = stripped.lstrip("# ").strip()
            elif stripped:
                body_lines.append(line)
        if not title:
            title = f"Build Log: {action_name}"
        body = "\n\n".join(body_lines)

        from .principles import ExternalAction, ActionType, should_take_action
        gate = should_take_action(ExternalAction(
            action_type=ActionType.CONTENT_CREATION,
            title=title,
            description=body,
            gives_value=True,
            is_verifiable=True,
            source_data={"action": action_name, "results_keys": list(results.keys())},
        ))

        if not gate.passed:
            failed = [o.filter_name for o in gate.outcomes if o.result.value != "pass"]
            logger.warning(f"[NARRATE] Blocked by conscience gate: {', '.join(failed)}")
            return None

        import uuid
        content_id = f"action-{uuid.uuid4().hex[:12]}"
        async with async_session() as session:
            session.add(PublishedContentRow(
                id=content_id,
                title=title,
                body=body,
                content_type="insight_article",
                domain="system",
                source_entries=[action_name],
                gate_decision="passed",
                gate_details={
                    "action": action_name,
                    "filters": [
                        {"name": o.filter_name, "result": o.result.value, "reason": o.reason}
                        for o in gate.outcomes
                    ],
                },
                generated_by="autonomous_action",
            ))
            await session.commit()

        logger.info(f"[NARRATE] Published: {title[:60]} (id={content_id})")

        try:
            from .actuators import _email_content_to_subscribers
            await _email_content_to_subscribers(content_id, title, body)
        except Exception as e:
            logger.warning(f"[NARRATE] Email failed: {e}")

        return content_id

    except Exception as e:
        logger.error(f"[NARRATE] Failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION 1: Scanner Accuracy Audit
# ═══════════════════════════════════════════════════════════════════════════════

async def action_scanner_accuracy_audit() -> dict:
    """Measure how effective the scanner is: signal vs noise ratio."""
    async with async_session() as session:
        total = (await session.execute(
            select(func.count()).select_from(IndexEntryRow)
        )).scalar() or 0

        high_impact = (await session.execute(
            select(func.count()).select_from(IndexEntryRow)
            .where(IndexEntryRow.impact_score >= 0.7)
        )).scalar() or 0

        medium_impact = (await session.execute(
            select(func.count()).select_from(IndexEntryRow)
            .where(IndexEntryRow.impact_score >= 0.4)
            .where(IndexEntryRow.impact_score < 0.7)
        )).scalar() or 0

        low_impact = total - high_impact - medium_impact

        led_to_content = (await session.execute(
            select(func.count(func.distinct(ExecutionBriefRow.entry_id)))
            .where(ExecutionBriefRow.status.in_(["adopted", "implemented"]))
        )).scalar() or 0

        sources = (await session.execute(
            select(
                IndexEntryRow.source,
                func.count().label("cnt"),
                func.avg(IndexEntryRow.impact_score).label("avg_impact"),
            )
            .group_by(IndexEntryRow.source)
            .order_by(desc("avg_impact"))
        )).all()

        source_rankings = [
            {"source": s[0], "entries": s[1], "avg_impact": round(float(s[2] or 0), 3)}
            for s in sources
        ]

    signal_ratio = high_impact / total if total > 0 else 0
    conversion = led_to_content / total if total > 0 else 0

    results = {
        "total_entries_scanned": total,
        "high_impact_entries": high_impact,
        "medium_impact_entries": medium_impact,
        "low_impact_noise": low_impact,
        "signal_to_noise_ratio": f"{signal_ratio:.1%}",
        "entries_that_led_to_action": led_to_content,
        "scan_to_action_conversion": f"{conversion:.2%}",
        "top_5_sources_by_quality": source_rankings[:5],
        "bottom_3_sources_by_quality": source_rankings[-3:] if len(source_rankings) >= 3 else source_rankings,
        "total_sources": len(source_rankings),
    }

    logger.info(f"[ACTION] Scanner audit: {total} entries, {signal_ratio:.1%} signal ratio")
    content_id = await _narrate_action("Scanner Accuracy Audit", results)
    results["article_id"] = content_id
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION 2: Conscience Layer Precision Test
# ═══════════════════════════════════════════════════════════════════════════════

async def action_conscience_precision_test() -> dict:
    """Measure how the conscience layer is performing — are blocks justified?"""
    async with async_session() as session:
        total_published = (await session.execute(
            select(func.count()).select_from(PublishedContentRow)
        )).scalar() or 0

        content_types = dict((await session.execute(
            select(PublishedContentRow.content_type, func.count())
            .group_by(PublishedContentRow.content_type)
        )).all())

        blocked = (await session.execute(
            select(ExecutionBriefRow)
            .where(ExecutionBriefRow.status == "gate_blocked")
            .order_by(desc(ExecutionBriefRow.created_at))
            .limit(20)
        )).scalars().all()

        blocked_details = []
        for b in blocked:
            blocked_details.append({
                "title": (b.entry_title or "")[:80],
                "narrative": (b.narrative or "")[:100],
                "score": b.relevance_score,
            })

        needs_review = (await session.execute(
            select(func.count()).select_from(ExecutionBriefRow)
            .where(ExecutionBriefRow.status == "needs_human_review")
        )).scalar() or 0

        total_proposals = (await session.execute(
            select(func.count()).select_from(ExecutionBriefRow)
        )).scalar() or 0

        adopted_count = (await session.execute(
            select(func.count()).select_from(ExecutionBriefRow)
            .where(ExecutionBriefRow.status.in_(["adopted", "implemented"]))
        )).scalar() or 0

    block_rate = len(blocked) / total_proposals if total_proposals > 0 else 0

    gate_with_details = []
    async with async_session() as session:
        content_with_gates = (await session.execute(
            select(PublishedContentRow.title, PublishedContentRow.gate_details)
            .where(PublishedContentRow.gate_details.isnot(None))
            .order_by(desc(PublishedContentRow.published_at))
            .limit(10)
        )).all()
        for title, details in content_with_gates:
            if isinstance(details, dict) and "filters" in details:
                gate_with_details.append({
                    "title": (title or "")[:60],
                    "filters": details["filters"],
                })

    results = {
        "total_published": total_published,
        "content_by_type": content_types,
        "total_blocked": len(blocked),
        "total_proposals_evaluated": total_proposals,
        "block_rate": f"{block_rate:.1%}",
        "adopted_and_implemented": adopted_count,
        "awaiting_human_review": needs_review,
        "recent_blocks_sample": blocked_details[:5],
        "gate_filter_samples": gate_with_details[:3],
        "conscience_efficiency": f"{(total_published / (total_published + len(blocked)) * 100):.0f}% throughput" if (total_published + len(blocked)) > 0 else "N/A",
    }

    logger.info(f"[ACTION] Conscience test: {total_published} published, {len(blocked)} blocked, {block_rate:.1%} block rate")
    content_id = await _narrate_action("Conscience Layer Precision Test", results)
    results["article_id"] = content_id
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION 3: Source Health Check — Test Which Sources Are Actually Working
# ═══════════════════════════════════════════════════════════════════════════════

async def action_source_health_check() -> dict:
    """Ping each scanner source and measure response time + content quality."""
    async with async_session() as session:
        source_rows = (await session.execute(
            select(
                IndexEntryRow.source,
                IndexEntryRow.source_url,
                func.count().label("cnt"),
            )
            .where(IndexEntryRow.source_url.isnot(None))
            .group_by(IndexEntryRow.source, IndexEntryRow.source_url)
            .order_by(desc("cnt"))
        )).all()

    source_urls = {}
    for row in source_rows:
        name, url, _ = row
        if name and url and name not in source_urls and url.startswith("http"):
            source_urls[name] = url
        if len(source_urls) >= 20:
            break

    results_list = []
    async with httpx.AsyncClient(timeout=10) as client:
        for name, url in source_urls.items():
            start = time.time()
            try:
                resp = await client.get(url, follow_redirects=True)
                latency = round((time.time() - start) * 1000)
                content_length = len(resp.text)
                results_list.append({
                    "source": name,
                    "url": url[:60],
                    "status": resp.status_code,
                    "latency_ms": latency,
                    "content_bytes": content_length,
                    "healthy": resp.status_code == 200 and content_length > 100,
                })
            except Exception as e:
                latency = round((time.time() - start) * 1000)
                results_list.append({
                    "source": name,
                    "url": url[:60],
                    "status": "error",
                    "latency_ms": latency,
                    "error": str(e)[:80],
                    "healthy": False,
                })

    healthy = [r for r in results_list if r.get("healthy")]
    unhealthy = [r for r in results_list if not r.get("healthy")]
    avg_latency = sum(r["latency_ms"] for r in results_list) / len(results_list) if results_list else 0

    results = {
        "total_sources_tested": len(results_list),
        "healthy": len(healthy),
        "unhealthy": len(unhealthy),
        "health_rate": f"{len(healthy)/len(results_list)*100:.0f}%" if results_list else "N/A",
        "average_latency_ms": round(avg_latency),
        "fastest_source": min(results_list, key=lambda r: r["latency_ms"])["source"] if results_list else "N/A",
        "slowest_source": max(results_list, key=lambda r: r["latency_ms"])["source"] if results_list else "N/A",
        "unhealthy_sources": [{"source": r["source"], "reason": r.get("error", f"HTTP {r.get('status')}")} for r in unhealthy],
        "all_results": results_list,
    }

    logger.info(f"[ACTION] Source health: {len(healthy)}/{len(results_list)} healthy, avg {avg_latency:.0f}ms")
    content_id = await _narrate_action("Source Health Check", results)
    results["article_id"] = content_id
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION 4: Provider Latency Benchmark — Time Each AI Provider
# ═══════════════════════════════════════════════════════════════════════════════

async def action_provider_benchmark() -> dict:
    """Benchmark real response times from available AI providers."""
    test_prompt = "In exactly one sentence, explain what a conscience layer does in an AI system."
    benchmarks = []

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key and anthropic_key.startswith("sk-ant"):
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": anthropic_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 100,
                        "messages": [{"role": "user", "content": test_prompt}],
                    },
                )
                latency = round((time.time() - start) * 1000)
                answer = resp.json().get("content", [{}])[0].get("text", "")[:100]
                benchmarks.append({
                    "provider": "Anthropic", "model": "claude-sonnet-4-20250514",
                    "latency_ms": latency, "status": "ok", "answer_preview": answer,
                })
        except Exception as e:
            benchmarks.append({
                "provider": "Anthropic", "model": "claude-sonnet-4-20250514",
                "latency_ms": round((time.time() - start) * 1000),
                "status": "error", "error": str(e)[:80],
            })

    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [{"role": "user", "content": test_prompt}],
                        "max_tokens": 100,
                    },
                )
                latency = round((time.time() - start) * 1000)
                answer = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")[:100]
                benchmarks.append({
                    "provider": "Groq", "model": "llama-3.3-70b-versatile",
                    "latency_ms": latency, "status": "ok", "answer_preview": answer,
                })
        except Exception as e:
            benchmarks.append({
                "provider": "Groq", "model": "llama-3.3-70b-versatile",
                "latency_ms": round((time.time() - start) * 1000),
                "status": "error", "error": str(e)[:80],
            })

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{AI_BRAIN_URL}/v1/chat/completions",
                json={
                    "model": "llama3.1:8b",
                    "messages": [{"role": "user", "content": test_prompt}],
                    "max_tokens": 100,
                },
            )
            latency = round((time.time() - start) * 1000)
            if resp.status_code == 200:
                answer = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")[:100]
                benchmarks.append({
                    "provider": "Ollama (local)", "model": "llama3.1:8b",
                    "latency_ms": latency, "status": "ok", "answer_preview": answer,
                })
            else:
                benchmarks.append({
                    "provider": "Ollama (local)", "model": "llama3.1:8b",
                    "latency_ms": latency, "status": f"http_{resp.status_code}",
                })
    except Exception as e:
        benchmarks.append({
            "provider": "Ollama (local)", "model": "llama3.1:8b",
            "latency_ms": round((time.time() - start) * 1000),
            "status": "error", "error": str(e)[:80],
        })

    ok_benchmarks = [b for b in benchmarks if b["status"] == "ok"]
    fastest = min(ok_benchmarks, key=lambda b: b["latency_ms"]) if ok_benchmarks else None
    slowest = max(ok_benchmarks, key=lambda b: b["latency_ms"]) if ok_benchmarks else None

    results = {
        "providers_tested": len(benchmarks),
        "providers_responding": len(ok_benchmarks),
        "test_prompt": test_prompt,
        "benchmarks": benchmarks,
        "fastest": f"{fastest['provider']} ({fastest['latency_ms']}ms)" if fastest else "N/A",
        "slowest": f"{slowest['provider']} ({slowest['latency_ms']}ms)" if slowest else "N/A",
        "speed_ratio": f"{slowest['latency_ms']/fastest['latency_ms']:.1f}x" if fastest and slowest and fastest['latency_ms'] > 0 else "N/A",
    }

    logger.info(f"[ACTION] Provider benchmark: {len(ok_benchmarks)}/{len(benchmarks)} responding")
    content_id = await _narrate_action("Provider Latency Benchmark", results)
    results["article_id"] = content_id
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION 5: Self-Improvement Impact — Measure before vs after
# ═══════════════════════════════════════════════════════════════════════════════

async def action_self_improvement_impact() -> dict:
    """Measure the impact of all self-improvements the system has made."""
    async with async_session() as session:
        total_proposals = (await session.execute(
            select(func.count()).select_from(ExecutionBriefRow)
        )).scalar() or 0

        status_counts = dict((await session.execute(
            select(ExecutionBriefRow.status, func.count())
            .group_by(ExecutionBriefRow.status)
        )).all())

        implemented = (await session.execute(
            select(ExecutionBriefRow)
            .where(ExecutionBriefRow.status == "implemented")
            .order_by(desc(ExecutionBriefRow.executed_at))
            .limit(10)
        )).scalars().all()

        implemented_details = [
            {
                "title": (i.entry_title or "")[:80],
                "executed": str(i.executed_at)[:16] if i.executed_at else "pending",
                "score": i.relevance_score,
            }
            for i in implemented
        ]

        content_count = (await session.execute(
            select(func.count()).select_from(PublishedContentRow)
        )).scalar() or 0

        first_content = (await session.execute(
            select(func.min(PublishedContentRow.published_at))
        )).scalar()

        latest_content = (await session.execute(
            select(func.max(PublishedContentRow.published_at))
        )).scalar()

    days_active = (latest_content - first_content).days if first_content and latest_content else 1
    content_per_day = content_count / max(days_active, 1)

    results = {
        "total_proposals_ever": total_proposals,
        "status_breakdown": status_counts,
        "implemented_count": status_counts.get("implemented", 0),
        "adopted_count": status_counts.get("adopted", 0),
        "blocked_count": status_counts.get("gate_blocked", 0),
        "pending_review": status_counts.get("needs_human_review", 0),
        "implementation_rate": f"{status_counts.get('implemented', 0) / total_proposals * 100:.1f}%" if total_proposals > 0 else "N/A",
        "total_content_published": content_count,
        "days_active": days_active,
        "content_per_day": round(content_per_day, 1),
        "recent_implementations": implemented_details[:5],
    }

    logger.info(f"[ACTION] Impact audit: {status_counts.get('implemented', 0)} implemented out of {total_proposals}")
    content_id = await _narrate_action("Self-Improvement Impact Measurement", results)
    results["article_id"] = content_id
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR — Run actions on schedule
# ═══════════════════════════════════════════════════════════════════════════════

ALL_ACTIONS = {
    "scanner_accuracy_audit": action_scanner_accuracy_audit,
    "conscience_precision_test": action_conscience_precision_test,
    "source_health_check": action_source_health_check,
    "provider_benchmark": action_provider_benchmark,
    "self_improvement_impact": action_self_improvement_impact,
}

_action_cycle_index = 0


async def run_next_autonomous_action() -> dict:
    """Execute the next action in the rotation and narrate the results.

    Rotates through all actions, one per call. Designed to be called
    from the scheduler so the system continuously does real things
    and writes about them.
    """
    from .budget import check_budget, send_action_alert, ACTION_COST_ESTIMATES

    budget = await check_budget("narrate_action")
    if not budget["allowed"]:
        logger.warning(f"[AUTONOMOUS] Skipped — budget: {budget['reason']}")
        return {"action": "skipped", "success": False, "reason": budget["reason"]}

    global _action_cycle_index
    action_names = list(ALL_ACTIONS.keys())
    action_name = action_names[_action_cycle_index % len(action_names)]
    _action_cycle_index += 1

    logger.info(f"[AUTONOMOUS] Running action: {action_name}")
    try:
        action_fn = ALL_ACTIONS[action_name]
        results = await action_fn()
        logger.info(f"[AUTONOMOUS] Completed: {action_name}, article_id={results.get('article_id')}")

        try:
            await send_action_alert([{
                "action": action_name,
                "cost": ACTION_COST_ESTIMATES.get("narrate_action", 0.03),
                "description": f"Autonomous: {action_name}",
                "content_id": results.get("article_id"),
                "reversible": True,
                "success": True,
            }])
        except Exception:
            pass

        return {"action": action_name, "success": True, "results": results}
    except Exception as e:
        logger.error(f"[AUTONOMOUS] Action {action_name} failed: {e}")
        return {"action": action_name, "success": False, "error": str(e)}
