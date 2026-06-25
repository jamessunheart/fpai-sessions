"""Beacon campaign creation, approval, and attribution tracking."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

DEFAULT_QR_DIR = Path(os.environ.get("BEACON_QR_DIR", "/opt/fpai-build/beacon_qr"))
DEFAULT_PORTAL_URL = os.environ.get("PORTAL_URL", "https://fullpotential.com")
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))

EVENT_COUNTERS = {
    "click": ("clicks", "clicks"),
    "chat_start": ("chat_starts", "chat_starts"),
    "passport_created": ("passports_created", None),
    "cora_earned": ("cora_earned", None),
    "first_action": ("first_actions", None),
    "proof_created": ("proofs_created", "proofs"),
    "paid_conversion": ("paid_conversions", None),
}

APPROVAL_RE = re.compile(r"^b(?P<campaign>[A-Za-z0-9][A-Za-z0-9_-]*):(?P<label>A|B|C|all)$", re.IGNORECASE)


@dataclass(frozen=True)
class BeaconVariant:
    campaign_id: str
    variant_label: str
    content_type: str
    headline: str
    body: str
    cta_text: str
    intent_lane: str
    tone_score: Decimal
    alignment_score: Decimal


class BeaconStore(Protocol):
    def insert_campaign(self, row: dict[str, Any]) -> None: ...
    def insert_variants(self, variants: list[BeaconVariant]) -> None: ...
    def update_campaign_status(self, campaign_id: str, status: str) -> None: ...
    def increment_event(self, campaign_id: str, campaign_counter: str, variant_label: str | None, variant_counter: str | None) -> None: ...
    def approve_variants(self, campaign_id: str, labels: list[str]) -> int: ...
    def get_campaign(self, campaign_id: str) -> dict[str, Any] | None: ...
    def beacon_summary(self) -> dict[str, Any]: ...


class PsycopgBeaconStore:
    """Small sync store wrapper for brain_index tables."""

    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or os.environ.get(
            "BRAIN_INDEX_DB_URL",
            "postgres://brain_index:changeme@127.0.0.1:25432/appflowy",
        )

    def _connect(self):
        import psycopg

        return psycopg.connect(self.db_url, autocommit=True)

    def insert_campaign(self, row: dict[str, Any]) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO brain_index.beacon_campaigns
                    (campaign_id, channel, creative_type, cta, audience, beacon_url, beacon_qr_path, status)
                VALUES (%(campaign_id)s, %(channel)s, %(creative_type)s, %(cta)s, %(audience)s,
                        %(beacon_url)s, %(beacon_qr_path)s, 'draft')
                ON CONFLICT (campaign_id) DO NOTHING
                """,
                row,
            )

    def insert_variants(self, variants: list[BeaconVariant]) -> None:
        if not variants:
            return
        with self._connect() as conn, conn.cursor() as cur:
            for v in variants:
                cur.execute(
                    """
                    INSERT INTO brain_index.beacon_variants
                        (campaign_id, variant_label, content_type, headline, body, cta_text,
                         intent_lane, tone_score, alignment_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        v.campaign_id,
                        v.variant_label,
                        v.content_type,
                        v.headline,
                        v.body,
                        v.cta_text,
                        v.intent_lane,
                        v.tone_score,
                        v.alignment_score,
                    ),
                )

    def update_campaign_status(self, campaign_id: str, status: str) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE brain_index.beacon_campaigns SET status = %s WHERE campaign_id = %s",
                (status, campaign_id),
            )

    def increment_event(
        self,
        campaign_id: str,
        campaign_counter: str,
        variant_label: str | None,
        variant_counter: str | None,
    ) -> None:
        if campaign_counter not in {v[0] for v in EVENT_COUNTERS.values()}:
            raise ValueError(f"unsupported campaign counter: {campaign_counter}")
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"UPDATE brain_index.beacon_campaigns SET {campaign_counter} = {campaign_counter} + 1 WHERE campaign_id = %s",
                (campaign_id,),
            )
            event_type = next((name for name, counters in EVENT_COUNTERS.items() if counters == (campaign_counter, variant_counter)), "")
            cur.execute(
                """
                INSERT INTO brain_index.beacon_events (campaign_id, variant_label, event_type)
                VALUES (%s, %s, %s)
                """,
                (campaign_id, variant_label, event_type),
            )
            if variant_label and variant_counter:
                cur.execute(
                    f"""
                    UPDATE brain_index.beacon_variants
                       SET {variant_counter} = {variant_counter} + 1
                     WHERE campaign_id = %s AND UPPER(variant_label) = UPPER(%s)
                    """,
                    (campaign_id, variant_label),
                )

    def approve_variants(self, campaign_id: str, labels: list[str]) -> int:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE brain_index.beacon_variants
                   SET james_approved_at = NOW()
                 WHERE campaign_id = %s AND UPPER(variant_label) = ANY(%s)
                RETURNING id
                """,
                (campaign_id, [label.upper() for label in labels]),
            )
            rows = cur.fetchall()
            if rows:
                cur.execute(
                    """
                    UPDATE brain_index.beacon_campaigns
                       SET james_approved_at = COALESCE(james_approved_at, NOW()),
                           status = CASE WHEN status = 'draft' THEN 'approved' ELSE status END
                     WHERE campaign_id = %s
                    """,
                    (campaign_id,),
                )
            return len(rows)

    def get_campaign(self, campaign_id: str) -> dict[str, Any] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT campaign_id, status, cost_budget_usd, cost_spent_usd, james_approved_at
                  FROM brain_index.beacon_campaigns
                 WHERE campaign_id = %s
                """,
                (campaign_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {
            "campaign_id": row[0],
            "status": row[1],
            "cost_budget_usd": row[2],
            "cost_spent_usd": row[3],
            "james_approved_at": row[4],
        }

    def beacon_summary(self) -> dict[str, Any]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE status = 'live')::int
                  FROM brain_index.beacon_campaigns
                """
            )
            (active,) = cur.fetchone()
            cur.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE event_type = 'click')::int,
                    COUNT(*) FILTER (WHERE event_type = 'chat_start')::int,
                    COUNT(*) FILTER (WHERE event_type = 'proof_created')::int
                  FROM brain_index.beacon_events
                 WHERE at > NOW() - INTERVAL '24 hours'
                """
            )
            clicks, chats, proofs = cur.fetchone()
            cur.execute(
                """
                SELECT campaign_id, cost_per_proof
                  FROM brain_index.beacon_campaigns
                 WHERE proofs_created > 0
                 ORDER BY cost_per_proof ASC NULLS LAST, proofs_created DESC
                 LIMIT 1
                """
            )
            best = cur.fetchone()
            cur.execute(
                """
                SELECT COUNT(*)::int
                  FROM brain_index.beacon_variants
                 WHERE james_approved_at IS NULL
                """
            )
            (awaiting,) = cur.fetchone()
        return {
            "active_campaigns": active,
            "clicks_24h": clicks,
            "chat_starts_24h": chats,
            "proofs_24h": proofs,
            "best": {"campaign_id": best[0], "cost_per_proof": best[1]} if best else None,
            "ready_for_james": awaiting,
        }


class InMemoryBeaconStore:
    """Test store with the same behavioral surface as the DB store."""

    def __init__(self):
        self.campaigns: dict[str, dict[str, Any]] = {}
        self.variants: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []

    def insert_campaign(self, row: dict[str, Any]) -> None:
        self.campaigns.setdefault(
            row["campaign_id"],
            {
                **row,
                "status": "draft",
                "cost_budget_usd": Decimal("0"),
                "cost_spent_usd": Decimal("0"),
                "clicks": 0,
                "chat_starts": 0,
                "passports_created": 0,
                "cora_earned": 0,
                "first_actions": 0,
                "proofs_created": 0,
                "paid_conversions": 0,
                "james_approved_at": None,
            },
        )

    def insert_variants(self, variants: list[BeaconVariant]) -> None:
        for v in variants:
            self.variants.append(
                {
                    "campaign_id": v.campaign_id,
                    "variant_label": v.variant_label.upper(),
                    "content_type": v.content_type,
                    "headline": v.headline,
                    "body": v.body,
                    "cta_text": v.cta_text,
                    "intent_lane": v.intent_lane,
                    "tone_score": v.tone_score,
                    "alignment_score": v.alignment_score,
                    "clicks": 0,
                    "chat_starts": 0,
                    "proofs": 0,
                    "james_approved_at": None,
                }
            )

    def update_campaign_status(self, campaign_id: str, status: str) -> None:
        self.campaigns[campaign_id]["status"] = status

    def increment_event(
        self,
        campaign_id: str,
        campaign_counter: str,
        variant_label: str | None,
        variant_counter: str | None,
    ) -> None:
        self.campaigns[campaign_id][campaign_counter] += 1
        event_type = next((name for name, counters in EVENT_COUNTERS.items() if counters == (campaign_counter, variant_counter)), "")
        self.events.append(
            {
                "campaign_id": campaign_id,
                "variant_label": variant_label,
                "event_type": event_type,
                "at": datetime.now(timezone.utc),
            }
        )
        if variant_label and variant_counter:
            for row in self.variants:
                if row["campaign_id"] == campaign_id and row["variant_label"] == variant_label.upper():
                    row[variant_counter] += 1

    def approve_variants(self, campaign_id: str, labels: list[str]) -> int:
        wanted = {label.upper() for label in labels}
        now = datetime.now(timezone.utc)
        count = 0
        for row in self.variants:
            if row["campaign_id"] == campaign_id and row["variant_label"] in wanted:
                row["james_approved_at"] = now
                count += 1
        if count and campaign_id in self.campaigns:
            self.campaigns[campaign_id]["james_approved_at"] = now
            if self.campaigns[campaign_id]["status"] == "draft":
                self.campaigns[campaign_id]["status"] = "approved"
        return count

    def get_campaign(self, campaign_id: str) -> dict[str, Any] | None:
        return self.campaigns.get(campaign_id)

    def beacon_summary(self) -> dict[str, Any]:
        campaigns = list(self.campaigns.values())
        live = [c for c in campaigns if c["status"] == "live"]
        awaiting = sum(1 for v in self.variants if not v["james_approved_at"])
        best = None
        proven = [c for c in campaigns if c.get("proofs_created", 0) > 0]
        if proven:
            c = min(proven, key=lambda row: (row["cost_spent_usd"] / row["proofs_created"]))
            best = {"campaign_id": c["campaign_id"], "cost_per_proof": c["cost_spent_usd"] / c["proofs_created"]}
        return {
            "active_campaigns": len(live),
            "clicks_24h": sum(c["clicks"] for c in campaigns),
            "chat_starts_24h": sum(c["chat_starts"] for c in campaigns),
            "proofs_24h": sum(c["proofs_created"] for c in campaigns),
            "best": best,
            "ready_for_james": awaiting,
        }


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "campaign"


def parse_beacon_id(beacon_id: str) -> tuple[str, str | None]:
    value = (beacon_id or "").strip()
    if ":" in value:
        campaign_id, variant = value.rsplit(":", 1)
        variant = variant.upper() if variant else None
        return campaign_id, variant
    return value, None


def write_qr_png(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import qrcode

        image = qrcode.make(url)
        image.save(path)
    except Exception:
        # 1x1 transparent PNG fallback for dev/test hosts without qrcode.
        path.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
            b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )


def log_ops_event(event: str, detail: dict[str, Any], ledger: Path = DEFAULT_OPS_LEDGER) -> None:
    row = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "loop": "beacon",
        "event": event,
        "detail": json.dumps(detail, sort_keys=True),
        "cost": "$0",
        "artifact": detail.get("campaign_id", ""),
        "next": "",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
    }
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


class BeaconCampaign:
    def __init__(
        self,
        store: BeaconStore | None = None,
        *,
        portal_url: str = DEFAULT_PORTAL_URL,
        qr_dir: Path = DEFAULT_QR_DIR,
        ops_ledger: Path = DEFAULT_OPS_LEDGER,
    ):
        self.store = store or PsycopgBeaconStore()
        self.portal_url = portal_url.rstrip("/")
        self.qr_dir = qr_dir
        self.ops_ledger = ops_ledger

    def create(
        self,
        channel: str,
        cta_concept: str,
        audience: str,
        intent_lane: str,
        *,
        creative_type: str = "post",
        now: datetime | None = None,
        generate: bool = True,
    ) -> str:
        if os.environ.get("BEACON_DISABLE") == "1":
            raise RuntimeError("Beacon is disabled by BEACON_DISABLE=1")
        if creative_type == "ad" and os.environ.get("BEACON_PAID_ENABLED") != "1":
            raise PermissionError("content_type=ad requires BEACON_PAID_ENABLED=1")

        stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%d%H%M%S")
        campaign_id = f"{slugify(cta_concept)}-{stamp}"
        beacon_url = f"{self.portal_url}/?b={quote(campaign_id)}"
        qr_path = self.qr_dir / f"{campaign_id}.png"
        write_qr_png(beacon_url, qr_path)

        self.store.insert_campaign(
            {
                "campaign_id": campaign_id,
                "channel": channel,
                "creative_type": creative_type,
                "cta": cta_concept,
                "audience": audience,
                "beacon_url": beacon_url,
                "beacon_qr_path": str(qr_path),
            }
        )
        if generate:
            from .variant_generator import generate_variants

            self._current_campaign_id = campaign_id
            variants = generate_variants(
                self,
                cta_concept=cta_concept,
                audience=audience,
                intent_lane=intent_lane,
                content_type=creative_type,
                send_approval=False,
            )
            self.last_campaign_id = campaign_id
            self._current_campaign_id = ""
            self.store.insert_variants(variants)
            from .variant_generator import send_approval_request

            send_approval_request(campaign_id, variants)
        return campaign_id

    def pause(self, campaign_id: str) -> None:
        self.store.update_campaign_status(campaign_id, "paused")
        log_ops_event("beacon_paused", {"campaign_id": campaign_id}, self.ops_ledger)

    def resume(self, campaign_id: str) -> None:
        self.store.update_campaign_status(campaign_id, "live")

    def complete(self, campaign_id: str) -> None:
        self.store.update_campaign_status(campaign_id, "complete")

    def mark_live(self, campaign_id: str, *, paid: bool = False) -> None:
        row = self.store.get_campaign(campaign_id)
        if not row:
            raise KeyError(campaign_id)
        approved = bool(row.get("james_approved_at"))
        budget = Decimal(str(row.get("cost_budget_usd") or 0))
        if paid and (not approved or budget <= 0):
            raise PermissionError("paid campaign cannot go live without James approval and budget")
        if not approved:
            raise PermissionError("campaign cannot go live without James approval")
        self.store.update_campaign_status(campaign_id, "live")

    def record_event(self, beacon_id: str, event_type: str) -> None:
        if os.environ.get("BEACON_DISABLE") == "1":
            return
        if event_type not in EVENT_COUNTERS:
            raise ValueError(f"unknown beacon event_type: {event_type}")
        campaign_id, variant_label = parse_beacon_id(beacon_id)
        campaign_counter, variant_counter = EVENT_COUNTERS[event_type]
        self.store.increment_event(campaign_id, campaign_counter, variant_label, variant_counter)

    def proof_feedback(self, beacon_id: str) -> None:
        if os.environ.get("BEACON_DISABLE") == "1":
            return
        campaign_id, variant_label = parse_beacon_id(beacon_id)
        self.record_event(beacon_id, "proof_created")
        log_ops_event(
            "beacon_proof",
            {"campaign_id": campaign_id, "variant": variant_label or ""},
            self.ops_ledger,
        )


def parse_approval_text(text: str) -> tuple[str, list[str]] | None:
    match = APPROVAL_RE.match((text or "").strip())
    if not match:
        return None
    label = match.group("label").upper()
    labels = ["A", "B", "C"] if label == "ALL" else [label]
    return match.group("campaign"), labels


def approve_from_text(text: str, store: BeaconStore | None = None) -> str | None:
    parsed = parse_approval_text(text)
    if not parsed:
        return None
    campaign_id, labels = parsed
    count = (store or PsycopgBeaconStore()).approve_variants(campaign_id, labels)
    if count == 0:
        return f"Beacon {campaign_id}: no matching variants found."
    label_text = "/".join(labels)
    return (
        f"Beacon {campaign_id}: approved {label_text}. "
        "Organic content is ready for James to post; no auto-post was triggered."
    )
