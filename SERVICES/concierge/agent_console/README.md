# agent-console

Next.js 14 (App Router) single-pane-of-glass for human agents.

Scope (v1):
- Live conversation feed via WebSocket to `handoff-broker`
- Three-pane layout: queue · active conversation · tool ecosystem
- AI-drafted reply box with edit-to-train loop (emits `agent.draft_edited`)
- Skill passport + earnings tracker for the logged-in agent
- Real-time warm-transfer controls (accept / reject / hand off)

Run: `npm install && npm run dev` (port 3100). Planned in Milestone M3.
