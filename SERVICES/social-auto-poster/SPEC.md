# Content Pipeline V1 — build-in-public from commits

> **STATUS 2026-05-19:** This file supersedes the older "Social Auto-Poster"
> grand-vision spec (preserved below for reference under `## Legacy spec`).
> The new V1 is caveman: commits → Haiku → Telegram preview → James taps POST.
> Built by The Forge on 2026-05-19 per "4 AI Engine Upgrades" greenlight.

## The frame

James's most-valuable currency = JamesTime. Every move he already makes
(a commit, a decision, a voice memo, a retreat moment) should compound into
reach without him doing extra work. The Content Pipeline is the JamesTime
multiplier — engineering soul-time at the substrate level.

V1 ships ONE source (commits) end-to-end. V2 adds sources without
re-architecting.

## Architecture

```
git commit  (James already does this)
   │
   ▼
.git/hooks/post-commit
   │ (collects sha, subject, body, files, stat, author)
   │ POSTs JSON via curl -s
   ▼
brain.sunheart.com server (162.0.208.88)
   /opt/content-pipeline/tools/draft_from_commit.py
   │
   ├─ pre-filter (drop chore/identity/merge/revert)
   ├─ Claude Haiku 4.5 → draft {tg, x, thread, why, skip}
   ├─ save /opt/content-pipeline/drafts/{ts}_{sha}_{uuid}.json
   └─ Telegram sendMessage with inline keyboard
         [📣 POST] [✏️ EDIT] [🗑 SKIP]
         to TELEGRAM_CHAT_ID via existing @Adamclaw_bot token
```

The existing `sh-brain-tgbot.service` long-poller on the brain server already
handles callbacks; v1.1 wires `pipeline:*` callback handlers to move drafts
between `drafts/`, `posted/`, `skipped/` and dispatch the actual platform
posts. v1.0 (this ship) generates drafts only — James can copy from TG.

## Inputs (V1 → V3 roadmap)

| Source | Trigger | Ships in |
|---|---|---|
| Git commits | post-commit hook | **V1** ← here |
| Voice memos (SuperWhisper) | file drop in `~/voice-in/` | V2 |
| Brain captures (`/note`, `/concept` on TG) | brain webhook | V2 |
| Retreat photos | iOS shortcut → upload endpoint | V3 |
| Counsel critiques landing | brain.sunheart.com/legal/ webhook | V3 |
| Treasury yield deploys | treasurer agent emits event | V3 |
| Screen recordings (Camp Zen moments) | manual drop + Gemini Vision | V3 |

## Outputs (V1 → V3)

| Channel | Format | Approval |
|---|---|---|
| Telegram preview to James | rich HTML w/ inline buttons | **automatic in V1** |
| Drafts dir (auditable) | JSON | automatic |
| Public Telegram channel | one-tap POST | V1.1 |
| X/Twitter | one-tap POST via X API | V2 (needs API key) |
| Threads / IG | via meta-graph API | V3 |
| Public roll page at fullpotential.com/builds/ | auto-publish posted/ | V2 |

## Approval surface

V1: **auto-draft, never auto-post.** James gets a TG preview within
~5 seconds of any commit. Tapping POST is one of three states:
- POST → moves draft to `posted/`, fires channel send (V1.1)
- EDIT → bot replies with a quote and James can rewrite (V1.1)
- SKIP → moves draft to `skipped/`, learns the pattern (V2)

## Costs

| Item | $/mo |
|---|---|
| Claude Haiku for drafting | ~$0.50 (at ~5 commits/day × 30 days × $0.0003) |
| Telegram bot send | $0 |
| Server hosting | $0 (existing brain.sunheart.com) |
| **Total V1** | **<$1/mo** |

V2 adds X API ($0 for basic posting), no other paid services until V3.

## Build-in-public meta-loop

The pipeline IS build-in-public material itself: the commit landing this
spec generates the first draft about itself. Recursion = aesthetic.

## Pre-filter rules (avoid burning tokens on noise)

Drop commits whose subject matches:
- `chore(identity): checkpoint*`
- `chore(identity): settle*`
- `merge *`
- `revert *`
- `chore(security): scrub*` (sensitive content)

Everything else gets drafted. Haiku itself decides skip=true for cleanup.

## Voice baked into the SYSTEM prompt

- Caveman clarity (short, point first, no filler)
- First-person plural ("we shipped", "we wired")
- Present tense
- Never invent metrics or names not in the commit
- Hashtags only when natural (1-2 max)

## Phase 2 wishlist

1. Wire `pipeline:*` callback handlers in `sh-brain-tgbot` (the missing 50%)
2. Voice-memo source: drop SuperWhisper output in `~/voice-in/` → cron picks up
3. Public roll page at `fullpotential.com/builds/` — auto-publish posted drafts
4. X API integration (Twitter posting)
5. Auto-clip pipeline (sibling to this — paired ship)
6. Affiliate notif system (sibling) — fires when champion converts
7. Alumni TG group (sibling) — push retreat-grad-only content here

## Reference

- [[reference-capability-inventory]] — this pipe gets added
- [[feedback-build-in-public]] — the journey IS the offering
- [[reference-time-currency-ladder]] — pipe lives at "free-AI" tier
- [[reference-james-hour]] — the unit being multiplied
- `tools/draft_from_commit.py` (reference implementation in Appendix A)
- `.git/hooks/post-commit` (patched in same loop)

---

## Appendix A — Reference implementation

The server-side script that the post-commit hook POSTs to. Saved at
`/opt/content-pipeline/tools/draft_from_commit.py` on brain.sunheart.com
(162.0.208.88). Reads commit JSON on stdin; writes draft + sends TG preview.

```python
#!/usr/bin/env python3
"""Content Pipeline v1 - Source #1 (commits).

Reads commit JSON payload from stdin, drafts a build-in-public post via
Claude Haiku, saves draft to /opt/content-pipeline/drafts/, sends Telegram
preview to James with inline POST / EDIT / SKIP buttons.

ENV expected on server (already present in /etc/sh-brain/curator.env):
  ANTHROPIC_API_KEY      — drafting
  TELEGRAM_BOT_TOKEN     — preview push (@Adamclaw_bot)
  TELEGRAM_CHAT_ID       — James's owner chat id

Cost: ~$0.0002/commit at Haiku rates.
Reversibility: only ever writes drafts + sends a preview. Never posts publicly.
"""
import json, os, sys, time, uuid
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError

DRAFTS_DIR = Path("/opt/content-pipeline/drafts")
LOGS_DIR = Path("/opt/content-pipeline/logs")
MODEL_NAME = os.environ.get("CONTENT_PIPELINE_MODEL", "claude-haiku-4-5-20251001")
LLM_URL = "https://api.anthropic.com/v1/messages"
TG_API = "https://api.telegram.org/bot{t}/sendMessage"

SYSTEM_PROMPT = (
    "You are the build-in-public voice for James Sunheart. "
    "Turn a single git commit into a tight micro-post.\n\n"
    "Voice: caveman clarity. Short sentences. Point first. No filler. "
    "First-person plural ('we shipped'). Present tense. No invented metrics. "
    "If commit is internal cleanup, return skip=true.\n\n"
    "Return JSON only with keys: tg (<=500c), x (<=270c), "
    "thread (array of strings, empty if 1-tweeter), "
    "why (one-line reminder for James), skip (boolean)."
)


def call_llm(commit):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    files = commit.get("files", [])
    body_text = commit.get("body") or "(no body)"
    stat_text = (commit.get("stat", "") or "")[:1500]
    file_list = "\n".join(files[:30])
    prompt = (
        f"COMMIT {commit['sha']}: {commit['subject']}\n\n"
        f"AUTHOR: {commit.get('author','')}\n\n"
        f"BODY:\n{body_text}\n\n"
        f"FILES ({len(files)}):\n{file_list}\n\n"
        f"STAT:\n{stat_text}\n\nDraft the post per system rules."
    )
    payload = {
        "model": MODEL_NAME, "max_tokens": 700,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    req = urlrequest.Request(LLM_URL, data=json.dumps(payload).encode(), headers=headers)
    try:
        with urlrequest.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except (URLError, HTTPError, TimeoutError) as e:
        sys.stderr.write(f"[pipeline] llm failed: {e}\n")
        return None
    text = ""
    for b in data.get("content", []):
        if b.get("type") == "text":
            text += b.get("text", "")
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"tg": text[:500], "x": text[:270], "thread": [], "why": "", "skip": False}


def save_draft(commit, draft):
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    draft_id = f"{int(time.time())}_{commit['sha']}_{uuid.uuid4().hex[:6]}"
    out = DRAFTS_DIR / f"{draft_id}.json"
    out.write_text(json.dumps({
        "id": draft_id, "source": "commit",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        "commit": commit, "draft": draft, "status": "pending",
    }, indent=2))
    return out


def telegram_preview(draft, commit, draft_path):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    sha, subj = commit["sha"], commit["subject"]
    stem = draft_path.stem
    if draft.get("skip"):
        body = (f"⚪ <b>pipeline · skipped</b> · {sha}\n"
                f"<code>{subj}</code>\n"
                f"<i>(internal/cleanup — no public draft generated)</i>")
        kb = None
    else:
        why = f"\n<i>{draft.get('why','')}</i>" if draft.get("why") else ""
        body = (f"🟢 <b>pipeline · draft</b> · {sha}\n"
                f"<code>{subj}</code>\n\n"
                f"<b>TG:</b> {draft.get('tg','(empty)')}\n\n"
                f"<b>X:</b> {draft.get('x','(empty)')}{why}\n\n"
                f"<code>{draft_path.name}</code>")
        kb = {"inline_keyboard": [[
            {"text": "📣 POST", "callback_data": f"pipeline:post:{stem}"},
            {"text": "✏️ EDIT", "callback_data": f"pipeline:edit:{stem}"},
            {"text": "🗑 SKIP", "callback_data": f"pipeline:skip:{stem}"},
        ]]}
    payload = {"chat_id": chat_id, "text": body[:4000],
               "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb:
        payload["reply_markup"] = json.dumps(kb)
    req = urlrequest.Request(
        TG_API.format(t=token),
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
    )
    try:
        urlrequest.urlopen(req, timeout=10).read()
        return True
    except (URLError, HTTPError, TimeoutError) as e:
        sys.stderr.write(f"[pipeline] telegram failed: {e}\n")
        return False


def process(commit):
    if not commit.get("sha"):
        return None
    subj = (commit.get("subject") or "").lower()
    for p in ("chore(identity): checkpoint", "chore(identity): settle",
              "merge ", "revert ", "chore(security): scrub"):
        if subj.startswith(p):
            return None
    draft = call_llm(commit) or {
        "tg": "", "x": "", "thread": [], "why": "",
        "skip": False, "_error": "llm_unavailable",
    }
    path = save_draft(commit, draft)
    telegram_preview(draft, commit, path)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with (LOGS_DIR / "events.log").open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} draft {path.name} "
                f"subj={(commit.get('subject','')[:80])}\n")
    return path


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        sys.stderr.write("[pipeline] no payload on stdin\n")
        return 1
    try:
        commit = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"[pipeline] bad JSON: {e}\n")
        return 1
    path = process(commit)
    print(str(path) if path else "(filtered)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## Appendix B — post-commit hook addition

Add the following block to `.git/hooks/post-commit` (after Job 4, before
`exit 0`). Sends commit JSON to the pipeline endpoint over SSH so the local
hook stays small and the server holds all keys.

```bash
# Job 5: content pipeline — draft a build-in-public micro-post from this commit.
# Backgrounded; never blocks commit. Silent on failure.
if command -v ssh >/dev/null 2>&1; then
  (
    SHA="$(git rev-parse --short HEAD)"
    SUBJECT="$(git log -1 --pretty=format:%s | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')"
    BODY="$(git log -1 --pretty=format:%b | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')"
    FILES="$(git diff-tree --no-commit-id --name-only -r HEAD | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().splitlines()))')"
    STAT="$(git show --stat --format= HEAD | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')"
    AUTHOR="$(git log -1 --pretty=format:%an | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')"
    PAYLOAD="{\"sha\":\"${SHA}\",\"subject\":${SUBJECT},\"body\":${BODY},\"files\":${FILES},\"stat\":${STAT},\"author\":${AUTHOR}}"
    echo "$PAYLOAD" | ssh -o ConnectTimeout=5 -o BatchMode=yes root@162.0.208.88 \
      'set -a; source /etc/sh-brain/curator.env; set +a; python3 /opt/content-pipeline/tools/draft_from_commit.py' \
      >/dev/null 2>&1 || true
  ) &
fi
```

## Appendix C — server-side install (run once)

```bash
ssh root@162.0.208.88 'bash -s' <<'INSTALL'
set -e
mkdir -p /opt/content-pipeline/{tools,drafts,posted,skipped,logs}
# paste Appendix A python script into /opt/content-pipeline/tools/draft_from_commit.py
chmod +x /opt/content-pipeline/tools/draft_from_commit.py
# Verify env keys exist (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID / ANTHROPIC_API_KEY)
grep -hE '^(ANTHROPIC_API_KEY|TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID)=' /etc/sh-brain/curator.env | sed 's/=.*/=<set>/'
INSTALL
```

## Legacy spec (preserved for reference)

> The original Social Auto-Poster spec is preserved below. It described a
> grand-vision autonomous posting system. V1 above replaces it with the
> minimum-viable caveman version that ships this week.

---

# 📱 Social Auto-Poster System - Technical Specification (Legacy)

**Service Name:** `social-auto-poster`
**Purpose:** Autonomous daily posting to Twitter/LinkedIn without human intervention
**Priority:** Week 2-3 Build (High ROI)
**Infinite Scale:** Yes - posts forever, multiple platforms, zero effort

---

## 🎯 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Social Auto-Poster System                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐        ┌──────────────┐                  │
│  │ Cron Schedule│───────▶│Content Pool  │                  │
│  │  (8 AM daily)│        │(100+ posts)  │                  │
│  └──────────────┘        └──────┬───────┘                  │
│                                  │                           │
│                                  ▼                           │
│                         ┌─────────────────┐                 │
│                         │  AI Generator   │                 │
│                         │   (GPT-4 API)   │                 │
│                         └────────┬────────┘                 │
│                                  │                           │
│                    ┌─────────────┼─────────────┐            │
│                    ▼             ▼             ▼            │
│            ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│            │ Twitter  │  │ LinkedIn │  │ Facebook │        │
│            │   API    │  │   API    │  │   API    │        │
│            └──────────┘  └──────────┘  └──────────┘        │
│                                                              │
│                         ┌──────────────────┐                │
│                         │  Analytics DB    │                │
│                         │ (Track Results)  │                │
│                         └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🤖 How It Works

### Daily Posting Flow
```
1. Cron triggers at 8 AM daily
2. System queries I MATCH metrics:
   - New customers today
   - Matches created today
   - Success stories
   - Interesting data points
3. AI generates 3 post variations:
   - Twitter version (280 chars)
   - LinkedIn version (longer, professional)
   - Facebook version (casual, visual)
4. Posts to all platforms via APIs
5. Tracks engagement metrics
6. Learns from performance (auto-optimization)
```

---

## 📝 Content Strategy

### Content Types (Rotated Daily)

**Type 1: $0 Marketing Challenge Update** (Daily for 30 days)
```
Template:
"📊 Day {day_number}: $0 Marketing Challenge

Today's results:
✅ {customer_count} new signups
✅ {match_count} matches created
✅ $0 spent on ads

What worked: {top_tactic}
Tomorrow's focus: {next_tactic}

Try it: https://fullpotential.com/get-matched

What would you try next? 👇"

Variables: Auto-filled from I MATCH database
```

**Type 2: Success Story** (When available)
```
Template:
"🎉 {customer_name} found their perfect {service_type} in 24 hours

Before: {problem}
After: {solution}

Match score: {match_score}%
Time saved: ~20 hours

See how it works: https://fullpotential.com/get-matched"

Source: I MATCH completed matches
```

**Type 3: Controversial Take** (Weekly)
```
Pool of 20+ hot takes:
- "Spending 30+ hours researching is a waste"
- "Generic marketplaces are dead"
- "AI > 20 hours of Googling"
- "Stop browsing, start matching"

Rotates through pool
```

**Type 4: Data Insight** (Weekly)
```
Template:
"📊 Interesting data from {total_matches} matches:

• {insight_1}
• {insight_2}
• {insight_3}

The average customer saves {hours_saved} hours.

Try matching: https://fullpotential.com/get-matched"

Source: I MATCH analytics
```

**Type 5: Educational** (2x week)
```
Topics:
- "How to choose an executive coach"
- "Church formation: 501c3 vs 508c1a"
- "Vetting AI developers: red flags"
- "What makes a good consultant?"

Evergreen content, rotates
```

---

## 🔧 Technical Implementation

### Stack
```python
# Core
FastAPI==0.104.1
APScheduler==3.10.4
SQLAlchemy==2.0.23
Redis==5.0.1

# AI
openai==1.3.0  # GPT-4 for content generation

# Social APIs
tweepy==4.14.0  # Twitter API v2
linkedin-api==2.0.0  # LinkedIn
facebook-sdk==3.1.0  # Facebook

# Monitoring
prometheus-client==0.19.0
sentry-sdk==1.38.0
```

### Directory Structure
```
social-auto-poster/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app
│   ├── scheduler.py          # APScheduler config
│   ├── content/
│   │   ├── __init__.py
│   │   ├── generator.py      # AI content generation
│   │   ├── templates.py      # Content templates
│   │   └── pool.py           # Pre-written content pool
│   ├── platforms/
│   │   ├── __init__.py
│   │   ├── twitter.py        # Twitter API integration
│   │   ├── linkedin.py       # LinkedIn API integration
│   │   └── facebook.py       # Facebook API integration
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── tracker.py        # Track post performance
│   │   └── optimizer.py      # Auto-optimize based on data
│   └── models/
│       ├── __init__.py
│       ├── post.py           # Post model
│       └── metrics.py        # Metrics model
├── tests/
├── docker-compose.yml
└── requirements.txt
```

### Database Schema
```sql
-- Posts log
CREATE TABLE social_posts (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,  -- 'twitter', 'linkedin', 'facebook'
    content TEXT NOT NULL,
    content_type VARCHAR(50),  -- 'challenge_update', 'success_story', etc.
    posted_at TIMESTAMP DEFAULT NOW(),
    platform_post_id VARCHAR(255),  -- ID from platform
    url TEXT,  -- URL of post
    metrics JSONB  -- impressions, engagements, clicks, etc.
);

-- Content performance tracking
CREATE TABLE content_performance (
    id SERIAL PRIMARY KEY,
    content_type VARCHAR(50) NOT NULL,
    template_id VARCHAR(100),
    platform VARCHAR(50),
    impressions INTEGER DEFAULT 0,
    engagements INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    engagement_rate FLOAT,
    click_rate FLOAT,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Posting schedule
CREATE TABLE posting_schedule (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    time TIME NOT NULL,  -- When to post (e.g., '08:00:00')
    timezone VARCHAR(50) DEFAULT 'America/Los_Angeles',
    enabled BOOLEAN DEFAULT TRUE,
    UNIQUE(platform, time)
);

-- Indexes
CREATE INDEX idx_posts_platform ON social_posts(platform);
CREATE INDEX idx_posts_posted_at ON social_posts(posted_at);
CREATE INDEX idx_performance_type ON content_performance(content_type);
```

---

## 📱 Platform Integration

### Twitter API v2
```python
import tweepy

class TwitterPoster:
    def __init__(self, api_key, api_secret, access_token, access_secret):
        self.client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret
        )

    def post(self, content: str, url: str = None) -> dict:
        """Post to Twitter"""
        # Twitter automatically unfurls URLs
        tweet_text = f"{content}\n\n{url}" if url else content

        # Ensure within 280 char limit
        if len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."

        response = self.client.create_tweet(text=tweet_text)

        return {
            "post_id": response.data['id'],
            "url": f"https://twitter.com/user/status/{response.data['id']}"
        }
```

### LinkedIn API
```python
from linkedin_api import Linkedin

class LinkedInPoster:
    def __init__(self, access_token):
        self.api = Linkedin('', '', access_token=access_token)

    def post(self, content: str, url: str = None) -> dict:
        """Post to LinkedIn"""
        post_data = {
            "author": f"urn:li:person:{self.get_profile_id()}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "ARTICLE" if url else "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        if url:
            post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
                "status": "READY",
                "originalUrl": url
            }]

        response = self.api.post_share(post_data)
        return {"post_id": response['id']}
```

---

## 🤖 AI Content Generation

### GPT-4 Integration
```python
from openai import OpenAI

class ContentGenerator:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def generate_post(self, content_type: str, data: dict, platform: str) -> str:
        """Generate platform-specific content using GPT-4"""

        # Platform-specific constraints
        char_limits = {
            "twitter": 280,
            "linkedin": 3000,
            "facebook": 5000
        }

        prompt = self._build_prompt(content_type, data, platform, char_limits[platform])

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a marketing copywriter creating engaging social media posts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        return response.choices[0].message.content

    def _build_prompt(self, content_type: str, data: dict, platform: str, char_limit: int) -> str:
        """Build GPT-4 prompt based on content type"""

        if content_type == "challenge_update":
            return f"""
            Create a {platform} post for the $0 Marketing Challenge update.

            Data:
            - Day: {data['day_number']}
            - New signups: {data['customer_count']}
            - Matches created: {data['match_count']}
            - Top tactic: {data['top_tactic']}

            Requirements:
            - {char_limit} characters max
            - Include URL: https://fullpotential.com/get-matched
            - Engaging, transparent tone
            - End with question to drive engagement
            - Use relevant emoji
            """

        # ... other content types
```

---

## ⏰ Posting Schedule

### APScheduler Configuration
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class PostingScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Start scheduled posting"""

        # Twitter: 8 AM and 2 PM daily (PT)
        self.scheduler.add_job(
            self.post_to_twitter,
            CronTrigger(hour=8, minute=0, timezone='America/Los_Angeles'),
            id='twitter_morning'
        )
        self.scheduler.add_job(
            self.post_to_twitter,
            CronTrigger(hour=14, minute=0, timezone='America/Los_Angeles'),
            id='twitter_afternoon'
        )

        # LinkedIn: 8 AM daily (PT) - Professional audience
        self.scheduler.add_job(
            self.post_to_linkedin,
            CronTrigger(hour=8, minute=0, timezone='America/Los_Angeles'),
            id='linkedin_morning'
        )

        # Analytics: Update metrics every hour
        self.scheduler.add_job(
            self.update_metrics,
            CronTrigger(minute=0),  # Every hour
            id='metrics_update'
        )

        self.scheduler.start()
```

---

## 📊 Auto-Optimization

### Performance Tracking & Optimization
```python
class ContentOptimizer:
    def analyze_performance(self) -> dict:
        """Analyze which content types perform best"""

        query = """
        SELECT
            content_type,
            platform,
            AVG(engagement_rate) as avg_engagement,
            AVG(click_rate) as avg_clicks,
            COUNT(*) as posts_count
        FROM content_performance
        WHERE posted_at > NOW() - INTERVAL '30 days'
        GROUP BY content_type, platform
        ORDER BY avg_engagement DESC
        """

        results = db.execute(query)
        return results

    def optimize_posting_strategy(self):
        """Auto-adjust what content to post based on performance"""

        performance = self.analyze_performance()

        # Increase frequency of high-performing content
        for row in performance:
            if row['avg_engagement'] > 0.05:  # 5%+ engagement
                self.increase_frequency(row['content_type'], row['platform'])
            elif row['avg_engagement'] < 0.01:  # <1% engagement
                self.decrease_frequency(row['content_type'], row['platform'])

        # Auto-deprecate lowest performers
        bottom_10_percent = performance[-int(len(performance) * 0.1):]
        for row in bottom_10_percent:
            self.deprecate_content_type(row['content_type'])
```

---

## 🚀 Deployment

### Docker Compose
```yaml
version: '3.8'

services:
  social-poster-api:
    build: .
    ports:
      - "8501:8501"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - TWITTER_API_KEY=${TWITTER_API_KEY}
      - LINKEDIN_ACCESS_TOKEN=${LINKEDIN_ACCESS_TOKEN}
    depends_on:
      - redis

  scheduler:
    build: .
    command: python -m app.scheduler
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - TWITTER_API_KEY=${TWITTER_API_KEY}
      - LINKEDIN_ACCESS_TOKEN=${LINKEDIN_ACCESS_TOKEN}
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

## ✅ Success Criteria

### Week 1 (MVP)
- [ ] Posts to Twitter automatically at 8 AM daily
- [ ] Posts to LinkedIn automatically at 8 AM daily
- [ ] AI generates content from I MATCH data
- [ ] Metrics tracked in database

### Month 1 (Optimization)
- [ ] 60+ posts made (30 days × 2 platforms)
- [ ] 5%+ average engagement rate
- [ ] Auto-optimization working
- [ ] 100+ link clicks driven to form

### Month 3 (Scale)
- [ ] 3 platforms (added Facebook)
- [ ] 200+ posts made
- [ ] Content pool optimized
- [ ] 1000+ link clicks total

---

## 📈 Expected Impact

**Effort Saved:**
- Manual posting: 30 min/day = 15 hours/month
- Automated: 0 hours/month forever
- **Savings: 180 hours/year**

**Traffic Generated:**
- Conservative: 10 clicks/post × 60 posts/month = 600 visits/month
- Moderate: 20 clicks/post = 1,200 visits/month
- **Result: +15-30% traffic**

**Brand Building:**
- 60+ posts/month = consistent presence
- Engagement builds authority
- Compounds over time

---

**BUILD TIME:** 10-12 hours
**MAINTENANCE:** 0 hours/month
**INFINITE SCALE:** Yes - posts forever, multiple platforms, auto-optimizes

**Next:** Build after email automation (Week 2-3)
