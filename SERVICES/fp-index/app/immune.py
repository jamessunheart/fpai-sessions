"""
Immune System — Machine-Speed Dark AI Response
================================================

"Dark AI wins when it operates in the shadows.
 The Full Potential Index turns the lights on."

When a new dark AI pattern is detected, every subscribing agent in the
network knows about it in the same cycle. The immune response fires at the
speed of the infection, not at the speed of a human editorial calendar.

Webhook delivery to all registered agents for:
  - dark_ai_alert    : New dark AI activity detected
  - frontier_shift   : Major capability boundary moved
  - scan_complete    : Full scan cycle finished
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from .models.database import async_session, WebhookRow

logger = logging.getLogger("fp_index.immune")

WEBHOOK_TIMEOUT = 10.0
MAX_CONCURRENT_WEBHOOKS = 50


class ImmuneSystem:
    """Distributed immune response for the AI economy."""

    async def register_webhook(self, agent_id: str, callback_url: str, events: list[str]) -> dict:
        async with async_session() as session:
            row = WebhookRow(
                agent_id=agent_id,
                callback_url=callback_url,
                events=events,
            )
            session.add(row)
            await session.commit()
            return {"webhook_id": row.id, "events": events, "status": "active"}

    async def fire_event(self, event_type: str, payload: dict):
        """
        Fire an event to all subscribers of that event type.
        Runs concurrently with bounded parallelism.
        """
        async with async_session() as session:
            result = await session.execute(
                select(WebhookRow).where(WebhookRow.active == True)
            )
            hooks = result.scalars().all()

        targets = []
        for hook in hooks:
            hook_events = hook.events or []
            if event_type in hook_events or "all" in hook_events:
                targets.append(hook)

        if not targets:
            return

        logger.info(f"Firing {event_type} to {len(targets)} subscribers")

        event_payload = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "fp-index",
            "data": payload,
        }

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_WEBHOOKS)

        async def deliver(hook: WebhookRow):
            async with semaphore:
                try:
                    async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
                        resp = await client.post(
                            hook.callback_url,
                            json=event_payload,
                            headers={"X-FP-Event": event_type, "User-Agent": "FPIndex-Immune/1.0"},
                        )
                        if resp.status_code >= 400:
                            logger.warning(
                                f"Webhook delivery failed to {hook.callback_url}: HTTP {resp.status_code}"
                            )
                except Exception as e:
                    logger.warning(f"Webhook delivery error to {hook.callback_url}: {e}")

        await asyncio.gather(*[deliver(h) for h in targets], return_exceptions=True)

    async def fire_dark_ai_alert(self, entry: dict):
        """Specialized alert for dark AI detection — highest priority."""
        await self.fire_event("dark_ai_alert", {
            "alert_level": "critical",
            "title": entry.get("title", ""),
            "summary": entry.get("summary", ""),
            "domains": entry.get("domains", []),
            "source": entry.get("source", ""),
            "source_url": entry.get("source_url"),
            "threat_level": entry.get("threat_level"),
            "countermeasures": entry.get("countermeasures", []),
            "message": "Dark AI pattern detected. Adapt immediately.",
        })

    async def fire_frontier_shift(self, entry: dict):
        """Alert for major capability boundary movements."""
        await self.fire_event("frontier_shift", {
            "title": entry.get("title", ""),
            "summary": entry.get("summary", ""),
            "domains": entry.get("domains", []),
            "impact_score": entry.get("impact_score", 0),
            "message": "The Full Potential Line has shifted. New capabilities available.",
        })

    async def fire_scan_complete(self, stats: dict):
        """Notify subscribers that a scan cycle completed."""
        await self.fire_event("scan_complete", stats)

    async def get_webhook_stats(self) -> dict:
        async with async_session() as session:
            total = (await session.execute(
                select(WebhookRow).where(WebhookRow.active == True)
            )).scalars().all()

        event_counts: dict[str, int] = {}
        for hook in total:
            for event in (hook.events or []):
                event_counts[event] = event_counts.get(event, 0) + 1

        return {
            "total_webhooks": len(total),
            "event_subscriptions": event_counts,
        }


immune = ImmuneSystem()
