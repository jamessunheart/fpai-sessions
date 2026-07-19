---
type: doctrine
status: living
source: "Liam's execution-architecture insights · ingested by James 2026-07-19"
tags: [doctrine, goal-stewardship, routing, execution, proof]
---

# GOAL STEWARDSHIP — the middle layer between Routing and Proof

> ## ★ The one sentence
> **Routing is not assignment. Routing is the creation of accountable momentum — every meaningful routed outcome receives a persistent Goal Steward that holds the finish line until reality verifies completion.**

**Where this sits:** DOCTRINE layer, under [[CONSTITUTION]], beside [[FOUNDATION]]. FOUNDATION says *what* we optimize (Three Rs → Future Capability). This says *what continuously owns a thing once it's routed*. When they disagree, Constitution wins, then FOUNDATION, then this.

**The gap it closes.** FPOS was strong at capture → understand → prioritize → route → prove → learn. Unanswered: *once something is routed, what owns it until done?* Answer: a Goal Steward. The unit of responsibility is no longer a message, task, prompt, or agent turn. **It is the completed goal.**

---

## 1. Classification — not everything is a goal

Every incoming intent resolves to exactly one of three:

| Class | Response |
|---|---|
| **QUESTION** | Answer directly. No object created. |
| **SMALL ACTION** | Execute and verify immediately. No object created. |
| **MEANINGFUL GOAL** | Create a Goal Object + assign a Parent Goal Steward. |

Threshold for MEANINGFUL GOAL: requires **multiple actions, multiple carriers (people/tools/agents), or a learning cycle**. Do not force small interactions into projects — that's overhead theater. Do not let multi-step outcomes float unowned — that's the drift we're fixing.

## 2. The canonical Goal Object

One schema everywhere. This is the universal handshake between Router and any harness.

```
GOAL
├── Objective            — desired outcome, one sentence
├── Why it matters       — link to stream / north star
├── Finish line          — OBSERVABLE. What reality shows when done.
├── Priority
├── Owner / Goal Steward — who holds accountability
├── Authority envelope   — what may proceed without James (see §4)
├── Resource budget      — $ cap, time cap, token cap
├── Plan
├── Workstreams          — bounded units dispatched to specialists
├── Dependencies
├── Evidence ledger      — every claim, its receipt
├── Decisions            — what was settled, by whom, when
├── Blockers
├── Next action          — always exactly one, always concrete
└── Completion proof     — the external-reality artifact
```

Machine schema: `core/STATE/schemas/goal_object.schema.json`.

## 3. The execution organization — not a swarm

A collection of workers is not an organization. Separate the tiers:

```
JAMES              governs direction
  ↓
FPOS               decides what should happen · prioritizes · routes
  ↓
GOAL STEWARD       manages · maintains momentum · holds the finish line
  ↓
EXECUTION FLEET    humans · agents · tools · automations — change reality
  ↓
PROOF              determines what is true
  ↓
FPOS               learns and becomes more capable
```

**Each specialist receives five things** — a bounded question · relevant context · a concrete deliverable · permitted files and tools · an evidence standard and stopping condition. Anything less and the specialist invents scope.

**The Goal Steward integrates** results, resolves conflicts between specialists, detects drift from the finish line, and remains accountable regardless of which worker failed.

★ **Build ONE excellent Goal Steward before building many specialists.** Without the steward layer, more agents create more noise. With it, more agents become clean capacity.

## 4. Authority envelope — machine-readable, not vibes

Proceed autonomously when the work is **safe · reversible · in scope · in budget · operational (not strategic)**.

Return to James only when the action changes: **objective or direction · scope or authority · financial exposure · public representation · security or privacy · legal or brand commitments · external reality consequentially.**

> Being technically capable of an action is not authorization to perform it.

**James receives decisions, not operational questions.** A Goal Steward that needs James arrives with:

```
Decision required · Evidence · Options · Recommendation · Consequences
```

One high-leverage judgment from James should unlock another long arc of autonomous execution. Enforced by `tools/governance/constitution_check.py` + `core/STATE/RESERVED_CLASS.yaml` — not instinct.

## 5. Proof gets stricter — an action is not an outcome

- A draft is not a published asset.
- Code is not a working feature.
- Outreach is not pipeline.
- Removing access is not verified savings.
- Delegating work is not completing work.
- Producing a report is not changing reality.

**The six-stage proof ladder** — a goal closes only at stage 5+:

```
1. Attempted
2. Executed
3. Verified          ← external state check, test, receipt, log, screenshot, review
4. Outcome achieved  ← the finish line reads true in reality
5. Value produced
6. Learning captured
```

Verification must connect the action to the intended result through external evidence. Extends [[feedback-merged-reviewed-200-not-working]] and [[MTUE]].

## 6. Memory hierarchy — scoped continuity, not one database

Put every rule and every fact at the **narrowest scope where it stays durable**.

| Layer | Holds | Lives in |
|---|---|---|
| **FPOS Global** | identity · doctrine · relationships · commitments · global learning | `memory/`, `core/STATE/` |
| **Project** | accepted decisions · architecture · constraints · current phase | project docs, `core/INTENT/` |
| **Goal** | plan · status · evidence · blockers · next action | the Goal Object |
| **Skills** | reusable procedures, expert playbooks | `.claude/skills/`, playbooks |
| **Live systems** | current external reality | connectors, tools, HOT_STATE |

Instruction placement follows the same rule:

```
Universal doctrine        → global instructions (CLAUDE.md)
Project governance        → project policy
Goal constraints          → the Goal Object
Repeatable procedure      → a Skill
Machine-enforced limit    → a Hook / guardrail
This request              → the prompt
```

This is what prevents semantic drift, accidental reversals, and repeated context reconstruction. Every agent should not carry every rule; every project should not contaminate every other project.

## 7. Every completed goal upgrades the OS — the Learning Packet

On completion the Goal Steward returns the result **and** a Learning Packet:

```
What worked?
What failed?
What changed?
What should become memory?
What should become a skill?
What could be automated?
What should route differently next time?
What no longer needs James?
```

Then push the capability up the evolution ladder:

```
Manual → Playbook → Specification → Automation → Platform capability → Intelligence
```

That last question — *what no longer needs James?* — is the Sunheart Rule made measurable. See [[feedback-sunheart-rule]].

---

## The upgraded canonical FPOS loop

```
1.  James restores, discerns, and speaks
2.  FPOS captures the signal
3.  The Brain determines meaning and priority
4.  The Router selects the proper level and carrier
5.  A Goal Object is created
6.  A Parent Goal Steward accepts accountability
7.  The harness loads context, policy, skills, tools, and authority
8.  Specialists execute bounded workstreams
9.  Evidence updates the plan
10. The loop continues autonomously
11. James is consulted only at consequential boundaries
12. Reality verifies completion
13. Proof returns to FPOS
14. Memory, skills, routing, and capabilities improve
```

## What FPOS is becoming

Not only *an operating system that knows what matters* — **an operating organization that recognizes what matters, creates durable responsibility for it, carries it to verified completion, and becomes more capable each time.**

---
*Under [[CONSTITUTION]] · beside [[FOUNDATION]] · proof discipline extends [[MTUE]] and [[ACTIVATION_DOCTRINE]] · routing tiers from [[feedback-sunheart-rule]].*
