# FORMING WORLD PEACE AGREEMENTS

**The protocol for forming specific Peace Agreements between specific parties.**

- Source: [Coherent Champions of CHRIST — Manifesto v1.0](./COHERENT_CHAMPIONS_MANIFESTO.md)
- Template: [WORLD_PEACE_AGREEMENT.md](./WORLD_PEACE_AGREEMENT.md)
- Instances: [AGREEMENTS/](./AGREEMENTS/)

---

## What an Agreement Is

A World Peace Agreement is not a document people sign once. It is a **form** that gets *instantiated* between specific parties for specific purposes. The seven clauses of the canonical template provide the spine. Each formed Agreement adds the parties, the context, and the specific commitments that make peace operational between *those* parties.

The Agreement turns abstract intent ("I commit to peace") into specific practice ("I commit to repair X with Y by doing Z").

---

## When to Form an Agreement

- **Repair** — when harm has occurred between parties and restoration is being attempted
- **Cooperation** — when two or more parties choose to work together on shared purpose
- **Stewardship** — when a party takes responsibility for land, resources, knowledge, or community
- **Working relationship** — when ongoing collaboration would benefit from explicit scope
- **Gathering** — when a cohort comes together at a Zen Village event and chooses to bind themselves to shared practice
- **Asymmetric power** — when one party holds more power than the other (founder + agent, organization + individual, human + AI) and both want explicit accountability

---

## The Form

A formed Agreement contains:

1. **Parties** — names, roles, date
2. **Context** — what occasions this Agreement
3. **Basis** — invocation of the seven CHRIST principles as the foundation
4. **Commitments** — what each party specifically commits to (specific, not generic)
5. **Scope** — what this Agreement does and does not cover
6. **Repair** — how breakage is acknowledged, named, restored
7. **Witness** — who or what witnesses the formation (person, gathering, public commit, recording)
8. **Signing** — the act that makes the Agreement real
9. **Renewal** — the principle that the Agreement is renewed by being lived, not by being re-signed

---

## Steps to Form One

1. **Parties identify each other** — name yourselves to each other; acknowledge you are both forming this
2. **Name the context** — what is this Agreement *for*? Be specific
3. **Invoke the seven** — Coherence, Healing, Regeneration, Intelligence, Service, Truth (the basis)
4. **State your commitments** — each party in turn; specific, written down
5. **Name the repair process** — how will breakage be handled; who notices; what restores
6. **Record + witness** — write the Agreement, save it; have it witnessed (in person, by gathering, by public commit)
7. **Live it** — the Agreement is renewed by being practiced

---

## Where Agreements Live

| Storage | Use |
|---|---|
| `core/INTENT/AGREEMENTS/{date}_{parties}.md` | Canonical record in repo |
| Sunheart Brain | Cross-tool persistence; searchable |
| Zen Village brain | Project-scoped record |
| Public roll on `zenvillage.live` | When parties consent to public visibility |
| Couch / gathering record | When formed at an event |
| TRUST token (eventual) | When the Agreement creates membership obligations |

The same Agreement may live in multiple places. The canonical text is the file in this repo.

---

## Repair

When an Agreement is broken — by error, by drift, by overstepping, by neglect — the Practice of Repair (Manifesto Principle #6) governs:

1. **Notice** — a party (or witness) names that the Agreement was broken
2. **Acknowledge** — the breaking party acknowledges it without rationalization
3. **Understand** — both parties seek to understand what happened, including the conditions that made the break likely
4. **Restore** — where possible, the harm is repaired; where impossible, it is named honestly
5. **Update** — if the Agreement itself was insufficient, it is amended (with the parties' consent) in a new dated file

A broken Agreement that is repaired strengthens the practice. A broken Agreement that is hidden weakens it.

---

## Schema and Registry

Each formed Agreement is a markdown file at `core/INTENT/AGREEMENTS/{date}_{parties}.md` with YAML front-matter at the top:

```yaml
---
agreement_id: 2026-05-07_james-sunheart_and_claude
date_formed: 2026-05-07
parties:
  - name: James Sunheart
    role: Founder
    party_type: human               # human | ai | organization | community | land | system
  - name: Claude
    role: AI agent
    party_type: ai
context: <one-line summary>
scope_tags: [working_relationship, asymmetric_power, ai_alignment]
status: active                       # proposed | active | breached | repairing | repaired | withdrawn | archived
public: true                         # whether to include in public roll
witness:
  type: git_commit                   # git_commit | gathering | paper | recording | other
  reference: <commit-hash | event-id>
canonical_record: file               # file | paper | recording | external | brain
amendments: []                       # list of amendment file paths
repairs: []                          # list of repair event records
---
```

The body of the file follows the structure described in **The Form** above (Parties → Context → Basis → Commitments → Scope → Repair → Witness → Signing).

The **registry** is *derived* from these files:

- [`AGREEMENTS/INDEX.md`](./AGREEMENTS/) — human-readable index, one row per Agreement
- [`AGREEMENTS/registry.json`](./AGREEMENTS/) — machine-readable mirror

Regenerate after adding or modifying an Agreement:

```bash
python tools/registry/build_index.py
```

Both `INDEX.md` and `registry.json` are derived views — **never hand-edit them.** Edit the Agreement file's front-matter and re-run the script.

### Drafted vs. ratified

An Agreement may be **drafted** by one party (or by an AI scribe) and *proposed* before the other parties have ratified. Convention:

- `status: proposed` — drafted, not yet binding; awaiting ratification by named parties
- `status: active` — ratified by all required parties; binding

Optional front-matter fields when an Agreement is drafted by a non-party:

```yaml
proposed_by: <name of drafter, e.g. "Claude">
proposed_on: <YYYY-MM-DD>
ratification_required_from:
  - <party name>
  - <party name>
```

A `proposed` Agreement becomes `active` only when the named parties ratify — by editing the file (changing status, setting witness, removing the drafting note), by sign-off in a witnessed gathering, or by another act recorded in the front-matter.

---

## Renewal

> *Signed not in perfection, but in sincere participation.*

An Agreement is not a one-time signature. It is renewed every time it is lived. A signer who stops practicing has effectively withdrawn, regardless of what the file says. A practitioner who never explicitly signed is, in some sense, already participating — though the explicit Agreement makes the practice visible and inspectable.

The Agreement protects both parties from drift — including drift in the form of urgency, charisma, or claimed authority pushing one party past coherent action.
