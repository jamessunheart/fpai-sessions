# Proof Witness

**AI witness that captures proof automatically. Humans spend 15 seconds/day confirming, not creating.**

## The Problem

Every system we've designed assumes humans will *do the proving*:
- Film themselves
- Write the testimonial
- Mark the cut
- Confirm the rating
- Take the before/after photo
- Document the work

**That assumption is fragile.** Humans are inconsistent witnesses of their own work.

- The greenhouse gets done; the proof doesn't.
- The marriage cuts; nobody filmed it.
- Coherence gets clearer; the receipt never gets written.

Without proof, the whole circulation engine—content, currency, track records, trust—has no fuel.

## The Solution

**Make proof happen automatically so humans don't have to think about it.**

### The 85/15 Architecture

**85% Automated (Zero human attention):**
- Commit code → Proof logged automatically
- Deploy service → Proof captured
- Upload photo to Telegram → Auto-tagged by context
- Revenue transaction → Proof recorded

**15% One-Click Confirm (15 seconds of attention):**
```
@zenvillage_bot: "I saw 3 events today. Confirm?"

1. ✅ Atlas uploaded photo at greenhouse (2:14pm)
   → Tag as: Greenhouse electrical work?
   [Yes] [No] [Edit]

2. ✅ Kai deployed chief-of-staff (4:32pm)
   → Impact: Revenue now visible ($540)
   [Confirm] [Edit impact]

3. ✅ James answered 5 questions with Claude (evening)
   → Save to knowledge base?
   [Yes - make public] [Yes - private] [Skip]

Reply "1" to confirm all, or tap buttons.
```

**Total human attention: 15 seconds at end of day.**

Proof gets minted. Content gets drafted. Shows up in tomorrow's digest.

---

## What It Does

### 1. Watches Ambient Evidence

**GitHub Integration:**
- Watches commits via webhooks
- Captures deployments
- Auto-tags based on repo/message content
- Generates content drafts automatically

**Telegram Integration** (TODO):
- Watches photo uploads
- Captures voice notes
- Auto-tags by location/time
- Creates before/after pairs

**Calendar Integration** (TODO):
- Meeting happened → proof logged
- Duration tracked
- Attendees recorded

### 2. Auto-Tags with Confidence

**Keyword matching + AI** (MVP uses keywords, can upgrade to Claude/GPT later):
- "greenhouse" + "electrical" → Tag: `greenhouse_electrical`, Confidence: 0.9
- "revenue" + "dashboard" → Tag: `revenue_visibility`, Confidence: 0.8
- Photo + GPS near greenhouse → Tag: `greenhouse`, Confidence: 0.7

**Only suggests tags when confidence > 60%**

### 3. Generates Content Automatically

**Proof → Content in one step:**

Commit message: `"fix: greenhouse lighting circuit"`

Auto-generated tweet:
```
🏡 Greenhouse progress: Fixed lighting circuit

Building paradise one wire at a time.

#BuildInPublic #Greenhouse
```

Human can edit before posting, but gets a starting point.

### 4. Feeds into Daily Digest

**Morning digest shows yesterday's proof:**

```
☀️ *Daily Briefing*
_Monday, April 30_

🎯 *PROOF (Last 24h)*
💻 Atlas: Greenhouse electrical → Fixed lighting circuit
📸 Atlas: Uploaded 3 photos → 40% → 60% complete
💰 Kai: Revenue dashboard deployed → $540 now visible
✅ Sarah: Posted TikTok → 2.4K views

_Total: 4 proof items confirmed_
```

---

## API Endpoints

### Watchers (Automatic Capture)

- `POST /webhooks/github` - GitHub push/deployment webhooks
- `POST /webhooks/telegram` - Telegram photo/message uploads (TODO)

### Confirmation (The 15-Second Step)

- `GET /pending` - Get proof candidates waiting for confirmation
- `POST /confirm/{id}` - Confirm a proof candidate (one-click)
- `POST /reject/{id}` - Reject a proof candidate

### Digest Integration

- `GET /daily-summary` - Get daily proof summary (for digest)
- `GET /digest/format` - Get formatted text for Telegram digest

### Manual Submission

- `POST /submit` - Manually submit proof (for edge cases)

### UDC

- `GET /health` - Health check
- `GET /capabilities` - What this service can do
- `GET /state` - Current state (pending confirmations, etc.)

---

## Data Models

### ProofCandidate

Something that might be proof, waiting for human confirmation:

```python
{
    "id": "abc123",
    "source": "github",  # github, telegram, calendar, etc.
    "type": "code",      # code, photo, metric, event, etc.
    "status": "pending", # pending, confirmed, rejected
    "owner": "atlas",    # Who did the work
    "title": "Fixed greenhouse lighting circuit",
    "description": "Wired 220V outlets, passed inspection",
    "url": "https://github.com/...",
    "tags": ["greenhouse", "electrical"],
    "suggested_question": "greenhouse_electrical",
    "confidence": 0.9,
    "occurred_at": "2026-04-30T14:32:00Z",
    "content_draft": "🏡 Greenhouse progress: ..."
}
```

### ConfirmedProof

Human said "yes, this is real":

```python
{
    "id": "xyz789",
    "candidate_id": "abc123",
    "owner": "atlas",
    "title": "Fixed greenhouse lighting circuit",
    "tags": ["greenhouse_electrical"],
    "impact": "All outlets working, inspection passed",
    "progress_delta": 20.0,  # 40% → 60%
    "occurred_at": "2026-04-30T14:32:00Z",
    "confirmed_at": "2026-04-30T20:15:00Z",
    "content_published": "🏡 Greenhouse progress: ...",
    "content_url": "https://twitter.com/..."
}
```

---

## Setup

### 1. Install Dependencies

```bash
cd SERVICES/proof-witness
pip3 install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

Required:
- `GITHUB_WEBHOOK_SECRET` - For verifying GitHub webhooks
- `TELEGRAM_BOT_TOKEN` - For Telegram integration (optional)

### 3. Run Locally

```bash
python -m app.main
```

Service runs on `http://localhost:8900`

Visit `http://localhost:8900/docs` for interactive API docs.

### 4. Set Up GitHub Webhook

1. Go to your GitHub repo → Settings → Webhooks
2. Add webhook:
   - URL: `https://your-domain.com/webhooks/github`
   - Content type: `application/json`
   - Secret: (same as `GITHUB_WEBHOOK_SECRET` in .env)
   - Events: Push, Deployment

3. Test it: Make a commit, check `/pending` endpoint

---

## Deployment

### Systemd Service

```bash
# Copy service file
sudo cp proof-witness.service /etc/systemd/system/

# Enable and start
sudo systemctl enable proof-witness
sudo systemctl start proof-witness

# Check status
sudo systemctl status proof-witness
```

### Nginx Proxy (Optional)

```nginx
location /proof {
    proxy_pass http://localhost:8900;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

---

## Integration with Chief of Staff

The proof witness feeds into the Chief of Staff digest:

```python
# In Chief of Staff digest.py
async def _fetch_daily_proof() -> Dict:
    """Fetch proof from witness"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8900/daily-summary")
        if response.status_code == 200:
            return response.json()
    return None

# In generate_daily_digest()
proof_summary = await self._fetch_daily_proof()
if proof_summary:
    key_metrics["proof_items"] = proof_summary["total_confirmed"]
    # ... add to digest
```

---

## Roadmap

### Phase 1: GitHub Integration (✅ DONE)
- [x] Capture commits automatically
- [x] Capture deployments
- [x] Auto-tag with keywords
- [x] Generate content drafts
- [x] One-click confirmation API
- [x] Digest integration

### Phase 2: Telegram Bot
- [ ] Photo upload integration
- [ ] Voice note capture
- [ ] Location-based tagging
- [ ] One-tap confirmation in Telegram

### Phase 3: Calendar Integration
- [ ] Meeting attendance proof
- [ ] Duration tracking
- [ ] Participant recording

### Phase 4: AI Upgrade
- [ ] Use Claude/GPT for auto-tagging (better than keywords)
- [ ] Context-aware content generation
- [ ] Suggest which question each proof solves

### Phase 5: Content Publishing
- [ ] Auto-post to Twitter/TikTok (with human approval)
- [ ] Track engagement metrics
- [ ] Feed back into proof system

---

## Philosophy

**The question isn't "Can we build a proof system?"**

**The question is: "Can we make proof happen automatically so humans don't have to think about it?"**

This service is the answer. The witness runs silently, captures ambient evidence, creates proof candidates. Humans spend 15 seconds confirming, not creating.

**That's the smallest amount of human attention that still produces real proof.**

---

## The Meta-Loop

This conversation—where multiple AI instances refined the question from "build a proof tracker" to "make proof happen automatically"—is proof that the methodology works.

**Multi-AI question refinement → better questions → better systems.**

The proof witness is both:
1. A tool that captures proof automatically
2. Proof that the Question-to-Proof system works

**Ship it. The system is already running; it just needs a UI.**

🌐⚡💎
