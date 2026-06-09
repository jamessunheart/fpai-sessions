"""Load a tenant's active voice prompt pack + tool definitions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from shared.db import tenant_session


@dataclass
class PromptPack:
    id: str
    name: str
    system_prompt: str
    tools: list[dict[str, Any]]
    examples: list[dict[str, Any]]


async def load_active_voice_pack(tenant_id: str) -> PromptPack | None:
    async with tenant_session(tenant_id) as session:
        row = (
            await session.execute(
                text(
                    """
                    SELECT id::text, name, system_prompt, tools, examples
                      FROM prompt_packs
                     WHERE kind = 'voice' AND active = true
                     ORDER BY updated_at DESC
                     LIMIT 1
                    """
                )
            )
        ).first()
    if not row:
        return None
    return PromptPack(
        id=row[0],
        name=row[1],
        system_prompt=row[2],
        tools=list(row[3] or []),
        examples=list(row[4] or []),
    )
