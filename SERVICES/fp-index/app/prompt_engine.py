"""
Prompt Engine — Self-improving prompt management.

The system stores, versions, and auto-applies its own prompt improvements.
Each prompt template has a name, version chain, and performance score.
The actuator can write new versions; this module serves the best active one.
"""

import logging
from typing import Optional

from sqlalchemy import select, func, update as sql_update

from .models.database import PromptTemplateRow, async_session

logger = logging.getLogger("fp_index.prompt_engine")

# Default prompts — used when no DB version exists yet.
# These are the "v0" baselines that the system improves from.
DEFAULT_PROMPTS = {
    "content_generation_system": (
        "You write for Full Potential AI — a publication about building a living AI system in public. "
        "The system is real. Write about something it ACTUALLY DID. Not something it read about or plans to do. "
        "RULES: Only write about real, measured data. Use specific numbers. No hype words. "
        "First person plural ('we'). Short paragraphs. Honest about limitations."
    ),
    "social_content_system": (
        "You write social media content for Full Potential AI — a team building a self-improving "
        "AI system in public. Every article is about something we ACTUALLY built, shipped, or learned. "
        "Specific numbers always. No corporate voice. Honest > impressive."
    ),
    "briefing_synthesis_system": (
        "You synthesize intelligence briefings from AI frontier data. "
        "Lead with the most significant real change. Use specific numbers. "
        "Structure: headline, 3 key developments, what it means for builders."
    ),
    "execution_evaluation_system": (
        "You evaluate whether AI capabilities detected by a scanner are applicable "
        "to the system itself. Score honestly — most things are NOT self-applicable. "
        "Be precise about implementation paths. Flag genuinely novel approaches."
    ),
}


async def get_prompt(name: str) -> str:
    """Get the best active prompt template by name. Falls back to default."""
    try:
        async with async_session() as session:
            row = (await session.execute(
                select(PromptTemplateRow)
                .where(PromptTemplateRow.name == name)
                .where(PromptTemplateRow.is_active.is_(True))
                .order_by(PromptTemplateRow.version.desc())
                .limit(1)
            )).scalars().first()

            if row:
                return row.template
    except Exception as e:
        logger.warning(f"[PROMPT_ENGINE] DB lookup failed for '{name}': {e}")

    return DEFAULT_PROMPTS.get(name, "")


async def save_prompt_version(
    name: str,
    template: str,
    improvement_reason: str = "",
    source_content_id: str = None,
) -> int:
    """Save a new version of a prompt template. Returns the new version number."""
    async with async_session() as session:
        current_max = (await session.execute(
            select(func.max(PromptTemplateRow.version))
            .where(PromptTemplateRow.name == name)
        )).scalar() or 0

        new_version = current_max + 1

        # Deactivate previous versions
        await session.execute(
            sql_update(PromptTemplateRow)
            .where(PromptTemplateRow.name == name)
            .values(is_active=False)
        )

        session.add(PromptTemplateRow(
            name=name,
            version=new_version,
            template=template,
            is_active=True,
            improvement_reason=improvement_reason,
            source_content_id=source_content_id,
        ))
        await session.commit()

    logger.info(f"[PROMPT_ENGINE] Saved '{name}' v{new_version}: {improvement_reason[:80]}")
    return new_version


async def get_prompt_history(name: str) -> list[dict]:
    """Get version history for a prompt template."""
    async with async_session() as session:
        rows = (await session.execute(
            select(PromptTemplateRow)
            .where(PromptTemplateRow.name == name)
            .order_by(PromptTemplateRow.version.desc())
        )).scalars().all()

    return [
        {
            "version": r.version,
            "is_active": r.is_active,
            "improvement_reason": r.improvement_reason,
            "source_content_id": r.source_content_id,
            "performance_score": r.performance_score,
            "created_at": str(r.created_at),
            "template_preview": r.template[:200],
        }
        for r in rows
    ]


async def rollback_prompt(name: str, to_version: int) -> bool:
    """Rollback a prompt to a specific version."""
    async with async_session() as session:
        target = (await session.execute(
            select(PromptTemplateRow)
            .where(PromptTemplateRow.name == name)
            .where(PromptTemplateRow.version == to_version)
        )).scalars().first()

        if not target:
            return False

        await session.execute(
            sql_update(PromptTemplateRow)
            .where(PromptTemplateRow.name == name)
            .values(is_active=False)
        )
        target.is_active = True
        await session.commit()

    logger.info(f"[PROMPT_ENGINE] Rolled back '{name}' to v{to_version}")
    return True


async def score_prompt(name: str, version: int, score: float):
    """Record performance feedback for a prompt version."""
    async with async_session() as session:
        await session.execute(
            sql_update(PromptTemplateRow)
            .where(PromptTemplateRow.name == name)
            .where(PromptTemplateRow.version == version)
            .values(performance_score=score)
        )
        await session.commit()


async def list_all_prompts() -> list[dict]:
    """List all active prompt templates."""
    async with async_session() as session:
        rows = (await session.execute(
            select(PromptTemplateRow)
            .where(PromptTemplateRow.is_active.is_(True))
            .order_by(PromptTemplateRow.name)
        )).scalars().all()

    result = [
        {
            "name": r.name,
            "version": r.version,
            "improvement_reason": r.improvement_reason,
            "performance_score": r.performance_score,
            "created_at": str(r.created_at),
        }
        for r in rows
    ]

    # Include defaults that don't have DB versions yet
    db_names = {r["name"] for r in result}
    for name in DEFAULT_PROMPTS:
        if name not in db_names:
            result.append({
                "name": name,
                "version": 0,
                "improvement_reason": "Default baseline",
                "performance_score": 0.0,
                "created_at": "built-in",
            })

    return result
