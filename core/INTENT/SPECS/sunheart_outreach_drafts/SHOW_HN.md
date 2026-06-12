# Show HN draft · Sunheart AI

**Submit at:** https://news.ycombinator.com/submit
**Best slot:** Tuesday or Wednesday 7:00-8:00 ET (10:00-11:00 GMT) per HN data
**Submitter:** @jamessunheart (or whatever HN handle James uses)

---

## Title (80 char max)

**Show HN: Sunheart AI – open-source AI treasury intelligence (kernel + math)**

## URL

https://github.com/jamessunheart/sunheart-ai

## Text (the body — keep under 1500 chars)

Most AI tooling is built to extract attention. I'm trying to build one that returns it.

Sunheart AI is an open-source kernel for treasury intelligence — a pure-Python library that scores capital allocation opportunities using a coherence-adjusted yield formula instead of raw APY chasing. The thesis: $1 moving intelligently outperforms $10 sitting idle.

Day 1 (today): six of eight mathematical layers from the manifesto are encoded as testable functions in `kernel/equations.py`. Twenty-five tests pass. Three xfail tests are literal good-first-issues for builders who want to refine the underspecified equations (recursive intelligence is the most open).

What's there:
- Pure-function kernel, stdlib-only, no chain dependencies
- `examples/first_contribution.py` runs the demo end-to-end
- AGENTS.md + llms.txt + .cursorrules + .openhands/microagents/ — explicit AI-builder contract
- `mocks/aave/` adapter scaffold (where chain integrations land; kernel stays pure)
- CI matrix on Python 3.10/3.11/3.12
- MIT license · no token · no fundraising

I'm one founder + an AI Context Steward shipping in the open from Costa Rica. The repo is hour 0. Looking for adversarial reviewers, second implementations, and people who want to argue with the math.

https://sunheart.ai for the manifesto. Repo above.

---

## Posting checklist

- [ ] Read DISCLAIMER.md once more — not investment advice
- [ ] Confirm 22 tests pass on main (CI badge green)
- [ ] Post during 7-8 ET weekday for visibility
- [ ] Don't reply for first 30 min — let it find its own audience
- [ ] When replying, lead with substance not defensiveness
- [ ] If it dies (which is normal first-try), don't repost same day. Refine and retry in 2 weeks.

## After-post engagement script

- Reply within 2 hours to top 3 comments
- Substance over thanks. If someone proposes a fix, link the relevant `kernel/equations.py` line and offer to land their PR
- If a top comment misreads "no token" — clarify with one sentence + link DISCLAIMER

---

*This is a DRAFT staged in the cockpit. Not yet posted. James reviews and submits when he chooses to.*
