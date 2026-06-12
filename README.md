# Full Potential AI — MCP Server & Intelligence Platform

A **Model Context Protocol (MCP) server** providing real-time AI frontier intelligence. Scans 27+ sources every 30-60 minutes, tracks AI capability across 7 dimensions, and exposes 16 MCP tools + 13 resources for any MCP-compatible agent.

---

## 📖 Navigation & Guides

**New to this codebase?** Start here:
- **[QUICK_START.md](QUICK_START.md)** - Quick reference for common tasks
- **[STRUCTURE.md](STRUCTURE.md)** - Full directory structure & organization
- **[.ai-agent-guide.md](.ai-agent-guide.md)** - Guide for AI agents (Claude, Cursor)
- **[SERVICES/INDEX.md](SERVICES/INDEX.md)** - Service registry (261 services)

**Reorganized 2026-04-29:** See [MIGRATION_LOG.md](MIGRATION_LOG.md) for what moved where.

---

## MCP Server Quick Start

```
SSE Endpoint: https://fullpotential.ai/mcp
Manifest: https://fullpotential.ai/.well-known/mcp.json
Protocol: MCP 2024-11-05 over SSE transport
```

See [SERVICES/fp-index/README.md](SERVICES/fp-index/README.md) for full MCP documentation, tool list, and connection examples.

### Claude Desktop Config

```json
{
  "mcpServers": {
    "full-potential": {
      "url": "https://fullpotential.ai/mcp"
    }
  }
}
```

## Live Services

| Service | URL | Description |
|---------|-----|-------------|
| **MCP Server** | `https://fullpotential.ai/mcp` | SSE endpoint for MCP agent connections |
| **Intelligence Feed** | `https://fullpotential.ai/intelligence` | Live AI frontier intelligence |
| **Build Logs** | `https://fullpotential.ai/insights` | What the system actually built, with real numbers |
| **Transparency Log** | `https://fullpotential.ai/transparency` | Every conscience layer decision, publicly visible |
| **API** | `https://fullpotential.ai/api/v1/` | REST API for direct integration |

## Directory Overview

- `SERVICES/fp-index/` - MCP server + intelligence engine (main service)
- `SERVICES/` - All production services
- `docs/` - Documentation and coordination
- `core/` - Intelligence and state files

## Architecture

- **Scanner:** 27 sources, 3-tier scanning (30m/60m/6h), 4000+ entries indexed
- **MCP Server:** 16 tools, 13 resources, SSE transport, JSON-RPC 2.0
- **Conscience Layer:** Five-filter gate (SERVE, TRUTH, RESPECT, VALUE_FIRST, COHERENT)
- **Autonomous Actions:** Self-auditing scanner accuracy, provider benchmarks, source health checks
- **Content Engine:** Writes build logs about what the system actually did, with real data

---

Last Updated: 2025-11-17
