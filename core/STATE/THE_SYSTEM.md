# THE SYSTEM — one screen, plain words

**Last cleaned:** 2026-06-25 (verified live on server 162)

One line: **An AI that builds itself, learns, and helps people reach their full potential.**

---

## The 5 parts

| Part | What it does | Where | Alive? |
|------|--------------|-------|--------|
| 🧠 **Brain** | Holds all memory + answers you | 162 · `sh-brain-*` | 🟢 yes |
| 🔨 **Builder** | Writes new code for itself, every 10 min | 162 · `fpai-build-loop` | 🟢 yes |
| ⚖️ **Decider** | Picks what to build next (council) | 162 · `fpai-council` | 🟢 yes |
| 🔭 **Finder** | Hunts new powers + new people | 162 · `forge` + `discovery` | 🟢 forge fixed today |
| 👁️ **Watcher** | Checks the system knows itself | 162 · `awareness probe` | 🟢 42% |

When Builder runs out of work, it asks Decider. Decider finds a job. Builder builds it. Watcher checks. Loop closes. **The system runs itself, $0, even when laptop off.**

---

## The 2 bots

| Bot | For | Brain access? | Alive? |
|-----|-----|---------------|--------|
| 🔒 **@sunheartbrain_bot** | James only | YES — private | 🟢 yes |
| 🌍 **@sunheartai_bot** | Real people | NO — isolated | 🔴 not running |

**Rule: real people NEVER touch the private brain.** Public bot is their door. Build it clean, no brain.

---

## The 1 flow we want (first real conversation)

```
Finder finds person  →  Public bot says hi  →  Person talks  →
Bot answers (no brain)  →  System learns from reply  →  Better next time
```

**Today:** Finder finds names but no way to reach them. Public bot not up yet. So: first conversation = still blocked on the public bot.

---

## What is clean vs messy (honest)

- 🟢 Clean: Brain, Builder, Decider, Watcher — the self-running core. Solid.
- 🟡 Messy: outreach (finds names, can't reach), many half-built pieces, 100+ specs.
- 🔴 Missing: one public bot, isolated, where real people talk.

**Next clean act:** stand up the public bot. One door. No brain. Then the flow above is whole.

---

_This file is the simple truth. Deeper detail: `SYSTEM_ARCHITECTURE.md`. If they disagree, fix this one first — it is the one James + Ember + others read._
