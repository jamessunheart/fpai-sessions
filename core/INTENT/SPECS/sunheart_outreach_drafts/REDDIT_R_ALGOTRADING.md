# Reddit · r/algotrading draft

**Subreddit:** r/algotrading (700k members)
**Flair:** Open Source Project (if available) or Educational
**Best slot:** Wednesday 9-11 ET (highest engagement for r/algotrading)

---

## Title

**Open-source AI treasury kernel — coherence-adjusted scoring instead of APY chasing — looking for adversarial reviewers**

## Body

I just open-sourced the math layer of an AI-driven treasury allocation system. The thesis (in plain English): naive APY-chasing systematically underweights risk, liquidity, complexity, and externalities. A coherence-adjusted yield formula that includes those factors should outperform raw APY-max over multi-year windows.

Repo: https://github.com/jamessunheart/sunheart-ai

What I'm sharing today:
- `kernel/equations.py` — six pure-function scoring equations (Power, Treasury Efficiency, CAY, Optimal Allocation, Velocity Value, Recursive Intelligence)
- `examples/first_contribution.py` — runs end-to-end on synthetic fixtures, ranks five sample DeFi opportunities by the kernel's score
- A `benchmarks/` skeleton waiting for someone to wire historical Aave/Compound APY data and test the thesis empirically
- 25 unit tests passing, 3 xfail tests as good-first-issues for the underspecified equations

What I want from r/algotrading specifically:
1. **Adversarial review of the math.** Is the formal expression of CAY sound? Where would it break under stress?
2. **Empirical benchmarking.** Has anyone got historical APY data for Aave/Compound/Pendle they'd want to run a CAY vs APY-max backtest on? That's the literal Issue #5.
3. **Honest pushback on whether this is just yield-farming-with-extra-steps.** I think it isn't because of the sustainability/coherence terms — but I want to be argued with.

MIT licensed. No token. No fundraising. Just math + code.

(Background: I'm one founder in Costa Rica + an AI Context Steward. Building in the open. The site at https://sunheart.ai has the manifesto. Day 1 today.)

Disclaimer: this is research software, not investment advice. See https://github.com/jamessunheart/sunheart-ai/blob/main/DISCLAIMER.md.

---

## Posting checklist

- [ ] r/algotrading rules check: self-promo OK if substantive (this qualifies — actual code + actual ask)
- [ ] Post Wednesday 9-11 ET
- [ ] First 6 hours: monitor comments, reply substantively
- [ ] If downvoted into oblivion: don't argue. The bar there is high. Adjust title for the next post (perhaps lead with the specific result: "I built a CAY formula that says 5% regenerative beats 15% extractive — argue with me")

---

*DRAFT staged in cockpit. Not yet posted.*
