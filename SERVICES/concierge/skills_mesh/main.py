"""skills-mesh (port 8825) — skills-based routing, ratings, earnings, availability.

This service is the source of truth for "which agent is best right now".
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from shared.app_factory import create_app
from shared.db import SessionLocal, tenant_session
from shared.tenant_context import TenantContext, get_tenant_context

app = create_app("skills-mesh")


class MatchRequest(BaseModel):
    skills_required: list[str]
    exclude: list[str] = []


class MatchResult(BaseModel):
    agent_id: str | None
    score: float
    reason: str


@app.post("/match", response_model=MatchResult)
async def match_agent(body: MatchRequest, ctx: TenantContext = Depends(get_tenant_context)):
    now = datetime.now(timezone.utc)

    async with SessionLocal() as session:
        await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
        row = (
            await session.execute(
                text(
                    """
                    WITH tenant_agents AS (
                      SELECT a.id, a.rating_overall
                        FROM agents a
                        JOIN agent_tenant_access ata ON ata.agent_id = a.id
                       WHERE ata.tenant_id = CAST(:tid AS uuid)
                         AND ata.revoked_at IS NULL
                         AND a.status = 'active'
                    ),
                    live AS (
                      SELECT DISTINCT agent_id
                        FROM availabilities
                       WHERE status = 'live'
                         AND starts_at <= :now AND ends_at >= :now
                    ),
                    skilled AS (
                      SELECT ag.id, ag.rating_overall,
                             COUNT(DISTINCT s.id) FILTER (
                               WHERE s.key = ANY(:skills)
                                 AND ask.level IN ('certified','expert')
                             ) AS skill_hits,
                             COALESCE(AVG(ask.rating) FILTER (WHERE s.key = ANY(:skills)), 0) AS skill_rating
                        FROM tenant_agents ag
                        LEFT JOIN agent_skills ask ON ask.agent_id = ag.id
                        LEFT JOIN skills s ON s.id = ask.skill_id
                       WHERE ag.id IN (SELECT agent_id FROM live)
                         AND NOT (ag.id::text = ANY(:exclude))
                       GROUP BY ag.id, ag.rating_overall
                    )
                    SELECT id::text,
                           (skill_hits * 2 + skill_rating + rating_overall) AS score
                      FROM skilled
                     WHERE skill_hits > 0 OR cardinality(:skills) = 0
                     ORDER BY score DESC
                     LIMIT 1
                    """
                ),
                {
                    "tid": ctx.tenant_id,
                    "skills": body.skills_required,
                    "exclude": body.exclude,
                    "now": now,
                },
            )
        ).first()

    if not row:
        return MatchResult(agent_id=None, score=0.0, reason="no_available_agents")
    return MatchResult(agent_id=row[0], score=float(row[1] or 0.0), reason="matched")


class AvailabilityIn(BaseModel):
    agent_id: str
    starts_at: datetime
    ends_at: datetime
    status: str = "scheduled"


@app.post("/availabilities")
async def create_availability(body: AvailabilityIn, ctx: TenantContext = Depends(get_tenant_context)):
    async with SessionLocal() as session:
        await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
        row = (
            await session.execute(
                text(
                    """
                    INSERT INTO availabilities (agent_id, starts_at, ends_at, status)
                    VALUES (CAST(:aid AS uuid), :s, :e, :st)
                    RETURNING id::text
                    """
                ),
                {"aid": body.agent_id, "s": body.starts_at, "e": body.ends_at, "st": body.status},
            )
        ).first()
        await session.commit()
    return {"id": row[0]}


class RatingIn(BaseModel):
    agent_id: str
    skill_key: str | None = None
    conversation_id: str | None = None
    source: str
    score: float
    rubric: dict = {}


@app.post("/ratings")
async def add_rating(body: RatingIn, ctx: TenantContext = Depends(get_tenant_context)):
    async with tenant_session(ctx.tenant_id) as session:
        skill_id = None
        if body.skill_key:
            r = (
                await session.execute(
                    text("SELECT id FROM skills WHERE key = :k"), {"k": body.skill_key}
                )
            ).first()
            skill_id = r[0] if r else None
        await session.execute(
            text(
                """
                INSERT INTO ratings (agent_id, skill_id, conversation_id, source, score, rubric)
                VALUES (
                  CAST(:aid AS uuid),
                  CASE WHEN :sid IS NULL THEN NULL ELSE CAST(:sid AS uuid) END,
                  CASE WHEN :cid IS NULL THEN NULL ELSE CAST(:cid AS uuid) END,
                  :src, :sc, CAST(:rb AS jsonb)
                )
                """
            ),
            {
                "aid": body.agent_id,
                "sid": str(skill_id) if skill_id else None,
                "cid": body.conversation_id,
                "src": body.source,
                "sc": body.score,
                "rb": _to_json(body.rubric),
            },
        )
        # Update rolling rating (simple EMA)
        if skill_id:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_skills (agent_id, skill_id, rating, calls_scored)
                    VALUES (CAST(:aid AS uuid), CAST(:sid AS uuid), :sc, 1)
                    ON CONFLICT (agent_id, skill_id) DO UPDATE
                      SET rating = (agent_skills.rating * agent_skills.calls_scored + EXCLUDED.rating)
                                   / (agent_skills.calls_scored + 1),
                          calls_scored = agent_skills.calls_scored + 1,
                          updated_at = now()
                    """
                ),
                {"aid": body.agent_id, "sid": str(skill_id), "sc": body.score},
            )
    return {"ok": True}


class EarningIn(BaseModel):
    agent_id: str
    conversation_id: str | None = None
    kind: str
    amount_uc: float
    notes: str | None = None


@app.post("/earnings")
async def add_earning(body: EarningIn, ctx: TenantContext = Depends(get_tenant_context)):
    async with tenant_session(ctx.tenant_id) as session:
        await session.execute(
            text(
                """
                INSERT INTO earnings_ledger (agent_id, tenant_id, conversation_id, kind, amount_uc, notes)
                VALUES (
                  CAST(:aid AS uuid), CAST(:tid AS uuid),
                  CASE WHEN :cid IS NULL THEN NULL ELSE CAST(:cid AS uuid) END,
                  :kind, :amt, :notes
                )
                """
            ),
            {
                "aid": body.agent_id,
                "tid": ctx.tenant_id,
                "cid": body.conversation_id,
                "kind": body.kind,
                "amt": body.amount_uc,
                "notes": body.notes,
            },
        )
    return {"ok": True}


def _to_json(v):
    import json

    return json.dumps(v or {})
