# SUPER — Ledger (append-only; one line per movement; signed by the witness at each Build close)
# date | from | to | amount | purpose | build | witness
# AMOUNT COLUMN FORMAT (added 2026-10-04, finding 18b): the amount is read as the FIRST
# integer in this column — '100 SUPER', '100 SUPER (of 100)' and '1,000 SUPER' all read as
# intended. A column with no leading number ('tbd SUPER') is UNREADABLE, and mint/redeem
# then REFUSE rather than treat it as zero. Write the number first. Only lines with
# 'treasury' in the from/to column move the outstanding total.
# --- internal revolutions (agent services, pre-rung-3: earned in SUPER, unpaid, amount moved = 0; settle when agent wallets open and a human beneficiary has closed the chain) ---
2026-09-03 | super-agent | general-purpose (searcher) | 0 SUPER (earned 3) | provider search: 9 candidates, Pérez Zeledón | 001 | James (witness: read the list)
2026-09-03 | super-agent | super-steward | 0 SUPER (earned 1) | ruling HOLD on BUILD-001 | 001 | —
2026-09-03 | super-agent | super-vendor-agent | 0 SUPER (earned 5) | M1 drafted + sent to La Cocinona (James approved) | 001 | James
2026-09-03 | super-agent | super-build | 0 SUPER (earned 2) | Cards #001/#002, super_build.py, registry | 001 | —
2026-09-03 | james (director) | super-agent | 0 SUPER (earned 1) | orchestration of the above | 001 | James
