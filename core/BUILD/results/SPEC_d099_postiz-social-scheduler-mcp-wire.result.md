# SPEC d099 Result — Postiz Social Scheduler MCP Wire

Status: built in repo; live activation pending.

## Summary

Added guarded repo wiring for self-hosted Postiz on server 162 and its MCP endpoint. The build includes a non-secret MCP config fragment, a tested dry-run `schedulePostTool` payload generator, state/proof notes, and an activation script that can clone/update the official Postiz docker-compose repository and start it only when explicitly gated by live-host environment variables.

Codex did not deploy Postiz, create accounts, write secrets, or publish/schedule a live social post from the sandbox.

## Proof

- Repo MCP fragment: `core/BUILD/mcp/postiz.mcp.json`
- Live activation artifact: `core/BUILD/activate/SPEC_d099_postiz-social-scheduler-mcp-wire.sh`
- Dry-run payload helper: `tools/postiz/wire.py`
- Focused tests: `tools/postiz/test_wire.py`

## Live Proof Still Required

After merge on server 162:

1. Run the activation script with `POSTIZ_ACTIVATE=1` after setting the live Postiz env.
2. Start Docker compose with `POSTIZ_START=1` only after env values are complete.
3. Create/connect the Mastodon proof account in Postiz.
4. Create a Postiz Public API key and install the MCP fragment into Ember's MCP config outside git.
5. Call `integrationList`, then `schedulePostTool` for one proof post.

## Rollback

Revert the d099 files. If activation has run, stop the compose stack from `$POSTIZ_ROOT` with `docker compose down`, remove the Postiz MCP fragment from Ember's MCP config, and revoke the Postiz API key.

