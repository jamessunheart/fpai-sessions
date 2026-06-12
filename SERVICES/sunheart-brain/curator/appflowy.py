"""curator/appflowy.py — minimal AppFlowy REST client for the curator.

Just what we need: login, list workspaces, resolve view/database ids, add row,
update row, list rows. Token caching is in-memory (re-login on 401).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger("curator.appflowy")


SECRETS = Path(os.environ.get("SH_SECRETS", "/root/sh-brain-secrets/brain.env"))
BASE = os.environ.get("SH_APPFLOWY_BASE", "https://brain.sunheart.com")


def _load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if not SECRETS.exists():
        return env
    for line in SECRETS.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


class AppFlowy:
    def __init__(self) -> None:
        env = _load_env()
        self.email = env.get("SH_OWNER_EMAIL") or os.environ.get("SH_OWNER_EMAIL")
        self.password = env.get("SH_OWNER_PASSWORD") or os.environ.get("SH_OWNER_PASSWORD")
        self.workspace_id = env.get("SH_WORKSPACE_ID") or os.environ.get("SH_WORKSPACE_ID")
        if not (self.email and self.password):
            raise RuntimeError("SH_OWNER_EMAIL / SH_OWNER_PASSWORD missing")
        self._token: str | None = None
        self._client: httpx.AsyncClient | None = None

    # --- lifecycle ---
    async def __aenter__(self):
        self._client = httpx.AsyncClient(base_url=BASE, timeout=60)
        await self.login()
        return self

    async def __aexit__(self, *exc):
        if self._client:
            await self._client.aclose()

    async def login(self) -> None:
        r = await self._client.post(
            "/gotrue/token",
            params={"grant_type": "password"},
            json={"email": self.email, "password": self.password},
        )
        r.raise_for_status()
        self._token = r.json()["access_token"]
        if not self.workspace_id:
            ws = await self.get("/api/workspace")
            rows = (ws.get("data") or [])
            if rows:
                self.workspace_id = rows[0]["workspace_id"]

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    # --- HTTP ---
    async def get(self, path: str, **params: Any) -> dict:
        r = await self._client.get(path, headers=self._headers(), params=params or None)
        if r.status_code == 401:
            await self.login()
            r = await self._client.get(path, headers=self._headers(), params=params or None)
        r.raise_for_status()
        return r.json()

    async def post(self, path: str, body: dict | None = None) -> dict:
        r = await self._client.post(path, headers=self._headers(), json=body)
        if r.status_code == 401:
            await self.login()
            r = await self._client.post(path, headers=self._headers(), json=body)
        r.raise_for_status()
        return r.json()

    async def put(self, path: str, body: dict | None = None) -> dict:
        r = await self._client.put(path, headers=self._headers(), json=body)
        if r.status_code == 401:
            await self.login()
            r = await self._client.put(path, headers=self._headers(), json=body)
        r.raise_for_status()
        return r.json()

    # --- schema helpers ---
    async def find_database_id(self, view_name: str) -> tuple[str, str]:
        """Return (view_id, database_id) for a database by AppFlowy view name.

        AppFlowy gives the database_id directly on the folder view's `extra` blob
        (key: `database_id`). The folder view_id is *not* the same as the
        database's internal view_id, so we don't try to cross-reference via
        `/api/workspace/{ws}/database`.
        """
        folder = await self.get(f"/api/workspace/{self.workspace_id}/folder", depth=3)
        root = folder["data"]
        for space in root.get("children", []) or []:
            if not space.get("is_space"):
                continue
            for child in space.get("children", []) or []:
                if child.get("name") != view_name:
                    continue
                view_id = child["view_id"]
                extra = child.get("extra") or {}
                if isinstance(extra, str):
                    try:
                        extra = json.loads(extra)
                    except (TypeError, ValueError):
                        extra = {}
                db_id = extra.get("database_id")
                if db_id:
                    return view_id, db_id
                # Fallback: scan database listing (covers older AppFlowy versions)
                db_list = await self.get(f"/api/workspace/{self.workspace_id}/database")
                for d in db_list.get("data", []):
                    for v in d.get("views", []):
                        if v.get("view_id") == view_id:
                            return view_id, d["id"]
        raise LookupError(f"database '{view_name}' not found in workspace {self.workspace_id}")

    async def list_fields(self, db_id: str) -> list[dict]:
        body = await self.get(f"/api/workspace/{self.workspace_id}/database/{db_id}/fields")
        return body.get("data", []) or []

    async def add_row(self, db_id: str, cells: dict[str, Any]) -> str:
        body = await self.post(
            f"/api/workspace/{self.workspace_id}/database/{db_id}/row",
            {"cells": cells},
        )
        data = body.get("data")
        if isinstance(data, dict):
            return data.get("id") or data.get("row_id")
        return data  # AppFlowy sometimes returns the row id as a bare string

    async def update_row(self, db_id: str, row_id: str, cells: dict[str, Any]) -> None:
        await self.put(
            f"/api/workspace/{self.workspace_id}/database/{db_id}/row/{row_id}",
            {"cells": cells},
        )

    async def list_rows(self, db_id: str, limit: int = 100) -> list[dict]:
        body = await self.get(
            f"/api/workspace/{self.workspace_id}/database/{db_id}/row",
            limit=limit,
        )
        return body.get("data", []) or []
