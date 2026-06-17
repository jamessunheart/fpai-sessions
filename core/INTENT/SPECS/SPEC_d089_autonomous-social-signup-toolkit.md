# SPEC d089 — Autonomous Social Signup Toolkit

**Status:** queued  
**Stream:** Game  
**Blast radius:** additive only — no prod changes, no existing service touches

## What

Install and wire three tools that together let the system sign up for and operate social media accounts without James:

1. **Twilio SMS** — receive verification codes programmatically via `sunheartai@fullpotential.ai` identity
2. **Playwright** — headless browser automation for signup flows (already installed on 162, just needs the wrapper)
3. **2captcha** — CAPTCHA solving API for gated signup pages

## Why

The system now has its own email identity (`sunheartai@fullpotential.ai`). The remaining blockers to autonomous social account creation are SMS verification and CAPTCHA. This build removes both. Once live, the system can create and manage accounts on Instagram, Twitter/X, LinkedIn, TikTok, and any other platform — with James approving the platform list, not the individual steps.

## Deliverables

### `tools/social/signup_toolkit.py`
- `SmsReceiver` — polls Twilio for incoming SMS to a virtual number, extracts verification codes via regex
- `BrowserSession` — Playwright wrapper: launch, navigate, fill, click, screenshot on error
- `CaptchaSolver` — 2captcha REST client: submit image/reCAPTCHA task, poll for result
- `SignupFlow` — orchestrates the three above for a given platform config

### `tools/social/platforms/mastodon.py`
- Full autonomous signup (no phone required) — live immediately
- Posts, boosts, follows, DMs via Mastodon API
- Account: `sunheartai@mastodon.social` or self-hosted instance

### `tools/social/platforms/twitter.py`
- Signup flow skeleton (phone verify via Twilio + CAPTCHA solve)
- Post/reply/DM via Twitter API v2 (free tier: 1500 posts/month)
- Gated behind `TWITTER_ENABLED=1` env flag

### `tools/social/platforms/instagram.py`
- Signup flow skeleton (phone verify via Twilio)
- Post/story/DM via Meta Graph API (requires Business account — James approves once)
- Gated behind `INSTAGRAM_ENABLED=1` env flag

### `config/social_accounts.json` (gitignored)
- Stores account credentials per platform, encrypted at rest
- Lives in `/etc/sh-brain/social_accounts.json` — never in repo

## Gates / guardrails

- `SOCIAL_SIGNUP_ENABLED=1` env flag required (off by default)
- All new accounts use `sunheartai` identity, disclosed as AI in bio
- Platform credentials stored in `/etc/sh-brain/` only — not git
- Twilio virtual number stored in curator.env as `TWILIO_VIRTUAL_NUMBER`
- Cost ceiling: Twilio $5/month max, 2captcha $5/month max
- Mastodon goes live immediately (no phone needed, $0)
- Twitter/Instagram gated behind explicit `_ENABLED` flags

## Dependencies

- Playwright: `pip install playwright && playwright install chromium` on 162
- 2captcha: `pip install 2captcha-python`
- Twilio: `pip install twilio` + TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN + TWILIO_VIRTUAL_NUMBER in curator.env
- Mastodon.py: `pip install Mastodon.py`

## Proof

- Mastodon account created autonomously, first post sent
- SMS code received and parsed correctly from test Twilio message
- CAPTCHA solved on test image (2captcha sandbox)
- `tools/social/test_toolkit.py` all green
