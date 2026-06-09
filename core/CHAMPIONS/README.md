# Champions — the First Cohort tooling registry

Each Champion in the First Cohort gets the same stack:

1. A **Telegram bot** (one Anthropic-backed service per Champion) — handles lead intake, screens prospects, drafts in their voice, grows memory via `/teach`.
2. A **landing page** — single-file HTML rendered from their yaml config, conversion-optimized, all CTAs pointing to their bot.

This directory is the SSOT for each Champion's identity, voice, offerings, and pricing. Edit the yaml; rerender the site; redeploy the bot.

## The Cohort

| Slug | Name | Status | Bot | Site |
|---|---|---|---|---|
| `cheyenne` | Cheyenne Sapphire | Config complete; bot live as standalone `sapphire-bot.service` | @LilSapphirebot | `sites/cheyenne-sapphire/` |
| `atlas` | Atlas (TODO last name) | Stub — needs intake | TODO | `sites/atlas/` (rendered with TODOs) |
| `halley` | Halley | Stub — needs intake | TODO | `sites/halley/` |
| `josh` | Josh | Stub — needs intake | TODO | `sites/josh/` |
| `sierra` | Sierra | Stub — needs intake | TODO | `sites/sierra/` |
| `delaney` | Delaney | Stub — needs intake | TODO | `sites/delaney/` |

## What you need from each Champion to ship them

For the FIVE who aren't Cheyenne yet, gather the following per Champion. This is the intake form. Fill the answers into `core/CHAMPIONS/<slug>.yaml` (use `_TEMPLATE.yaml` as the starting point, `cheyenne.yaml` as the worked example).

### Identity (5 min from each Champion)
- Full legal name, preferred display name, brand split for the nav-bar
- Their domain (existing or planned)
- One-line positioning ("tantra · embodiment · sovereignty"-style)
- Three hex colors for their theme

### The bot (10 min — Champion creates via @BotFather)
- A Telegram bot username (must be globally unique on Telegram)
- The bot token from BotFather
- Their numeric Telegram ID (or skip — first /start auto-claims)
- The persona name the bot should use (e.g., "Sapphire" for Cheyenne)

### Methodology (most important — 30-60 min with each Champion)
- The name of their method ("The Sapphire Path"-style)
- Three pillars, each with a name and 2-3 sentences
- Their philosophical anchor sentence

### Offerings (45 min per Champion)
For each offering (typically 3):
- Category tag, container name, description
- Selectivity statement (caps, application, frequency)
- Investment level (price)
- 3 features/inclusions
- One image
- Bot intent string (deep-link arg)

### About + Lineage (15 min)
- 1-2 paragraphs about who they are
- Their actual training: teachers, traditions, years, retreats — this is the highest-trust signal

### Testimonials + FAQ (existing material — 15 min curation)
- 3-4 real testimonials with attribution
- Answers to: "is this for me", "who is it NOT for", "how much", "in-person or virtual", "what if I'm not ready"

### Bot positioning seed (10 min)
- One paragraph summary of who they are + what they offer + their tier (becomes the bot's `bot_role_summary`)
- Voice register description (warm/playful/clinical?)
- Audience description (who they serve)

## Workflow

```
# 1. Fill in the Champion's yaml
$EDITOR core/CHAMPIONS/atlas.yaml

# 2. Render their landing page
python3 SERVICES/champion-bot/render_site.py atlas
# → sites/atlas/index.html

# 3. Drop in their photos (Champion provides)
mkdir -p sites/atlas/img
# Copy their hero.jpg, logo.png, offering-1/2/3.jpg, accent-1.jpg into sites/atlas/img/

# 4. Preview locally
open sites/atlas/index.html

# 5. Deploy the bot (after they create their bot via @BotFather)
CHAMPION_SLUG=atlas \
BOT_TOKEN="123:ABC..." \
ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
bash SERVICES/champion-bot/deploy_champion.sh

# 6. They DM @<their_bot_username> and type /start to claim ownership.

# 7. Iterate: edit yaml → rerender → redeploy bot.
```

## Architecture

- **One bot binary, many instances.** All Champions run the same `champion-bot` Python service. They differ only in env files: `/etc/champion-bot/<slug>.env`.
- **systemd template unit.** `champion-bot@.service` is a templated unit; instances are named `champion-bot@<slug>.service`. One unit file, infinite Champions.
- **Per-Champion data isolation.** Each Champion's SQLite DB lives at `/var/lib/champion-bot/<slug>/db.sqlite`. No cross-contamination between Champion conversations.
- **Anthropic key**: shared across all Champions (off James's Max plan). Tracked centrally; each Champion bot makes its own API calls but billing rolls up.

## Cheyenne note

Cheyenne is currently running on the **standalone `sapphire-bot.service`** (built first, before this generic system). Her config (`cheyenne.yaml`) is complete and her site is hand-tuned at `sites/cheyenne-sapphire/`. We can migrate her to `champion-bot@cheyenne` whenever — the generic system is a strict superset of what she's running. For now, leave her alone (don't fix what works).

## Decision filter

When deciding whether to add a feature to this system, run it against the four-fold filter from `core/STATE/NOW.md`:

- **Proof** — does it produce a measurable Champion outcome (income, clients, witnessed work)?
- **Revenue** — does a Champion earn from it within 30 days?
- **Clarity** — does it make "what does the Game *do for me*" easier to answer?
- **Ease** — is it sub-hour to add for the next Champion?

If yes to 3+, ship it. If yes to <2, defer.
