# legal-critic — The Counsel

A specialized AI legal critic grounded in the Sunheart legal corpus
(180pg Church Legal Resource, Coherent Treasury v0.10, CORA Nation declarations,
trustee handbook, etc.).

**Role:** first-pass critique in the AI council protocol (`core/STATE/AI_CHARTER.md` § Refinement Protocol). Outputs feed into v0.2+ of architectural / legal / strategic docs. Human counsel reviews the converged v0.5+ version.

**Not legal advice.** AI critique only. Always engage licensed counsel before action.

## Endpoints

- `POST /critique` — submit a doc, get structured critique
- `POST /search` — pass-through RAG search of legal corpus
- `GET /healthz` — liveness

## Auth

Bearer token (`Authorization: Bearer <token>`). Tokens in
`/etc/legal-critic/legal-critic.env` as `LEGAL_CRITIC_TOKENS='{"<token>":"<agent>",...}'`.

## CLI

```bash
./scripts/critique.sh path/to/doc.md "securities"
echo "..." | ./scripts/critique.sh - "tax"
```

Reads token from `~/.config/fpai/ai.token` (override with `LEGAL_CRITIC_TOKEN`).

## Ingest the legal corpus

```bash
export BRAIN_INGEST_TOKEN=...
python3 scripts/ingest_corpus.py \
  ~/SunheartBrainData/papers/ \
  ~/Downloads/legal_framework_synthesis_v2.md \
  ~/Downloads/remarkably-coherent-treasury-v0.10.md
```

## Deploy

```bash
./deploy.sh
```

Deploys to `/opt/legal-critic/` on `162.0.208.88`. Systemd unit `legal-critic.service`. Port 28092 (loopback). nginx exposes at `https://brain.sunheart.com/legal/`.

## How AIs access it

| Surface | How |
|---|---|
| Claude Code / Cursor / Claude Desktop | HTTP `POST` to `https://brain.sunheart.com/legal/critique` with bearer token |
| Telegram (@sunheartbrain_bot) | `/legal_review` command — sends current message or attached file |
| Local CLI | `legal-critic <file>` (see `scripts/critique.sh`) |
| Brain MCP | `legal_critique` tool (future — wire via MCP server) |

## System prompt

Lives at `system-prompts/legal_critic.md`. Versioned. Per the Refinement Protocol, the prompt itself should go through council passes before becoming canonical.
