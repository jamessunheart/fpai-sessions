# Fi-art — Data Model

Backing the master `SPEC.md`. Storage-agnostic (SQLite for v1 on the brain substrate; chain-anchorable later). Every note is a record; the Truth Panel is a *view* of that record, not a separate table.

---

## `creators`
| field | type | notes |
|---|---|---|
| id | uuid pk | |
| handle | text unique | |
| tier | enum | `open` / `verified` / `redeemable_eligible` |
| identity_verified | bool | gate for `verified`+ |
| ownership_attested | bool | art-rights attestation on file |
| covenant_version | text | which Creator Covenant they signed |
| covenant_signed_at | ts | null until signed; minting blocked if null |
| created_at | ts | |

**Rule:** `tier='open'` may only mint `note.type='open'`. Redeemable mint requires `tier='redeemable_eligible'` + `covenant_signed_at` not null.

---

## `notes`
| field | type | notes |
|---|---|---|
| id | uuid pk | |
| creator_id | fk creators | |
| type | enum | `open` / `mirror` / `capacity` / `art` / `access` |
| title | text | |
| media_uri | text | image/asset |
| supply | int | edition size (1 = unique) |
| redeemable | bool | |
| redeemable_for | text | "$100" / "1 hotel night" / "1 massage" / "artwork" / "membership" / null |
| backed_by | enum | `fiat_reserve` / `merchant_capacity` / `physical_art` / `creator_promise` / `none` |
| honored_by | enum | `creator` / `merchant` / `art_holder` / `reserve_partner` |
| expiration | text | `none` / iso-date / booking-window |
| transferable | enum | `yes` / `no` / `restricted` |
| exit_path | enum | `burn_to_redeem` / `book_service` / `claim_physical` / `no_exit` |
| risk_label | enum | `art_only` / `creator_backed` / `capacity_backed` / `reserve_backed` |
| legal_status | const | always `not_legal_tender` |
| educational_theme | text | what this teaches about money |
| status | enum | `live` / `frozen` / `delisted` / `impaired` / `redeemed` |
| created_at | ts | |

**Integrity rules (enforced at mint, surfaced in Truth Panel):**
- `redeemable=false` ⇒ `backed_by='none'`, `risk_label='art_only'`, `exit_path='no_exit'`.
- `risk_label='reserve_backed'` requires a `reserve_records` row tier 1 **or** a verified reserve vouch.
- A **social vouch may never raise** `risk_label` above `creator_backed`.
- Money-claim scanner runs on `title`+`educational_theme`+`redeemable_for`; blocks "yield/profit/guaranteed/APY" unless creator is reserve-verified.

---

## `truth_panel` (view, not a table)
Computed from a `notes` row — the 11 fields in SPEC §4. Rendered on every note page. Never editable independently of the underlying record (no silent edits).

---

## `reserve_records`
| field | type | notes |
|---|---|---|
| id | uuid pk | |
| note_id | fk notes | |
| reserve_tier | int | 1–5 per Redemption Confidence Stack |
| kind | enum | `primary_reserve` / `issuer_stake` / `funded_vouch` / `mutual_pool` / `impaired` |
| amount | numeric | locked value |
| currency | text | USD / token / capacity-unit |
| verified | bool | gate for counting as backing |
| custodian | text | who holds it |
| created_at | ts | |

---

## `vouches`
| field | type | notes |
|---|---|---|
| id | uuid pk | |
| note_id | fk notes | |
| voucher_id | fk creators/users | |
| kind | enum | `social` / `funded` / `capacity` / `reserve` |
| counts_as_backing | bool | derived: social=false, funded=true, reserve=true-if-verified, capacity=conditional |
| locked_value | numeric | null for social |
| created_at | ts | |

---

## `redemptions`
| field | type | notes |
|---|---|---|
| id | uuid pk | |
| note_id | fk notes | |
| redeemer_id | fk users | |
| method | enum | `burn_to_redeem` / `book_service` / `claim_physical` |
| fulfilled_by | fk creators | who performed |
| status | enum | `requested` / `fulfilled` / `disputed` / `replaced` / `impaired` |
| fulfilled_at | ts | |

**Phase 3 = claims-only:** platform records the redemption + status; the honoring party performs off-platform (their Stripe, their hotel, their service). Platform custodies no funds in Phase 3 → keeps money-transmitter exposure off the table until Phase 4 reserve partners are formal.

---

## `covenant_signatures`
| field | type | notes |
|---|---|---|
| creator_id | fk | |
| version | text | |
| signed_at | ts | |
| ip / agent | text | audit |

---

## `dmca_actions`
| field | type | notes |
|---|---|---|
| id | uuid pk | |
| note_id | fk notes | |
| action | enum | `takedown` / `freeze` / `delist` / `impair` / `restore` |
| reason | text | |
| actor | text | DMCA agent / moderator |
| created_at | ts | |

Designated DMCA agent info stored in platform config; surfaced on a public `/dmca` page (§512 requirement).
