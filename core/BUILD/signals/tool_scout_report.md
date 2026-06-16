# Tool Scout Report

**Generated:** 2026-06-16T22:28:19Z
**Focus:** self-standing FPOS build loop tools and model replacements
**Research cost:** $0.00 (cap $1.50)
**Mode:** review-gated ranking only; no installs, purchases, deploys, secrets, or automatic adoption.

## Top Candidates

| Score | Verdict | Candidate | Source | Replaces |
|---:|---|---|---|---|
| 13 | adopt-spec | [LiteLLM Proxy](https://github.com/BerriAI/litellm) | github | hand-coded provider routing |
| 12 | pilot-spec | [Claude Code Skills](https://docs.anthropic.com/) | ai-tool-drop | ad hoc repeated prompts |
| 5 | watch | [Graphiti](https://github.com/getzep/graphiti) | github | flat episodic memory search for entity/time recall |

## Notes

### LiteLLM Proxy
- **Summary:** Provider abstraction, fallback, budget, and observability layer for model calls.
- **Proposed use:** Review as a future Resource Discipline Gate component for paid API calls.
- **Score inputs:** leverage 9, maturity 8, cost 5, risk 4
- **Evidence:** review source manually before adoption

### Claude Code Skills
- **Summary:** Reusable task instructions packaged as skills for repeatable agent workflows.
- **Proposed use:** Mirror stable FPOS operating workflows into small repo-local skills after they prove useful.
- **Score inputs:** leverage 8, maturity 7, cost 3, risk 3
- **Evidence:** review source manually before adoption

### Graphiti
- **Summary:** Temporal knowledge graph pattern for AI memory over entities, events, and relationships.
- **Proposed use:** Pilot against one non-sensitive repo-local stream before any memory migration.
- **Score inputs:** leverage 8, maturity 6, cost 7, risk 5
- **Evidence:** review source manually before adoption
