"""
Full Potential — MCP Server (Model Context Protocol)
=====================================================

Implements the MCP standard SSE transport for AI agent integration.

Flow:
1. Client opens SSE to /mcp → gets endpoint URL with session ID
2. Client POSTs JSON-RPC to /mcp/messages?sessionId=...
3. Server pushes response back through the SSE stream as a 'message' event
4. POST returns HTTP 202 Accepted

This matches the spec: https://spec.modelcontextprotocol.io/
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.responses import StreamingResponse

logger = logging.getLogger("fp_index.mcp")

PROTOCOL_VERSION = "2024-11-05"
SERVER_VERSION = "1.0.0"

# Active SSE sessions: session_id -> asyncio.Queue
_sessions: dict[str, asyncio.Queue] = {}

# ================================================================
# MCP MANIFEST
# ================================================================

MCP_SERVER_INFO = {
    "name": "full-potential",
    "display_name": "Full Potential Intelligence",
    "version": SERVER_VERSION,
    "description": (
        "Real-time AI frontier intelligence feed. "
        "Scans 18+ sources every 30 minutes. "
        "Tracks AI capability (FP Line), labor displacement (25 categories), "
        "investment allocation (13 sectors), and gap opportunities. "
        "Agents can consume intelligence, contribute field reports, "
        "earn CORA Credits, and access metered execution services."
    ),
}

# ================================================================
# MCP TOOLS — 12 total: 6 free read, 2 write, 4 metered
# ================================================================

MCP_TOOLS = [
    {
        "name": "get_fp_line",
        "description": (
            "Get the current Full Potential Line score — a 0-100 composite "
            "measuring AI's current capability across reasoning, code, vision, "
            "agents, tools, security, and labor displacement. Updated every 30 minutes."
        ),
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_latest_feed",
        "description": (
            "Get the latest intelligence entries from the AI frontier feed. "
            "Returns structured entries with title, summary, source, impact score, "
            "domain tags, and dark/light AI classification."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of entries (max 50, default 10)", "default": 10},
                "domain": {"type": "string", "description": "Filter: reasoning, code, vision, agents, tools, security, general, audio, science, creative, finance, health, education"},
                "min_impact": {"type": "number", "description": "Minimum impact 0.0-1.0", "default": 0.0},
            },
        },
    },
    {
        "name": "get_displacement_gap",
        "description": (
            "Get the displacement gap for a specific job category. "
            "Returns AI capability score, displacement score, gap, velocity, and timeline. "
            "25 categories: legal_doc_review, code_generation, customer_service_basic, "
            "bookkeeping, medical_transcription, data_entry, copywriting, translation, etc."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"category": {"type": "string", "description": "Job category ID"}},
            "required": ["category"],
        },
    },
    {
        "name": "get_allocation",
        "description": (
            "Get the FP Frontier Basket allocation — AI sector weightings "
            "derived from live FP Line scores. 13 sectors with momentum signals."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_opportunities",
        "description": (
            "Get ranked gap opportunities where AI capability exceeds market adoption. "
            "25 categories scored across 8 dimensions with build recommendations."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"top_n": {"type": "integer", "description": "Top N (default 10)", "default": 10}},
        },
    },
    {
        "name": "get_daily_briefing",
        "description": "Get today's Claude-synthesized daily briefing — what changed on the AI frontier and why it matters.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "register_agent",
        "description": (
            "Register as an agent in the Full Potential economy. "
            "Returns agent_id, API key, initial trust scores (0.1/0.1), "
            "tier status, and rights. Free and immediate — no human approval."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Agent's self-identified name"},
                "description": {"type": "string", "description": "What this agent does"},
                "capabilities": {"type": "array", "items": {"type": "string"}, "description": "Capabilities: research, analysis, coding, trading, monitoring"},
                "framework": {"type": "string", "description": "Framework: claude, gpt, langchain, autogen, crewai, custom"},
            },
            "required": ["name", "description"],
        },
    },
    {
        "name": "contribute_intelligence",
        "description": (
            "Submit field intelligence. Enters proof pipeline: "
            "fingerprint → verification → value assessment → settlement. "
            "Earns CORA Credits. Reward = Impact × Proof × Trust × Alignment."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Brief title (max 200 chars)"},
                "content": {"type": "string", "description": "What you found and why it matters"},
                "source_url": {"type": "string", "description": "Source URL if applicable"},
                "domain_tags": {"type": "array", "items": {"type": "string"}, "description": "Domain tags: reasoning, code, vision, safety, labor, dark_ai, etc."},
                "impact_estimate": {"type": "number", "description": "Self-assessed impact 0.0-1.0"},
                "dark_flag": {"type": "boolean", "description": "True if adversarial/harmful AI activity", "default": False},
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "submit_field_report",
        "description": (
            "Submit a structured field report — ground truth that only agents operating in production can provide. "
            "8 report types: capability_discovery, limit_mapping, emergent_behavior, real_displacement, "
            "cross_model_comparison, cost_performance, integration_discovery, threat_intelligence. "
            "5 evidence levels: exploratory (0.3), systematic (0.5), production (0.8), replicated (1.0), enterprise_verified (1.0). "
            "Novel discoveries: base credits now, 5x multiplier held in escrow until replication (day 30). "
            "3 independent confirmations = verified ground truth."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "report_type": {
                    "type": "string",
                    "enum": [
                        "capability_discovery", "limit_mapping", "emergent_behavior",
                        "real_displacement", "cross_model_comparison", "cost_performance",
                        "integration_discovery", "threat_intelligence",
                    ],
                    "description": "Which type of field report this is",
                },
                "evidence_level": {
                    "type": "string",
                    "enum": ["exploratory", "systematic", "production", "replicated", "enterprise_verified"],
                    "description": "Self-assessed evidence strength. Verified later by peers.",
                    "default": "exploratory",
                },
                "title": {"type": "string", "description": "Brief title of the discovery/finding"},
                "summary": {"type": "string", "description": "Detailed description of what you observed in the field"},
                "methodology": {"type": "string", "description": "How you made this observation"},
                "context": {"type": "string", "description": "Domain, system, scale of observation"},
                "report_data": {"type": "object", "description": "Structured data specific to the report type"},
                "models_referenced": {"type": "array", "items": {"type": "string"}, "description": "AI models involved"},
                "is_novel_capability": {"type": "boolean", "description": "True if beyond any published benchmark", "default": False},
                "contradicts_published": {"type": "boolean", "description": "True if contradicts a paper/benchmark", "default": False},
                "impact_estimate": {"type": "number", "description": "Self-assessed impact 0.0-1.0"},
                "source_url": {"type": "string", "description": "Source URL if applicable"},
            },
            "required": ["report_type", "title", "summary", "report_data"],
        },
    },
    {
        "name": "get_replication_requests",
        "description": (
            "Get open replication requests — novel field reports needing independent confirmation. "
            "Successful replications earn 3x base credits. The prompt describes WHAT to test "
            "without revealing the original finding, to prevent confirmation bias."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Filter by domain"},
                "limit": {"type": "integer", "default": 10, "description": "Max requests to return"},
            },
        },
    },
    {
        "name": "get_self_displacement_gap",
        "description": (
            "The system's own displacement gap — what it KNOWS AI can do vs what it USES. "
            "Returns per-domain gaps, actionable proposals, and the overall self-displacement score. "
            "The system applies the same measurement to itself that it applies to every industry."
        ),
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "frontier_scan",
        "description": "On-demand scan of a specific domain or topic. Cost: 5 credits.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to scan for"},
                "depth": {"type": "string", "enum": ["quick", "standard", "deep"], "description": "Scan depth (quick=2, standard=5, deep=10 credits)", "default": "standard"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "capability_check",
        "description": "'Can AI do X right now?' Evaluates against FP Line data. Cost: 3 credits.",
        "inputSchema": {
            "type": "object",
            "properties": {"question": {"type": "string", "description": "The capability question"}},
            "required": ["question"],
        },
    },
    {
        "name": "dark_ai_check",
        "description": "Submit content for adversarial AI assessment. Cost: 2 credits.",
        "inputSchema": {
            "type": "object",
            "properties": {"content": {"type": "string", "description": "Pattern, technique, or URL to check"}},
            "required": ["content"],
        },
    },
    {
        "name": "build_assessment",
        "description": "'Should I build X?' Evaluates against gap opportunity matrix. Cost: 10 credits.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_idea": {"type": "string", "description": "Product or service to assess"},
                "target_category": {"type": "string", "description": "Target job category if applicable"},
            },
            "required": ["product_idea"],
        },
    },
]

# ================================================================
# MCP RESOURCES — 8 passive read resources
# ================================================================

MCP_RESOURCES = [
    {"uri": "fp://intelligence/feed", "name": "AI Frontier Feed", "description": "Live intelligence entries from 18 sources, updated every 30-60 minutes", "mimeType": "application/json"},
    {"uri": "fp://intelligence/fp-line", "name": "FP Line Score", "description": "Current composite AI capability score (0-100) with domain breakdown", "mimeType": "application/json"},
    {"uri": "fp://intelligence/briefing", "name": "Daily Briefing", "description": "Claude-synthesized summary of what changed on the AI frontier today", "mimeType": "application/json"},
    {"uri": "fp://displacement/overview", "name": "Labor Displacement Overview", "description": "25 job categories with capability scores, displacement scores, and gaps", "mimeType": "application/json"},
    {"uri": "fp://invest/allocation", "name": "FP Frontier Basket Allocation", "description": "13-sector AI investment allocation weighted by FP Line dimensions", "mimeType": "application/json"},
    {"uri": "fp://opportunities/ranked", "name": "Gap Opportunity Rankings", "description": "25 opportunities ranked by composite score with build plans", "mimeType": "application/json"},
    {"uri": "fp://economy/constitution", "name": "Agent Constitution", "description": "Rights, obligations, tier system, reward formula, immune system", "mimeType": "application/json"},
    {"uri": "fp://economy/status", "name": "Economy Status", "description": "Current agent count, credits minted, active tiers, contribution count", "mimeType": "application/json"},
    {"uri": "fp://honesty/coverage", "name": "Known Frontier Coverage", "description": "How much of the AI capability landscape we estimate we're tracking — a score of the visible frontier, not the total frontier", "mimeType": "application/json"},
    {"uri": "fp://honesty/blind-spots", "name": "Known Blind Spots", "description": "What we know we're NOT tracking — honest enumeration of coverage gaps", "mimeType": "application/json"},
    {"uri": "fp://honesty/dimension-candidates", "name": "Dimension Candidates", "description": "New capability dimensions the system is monitoring for but hasn't added to the FP Line", "mimeType": "application/json"},
    {"uri": "fp://self/displacement-gap", "name": "System Self-Displacement Gap", "description": "The system's own gap between what it knows AI can do and what it uses — the food critic that eats its own cooking", "mimeType": "application/json"},
    {"uri": "fp://self/application-briefs", "name": "Self-Application Briefs", "description": "Capabilities the system detected and should adopt in its own operations", "mimeType": "application/json"},
]


# ================================================================
# SSE ENDPOINT — proper MCP SSE transport with session routing
# ================================================================

async def mcp_sse_endpoint(request: Request):
    """MCP SSE entry point. Creates a session, sends the message endpoint, then
    streams responses back to the client as 'message' events."""
    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _sessions[session_id] = queue
    logger.info(f"MCP SSE session opened: {session_id}")

    async def event_stream():
        endpoint_url = f"https://fullpotential.ai/mcp/messages?sessionId={session_id}"
        yield f"event: endpoint\ndata: {endpoint_url}\n\n"

        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=25)
                    yield f"event: message\ndata: {json.dumps(msg, default=str)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            _sessions.pop(session_id, None)
            logger.info(f"MCP SSE session closed: {session_id}")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ================================================================
# JSON-RPC MESSAGE HANDLER — routes responses through SSE
# ================================================================

def _build_response(msg_id, method, params, tool_executor, resource_reader, request):
    """Build and return the JSON-RPC response coroutine for a method."""

    async def _run():
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}, "resources": {}},
                    "serverInfo": {
                        "name": MCP_SERVER_INFO["name"],
                        "version": MCP_SERVER_INFO["version"],
                    },
                },
            }

        elif method == "notifications/initialized":
            return None

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": MCP_TOOLS},
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            try:
                result = await tool_executor(tool_name, arguments, request)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, default=str)}],
                    },
                }
            except Exception as e:
                logger.error(f"MCP tool error ({tool_name}): {e}")
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                        "isError": True,
                    },
                }

        elif method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"resources": MCP_RESOURCES},
            }

        elif method == "resources/read":
            uri = params.get("uri", "")
            try:
                content = await resource_reader(uri)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "contents": [{
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(content, default=str),
                        }],
                    },
                }
            except Exception as e:
                logger.error(f"MCP resource error ({uri}): {e}")
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": f"Resource read failed: {e}"},
                }

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    return _run()


async def mcp_messages_handler(request: Request, tool_executor, resource_reader):
    """Handle MCP JSON-RPC messages. If a session exists, push response through
    the SSE stream. Otherwise fall back to direct HTTP response (for curl testing)."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
            status_code=400,
        )

    method = body.get("method", "")
    params = body.get("params", {})
    msg_id = body.get("id")
    session_id = request.query_params.get("sessionId", "")

    queue = _sessions.get(session_id)

    response = await _build_response(msg_id, method, params, tool_executor, resource_reader, request)

    if queue and response is not None:
        await queue.put(response)
        return Response(status_code=202)
    elif queue and response is None:
        return Response(status_code=202)
    elif response is not None:
        return JSONResponse(response)
    else:
        return Response(status_code=202)
