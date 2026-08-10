"""outbounders-mcp — minimal MCP (stdio) server wrapping the Outbounders Agent API.

Lets Claude / GPT agents search talent and post jobs directly.

Env:
  OUTBOUNDERS_API_KEY   (required) bearer key minted in the api_keys table
  OUTBOUNDERS_API_BASE  (optional) default https://api.outbounders.com
                        use http://127.0.0.1:8300 when running on the server

Deps: pip install mcp   (stdlib urllib for HTTP — dependency-light)
Run:  python3 server.py  (stdio transport; wire into an MCP client config)
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

API_BASE = os.environ.get("OUTBOUNDERS_API_BASE", "https://api.outbounders.com").rstrip("/")
API_KEY = os.environ.get("OUTBOUNDERS_API_KEY", "")

mcp = FastMCP("outbounders")


def _request(method: str, path: str, params: Optional[dict[str, Any]] = None,
             body: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if not API_KEY:
        return {"error": "OUTBOUNDERS_API_KEY env var not set"}
    url = f"{API_BASE}{path}"
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        if clean:
            url += "?" + urllib.parse.urlencode(clean)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode())
        except Exception:  # noqa: BLE001
            detail = exc.reason
        return {"error": f"HTTP {exc.code}", "detail": detail}
    except urllib.error.URLError as exc:
        return {"error": f"connection failed: {exc.reason}"}


@mcp.tool()
def search_talent(country_code: Optional[str] = None,
                  active_within_days: Optional[int] = None,
                  limit: int = 25) -> dict[str, Any]:
    """Search Outbounders' agent talent pool (anonymized records).

    Records include skill self-scores (survey, cold calling, upsell, close),
    experience years, and night-shift availability. There is no profile-level
    hourly rate — agents propose a rate per application (see get_applications).

    Args:
        country_code: 2-letter ISO country filter, e.g. "PH".
        active_within_days: only agents active within N days (e.g. 90).
        limit: max results (1-100).
    """
    return _request("GET", "/v1/talent", params={
        "country_code": country_code,
        "active_within_days": active_within_days,
        "limit": limit,
    })


@mcp.tool()
def post_job(title: str, description: str) -> dict[str, Any]:
    """Post a job to Outbounders. Enters the admin-approval queue before going public.

    Args:
        title: job title (3-255 chars).
        description: full job description (10-20000 chars).
    """
    return _request("POST", "/v1/jobs", body={"title": title, "description": description})


@mcp.tool()
def get_job(job_id: int) -> dict[str, Any]:
    """Fetch a job posting by id."""
    return _request("GET", f"/v1/jobs/{job_id}")


@mcp.tool()
def get_applications(job_id: int, limit: int = 50) -> dict[str, Any]:
    """Poll applications submitted to a job posting.

    Each application includes the agent's proposed hourly_rate (USD).
    """
    return _request("GET", f"/v1/jobs/{job_id}/applications", params={"limit": limit})


if __name__ == "__main__":
    mcp.run()  # stdio transport
