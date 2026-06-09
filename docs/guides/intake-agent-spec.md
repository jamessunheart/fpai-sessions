# Intake Agent Spec — "The Mouth of the Funnel"

## What This Is

A lightweight agent that monitors inbound channels, does three things for every new contact, and nothing else:

1. **Acknowledge** — respond within minutes so the person knows they were heard
2. **Qualify** — determine if this is a real prospect for Full Potential consulting
3. **Book** — if qualified, get them on Sunheart's calendar

This is NOT a chatbot. It's a triage system with a human face.

---

## Architecture

```
Inbound Channels                    Intake Agent                     Output
─────────────────              ─────────────────────            ──────────────
                               │                   │
Email reply ──────────────────→│  1. Acknowledge    │───→ Auto-reply sent
                               │                   │
Lead capture form ────────────→│  2. Qualify        │───→ Qualified? → Book
                               │     - Budget?      │    Not qualified? → Nurture
Facebook/IG DM ───────────────→│     - Need?        │    Spam? → Discard
                               │     - Timeline?    │
Website contact ──────────────→│     - Fit?         │
                               │                   │
                               │  3. Book / Route   │───→ Calendar link sent
                               │                   │    OR overflow to OneBPO
                               └───────────────────┘    OR flag for Sunheart
                                        │
                                        ↓
                               Lead DB updated
                               CORA notified
                               Telegram alert
```

---

## Inbound Channels (Priority Order)

### Phase 1 (build first)
1. **Email replies** — Monitor Resend/Brevo inbox for replies to outbound emails
2. **Lead capture form** — Already live at port 8191, currently just stores + notifies

### Phase 2 (add when Phase 1 works)
3. **Telegram DMs** — People who message @Adamclaw_bot directly
4. **Facebook/Instagram DMs** — Via Meta Graph API (if business account connected)

### Phase 3 (stretch)
5. **WhatsApp Business** — Via Twilio/Meta WhatsApp API
6. **LinkedIn InMail** — Manual import (no clean API)

---

## Qualification Framework

The agent scores each inbound contact on 4 dimensions:

| Dimension | Question | Score |
|-----------|----------|-------|
| **Need** | Does this person have a problem FP solves? (leadership ceiling, life transition, seeking alignment) | 0-25 |
| **Budget** | Can they likely afford $500-5K/session? (inferred from company size, title, context) | 0-25 |
| **Timeline** | Are they ready now, or just browsing? (language cues: "looking for," "need help with" vs "just curious") | 0-25 |
| **Fit** | Would Sunheart enjoy working with this person? (values alignment, growth mindset, not extractive) | 0-25 |

**Score → Action:**
- 70-100: **Hot lead** → Send calendar link immediately + Telegram alert to Sunheart
- 40-69: **Warm lead** → Send personalized follow-up, add to nurture sequence
- 20-39: **Cold lead** → Polite acknowledgment, add to newsletter list
- 0-19: **Not a fit** → Polite decline or redirect

---

## Acknowledgment Templates

### Hot Lead (score 70+)
```
Subject: Re: [their subject]

[Name],

Thank you for reaching out. Based on what you've shared, I think there's 
a strong alignment with what we do at Full Potential.

James (Sunheart) works directly with [leaders/founders/individuals] on 
exactly this kind of [challenge they described]. 

Would you be open to a 30-minute conversation this week? Here's his 
calendar: [CALENDAR_LINK]

Looking forward to connecting you.

Best,
Full Potential AI Team
```

### Warm Lead (score 40-69)
```
Subject: Re: [their subject]

[Name],

Thanks for getting in touch. I've noted your interest in [their topic].

To make sure we point you in the right direction — could you share a 
bit more about what you're looking for? Specifically:

1. What's the main challenge or transition you're navigating?
2. What would success look like for you in the next 90 days?

This helps us determine the best way to support you.

Best,
Full Potential AI Team
```

### Cold/Not a Fit
```
Subject: Re: [their subject]

[Name],

Thanks for reaching out. We appreciate your interest.

Right now, Full Potential is focused on [specific niche]. Based on what 
you've described, [brief redirect — e.g., "you might find X helpful"].

Wishing you the best,
Full Potential AI Team
```

---

## Calendar Integration Options

| Option | Complexity | Cost |
|--------|-----------|------|
| **Calendly free tier** | Low — just a link | Free (1 event type) |
| **Cal.com self-hosted** | Medium — deploy on server | Free |
| **Google Calendar API** | Medium — OAuth setup | Free |
| **Simple time-slot picker** | Low — custom page | Free |

**Recommendation:** Start with Calendly free tier. One event type: "Full Potential Discovery Call — 30 min." Sunheart sets available hours. Agent sends the link. Zero integration needed for Phase 1.

---

## Data Flow

```
1. Inbound arrives
2. Intake agent:
   a. Parse the message (name, email, content, channel)
   b. Check lead DB — existing contact? Update. New? Create.
   c. Run qualification scoring
   d. Select response template
   e. Personalize with Claude API call (~$0.01)
   f. Send response via appropriate channel
   g. If hot: include calendar link
   h. Update lead DB with score, status, response sent
   i. Notify Telegram: "New [hot/warm/cold] lead: [name] from [channel]"
   j. If hot: also inject into CORA memory as a fact
3. CORA sees hot leads next cycle and can direct follow-up strategy
```

---

## Technical Implementation (When Ready to Build)

```
intake-agent/
├── main.py              # Polling loop + webhook receiver
├── channels/
│   ├── email.py         # Monitor Resend webhook for replies
│   ├── form.py          # Already exists (lead capture API)
│   ├── telegram.py      # Poll @Adamclaw_bot for DMs
│   └── facebook.py      # Meta Graph API polling
├── qualify.py            # Scoring engine
├── respond.py            # Template selection + Claude personalization
├── calendar.py           # Calendar link generation
├── config.json           # Scoring weights, templates, thresholds
└── requirements.txt
```

**Estimated build time:** 4-6 hours (Ori) or 1-2 days (Adam with clear specs)

**Estimated cost per lead processed:** ~$0.01-0.02 (one small Claude call for personalization)

**Estimated monthly cost at 50 leads/month:** ~$0.50-1.00

---

## What Must Exist Before Building

1. **Calendly (or equivalent) link** — Sunheart needs to set this up (5 min)
2. **Resend webhook** — Configure Resend to forward inbound replies to our API
3. **Decision: response speed** — Should the agent respond instantly (automated) or queue for Sunheart review before sending? Recommendation: auto-respond for cold/warm, queue hot leads for 15-min review window before sending calendar link.

---

## Anti-Patterns to Avoid

- **Don't pretend to be Sunheart.** Sign as "Full Potential AI Team" — honest that initial response is AI-assisted.
- **Don't over-qualify.** If someone explicitly asks for a call, give them the link. Don't make them answer 5 questions first.
- **Don't send long emails.** Acknowledgment should be 3-5 sentences. If more context is needed, ask one question.
- **Don't auto-respond to spam.** Basic spam detection: no reply to bulk senders, obvious bots, or promotional emails.

---

## Success Metric

**A qualified lead gets a calendar link within 15 minutes of first contact, without Sunheart lifting a finger.**
