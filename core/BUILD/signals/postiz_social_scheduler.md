# Postiz Social Scheduler MCP Wire

Status: repo-wired, live activation pending.

## What Is Wired

- Official compose source: `https://github.com/gitroomhq/postiz-docker-compose`
- Self-hosted backend target: `https://postiz.fullpotential.ai`
- MCP config fragment: `core/BUILD/mcp/postiz.mcp.json`
- Dry-run schedule payload helper: `python3 -m tools.postiz.wire schedule-payload ...`
- Guarded activation script: `core/BUILD/activate/SPEC_d099_postiz-social-scheduler-mcp-wire.sh`

## Live Proof Gate

Codex did not deploy Docker, create social accounts, write secrets, or publish a post. Those are live-host/public-send edges. After merge, Ember can run:

```bash
POSTIZ_ACTIVATE=1 POSTIZ_START=1 core/BUILD/activate/SPEC_d099_postiz-social-scheduler-mcp-wire.sh
```

Then create a Postiz Public API key, install the MCP fragment into Ember's MCP config with the real key outside git, call `integrationList`, and call `schedulePostTool` for one Mastodon proof post.

## First Platforms

- Mastodon: first proof target.
- Instagram: waits on James's one-time Meta token refresh.
- X: waits on Twilio/CAPTCHA/signup path.

