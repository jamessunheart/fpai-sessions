export const meta = {
  name: 'self-improvement-swarm',
  description: 'Probe swarm pokes the system for weak points as sharp questions → answer swarm adversarially diagnoses each → weighted intent stream (highest-leverage first) as a build-ready queue for Codex. Schedulable to compound system intelligence.',
  whenToUse: 'Periodic deep self-probe → ranked build intents. The deep/periodic complement to the continuous/shallow council loop. Run after big changes or on a cadence.',
  phases: [
    { title: 'Probe', detail: 'red-team Sonnets crawl each system facet → sharp questions targeting real weak points' },
    { title: 'Diagnose', detail: 'answer Sonnets adversarially confirm-or-refute each weakness, grounded in the real code/state' },
    { title: 'Rank', detail: 'weight confirmed weaknesses into a highest-leverage-first intent stream + build-ready specs' },
  ],
}

const REPO = '/opt/fpai-build/FPAI_Cockpit'

// The north star the swarm optimizes toward — every intent is scored against this.
const SPINE = `SYSTEM SPINE (score every weakness against this):
- Keystone: Allocation Intelligence — route/reason/recurse scarce resources -> max Future Capability.
- CONSTITUTION 8 Laws + AI_PRINCIPLES P1-P9. Coherence theme: kill map!=territory (metric drift, repo!=running,
  merged!=live); render truth from a measured SSOT; honesty-first (no theater/overclaims); default-to-substrate.
- The system compounds when it PROVES improvement, not when it merely merges specs. Bottleneck-first (Law 4).`

// Read-cap discipline (the budget lesson): every agent triages, never reads everything.
const READCAP = `★ BUDGET CAP (obey strictly): read AT MOST ~15 highest-signal files/artifacts fully; title-scan the rest. ` +
  `Run cheap commands (grep/ls/git log/a metric script) over reading everything. Bound your own cost.`

// The facets to probe — each a distinct attack surface, each blind to the others (multi-modal sweep).
const FACETS = [
  { key: 'bugs', lens: 'Unguarded bugs & class-fixes owing',
    where: `${REPO}/core/STATE/BUG_LOG.md, tools/rca/, ops_ledger; look for ROOT-CAUSED-but-PENDING guards, recurring diagnostic_errors, class-fixes never shipped.` },
  { key: 'coherence', lens: 'map != territory drift',
    where: `run tools/governance/metric_coherence.py; check repo!=running (D138 reconciliation), merged!=live (build_status=merged but merged_at NULL / not in git), stale SSOTs vs SSOT_REGISTRY.md.` },
  { key: 'loops', lens: 'Loop efficacy — proof vs burn',
    where: `systemd timers (council/build/rca/self-audit/metabolism); are they producing PROOF or idle-burning? check ops_ledger for wasted wakes, stalled worktrees, empty runs.` },
  { key: 'learning', lens: 'Is the brain actually learning?',
    where: `brain_index.corrections -> L2 dataset, RCA findings -> AI_PRINCIPLES graduation, session_insights growth. Is signal captured LIVE or merely designed?` },
  { key: 'honesty', lens: 'Theater & overclaim (P4)',
    where: `claimed!=wired, false-"merged", inflated status, metrics without source/timestamp. Grep docs/state for confident claims; verify against ground truth.` },
  { key: 'guardrails', lens: 'Security & guardrail integrity',
    where: `PROTECTED_PATHS, secrets in repo/vault, classifier-bypass risks, reversibility/rollback gaps, cost-cap enforcement (BURN_REGISTRY).` },
  { key: 'doctrine-lived', lens: 'Does behavior match the Constitution?',
    where: `default-to-substrate actually happening (substrate_default_catches.jsonl)? bottleneck-first? Are decisions landing on James that shouldn't? Reserved-class discipline.` },
  { key: 'attention-noise', lens: "James's attention — signal vs noise",
    where: `HOT_STATE + surfaces: is the system generating noise? duplicate/stale files, MEMORY.md bloat, redundant loops fragmenting attention (minimum-sufficient principle).` },
]

const PROBE_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['facet', 'questions'],
  properties: {
    facet: { type: 'string' },
    questions: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      required: ['q', 'weakness', 'where'],
      properties: {
        q: { type: 'string', description: 'a sharp, specific question that pokes a real weak point (<=30 words)' },
        weakness: { type: 'string', description: 'the underlying weakness it targets' },
        where: { type: 'string', description: 'file/loop/table where it lives — must be concrete, not hypothetical' },
      },
    } },
  },
}

const DIAGNOSE_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['question', 'is_real', 'severity', 'root_cause', 'proposed_fix', 'reversible', 'effort', 'facet'],
  properties: {
    question: { type: 'string' },
    facet: { type: 'string' },
    is_real: { type: 'boolean', description: 'ADVERSARIAL: confirm only if verified against real code/state; default false if uncertain' },
    severity: { type: 'string', enum: ['low', 'med', 'high'] },
    root_cause: { type: 'string' },
    proposed_fix: { type: 'string', description: 'concrete, buildable fix' },
    reversible: { type: 'boolean', description: 'is the fix reversible + within delegated authority (Law 7)?' },
    effort: { type: 'string', enum: ['S', 'M', 'L'] },
    evidence: { type: 'string', description: 'the ground-truth you checked (command output / file:line)' },
  },
}

const INTENT_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['intents'],
  properties: {
    intents: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      required: ['title', 'priority', 'why', 'build_spec', 'reversible', 'facet'],
      properties: {
        title: { type: 'string', description: '<=10 words' },
        priority: { type: 'number', description: '0-100; impact x leverage x alignment / (cost x risk). Highest = build first.' },
        why: { type: 'string', description: 'one sentence — the weakness it closes + why it matters now' },
        build_spec: { type: 'string', description: 'concrete: what to build, where, what proof looks like — Codex-ready' },
        reversible: { type: 'boolean' },
        facet: { type: 'string' },
        bottleneck: { type: 'boolean', description: 'true if this is the weakest-conversion / limiting constraint (Law 4)' },
      },
    } },
  },
}

// Batched fan-out — fire at most `size` heavy agents per wave to avoid the
// API-529 burst-overload (learned when an 11-agent burst killed 10/11 on run 1).
async function inBatches(items, size, make) {
  const out = []
  for (let i = 0; i < items.length; i += size) {
    const wave = await parallel(items.slice(i, i + size).map(make))
    out.push(...wave)
  }
  return out
}

// ---------- Phase 1: PROBE (red-team swarm) ----------
phase('Probe')
const probes = (await inBatches(FACETS, 3, f => () =>
  agent(
    `You are a red-team Sonnet probing a self-evolving AI system for WEAK POINTS. Be skeptical and specific — poke where it actually hurts.\n\n${SPINE}\n\n${READCAP}\n\n` +
    `YOUR FACET: ${f.lens}\nWhere to look: ${f.where}\n\n` +
    `MISSION: crawl this facet of the REAL system (read files, run grep/git/scripts) and produce 2-5 sharp questions that expose genuine weaknesses — ` +
    `things that are broken, drifting, unproven, theatrical, or leaving capability on the table. Ground every question in something you actually observed. No hypotheticals.`,
    { label: `probe:${f.key}`, phase: 'Probe', model: 'sonnet', schema: PROBE_SCHEMA }
  )
)).filter(Boolean)

const questions = probes.flatMap(p => (p.questions || []).map(q => ({ ...q, facet: p.facet })))
log(`Probe swarm surfaced ${questions.length} weak-point questions across ${probes.length} facets`)

// ---------- Phase 2: DIAGNOSE (answer swarm — adversarial confirm/refute) ----------
phase('Diagnose')
const diagnoses = (await inBatches(questions, 4, item => () =>
  agent(
    `You are a diagnostician Sonnet. A red-team probe raised this weakness question about a self-evolving AI system. ` +
    `Your job is ADVERSARIAL VERIFICATION: confirm it is a REAL weakness only if you verify it against ground truth — otherwise mark is_real=false. Do not accept the premise on faith.\n\n${SPINE}\n\n${READCAP}\n\n` +
    `QUESTION: ${item.q}\nWEAKNESS CLAIMED: ${item.weakness}\nWHERE: ${item.where}\n\n` +
    `MISSION: investigate the real code/state (read the file, run the command, check the table). Decide is_real. If real, give root cause, a concrete buildable fix, whether it's reversible (Law 7), and effort. Cite the ground-truth evidence you checked.`,
    { label: `diagnose:${item.facet}`, phase: 'Diagnose', model: 'sonnet', schema: DIAGNOSE_SCHEMA }
  )
)).filter(Boolean)

const confirmed = diagnoses.filter(d => d && d.is_real)
log(`Diagnosed ${diagnoses.length} → ${confirmed.length} confirmed real weaknesses`)

// ---------- Phase 3: RANK (weighted intent stream — the build queue) ----------
// Feed a TRIMMED view to the ranker — the full confirmed set (verbose root_cause +
// evidence) once overwhelmed the single ranker agent and it returned 0 intents, silently
// dropping 34 real findings (run wru864hcw). Trim + always return `confirmed` as the
// durable fallback so the gold can never be lost at the packaging stage again.
phase('Rank')
const trimmed = confirmed.map(d => ({
  facet: d.facet, severity: d.severity, reversible: d.reversible, effort: d.effort,
  weakness: (d.root_cause || '').slice(0, 220), fix: (d.proposed_fix || '').slice(0, 220),
}))
const stream = await agent(
  `You are the lead prioritizer building a weighted INTENT STREAM (a build queue) for a self-evolving AI system's Codex builder.\n\n${SPINE}\n\n` +
  `Here are the ${trimmed.length} CONFIRMED weaknesses (trimmed) as JSON:\n${JSON.stringify(trimmed, null, 1)}\n\n` +
  `MISSION:\n` +
  `1. Turn each into a build-ready intent with a Codex-ready build_spec (what to build, where, what proof looks like).\n` +
  `2. Score priority 0-100 = impact x leverage x alignment-to-spine / (cost x risk). BOTTLENECK-first (Law 4): the weakest limiting conversion outranks the loudest.\n` +
  `3. DEDUP + MERGE overlapping intents into one. Drop anything low-value or already-solved.\n` +
  `4. Mark reversible (Law 7) and flag the single biggest bottleneck.\n` +
  `You MUST return at least one intent per distinct confirmed weakness that survives dedup. Sorted priority DESC.`,
  { label: 'rank:intent-stream', phase: 'Rank' }
)

const intents = (stream && stream.intents && stream.intents.length) ? stream.intents : []
return {
  intent_stream: intents,
  confirmed,  // durable fallback — never lose the findings even if rank returns empty
  stats: {
    facets: probes.length,
    questions: questions.length,
    diagnosed: diagnoses.length,
    confirmed: confirmed.length,
    intents: intents.length,
    reversible_intents: intents.filter(i => i.reversible).length,
  },
  // Queuing to the build DB is intentionally NOT done here — that arms the build/deploy
  // pipeline (harness-gated). The caller routes reversible intents through
  // constitution_check -> brain_index.decisions (the sanctioned council/self-audit path),
  // and surfaces reserved ones. Output-only workflow; the human/daemon owns the arming.
}
