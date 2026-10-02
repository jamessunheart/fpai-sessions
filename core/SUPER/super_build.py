#!/usr/bin/env python3
"""Super Build — the working loop. Reads a Build Card, applies the steward's four
release conditions, prints the ruling, appends it to STEWARD_LOG.md.

  python3 super_build.py status BUILD_001.md      # steward ruling (HOLD/READY/CLOSED)
  python3 super_build.py new 002 "Second hop"     # new card from template
  python3 super_build.py ladder                   # where each Build stands

Never moves funds. Never invents a field. A blank is a blank.
"""
import re, sys, os, datetime, pathlib

HERE = pathlib.Path(__file__).parent
LOG = HERE / "STEWARD_LOG.md"
REDEMPTION = HERE / "REDEMPTION.md"

def parse_card(path):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    m = re.search(r"```card\n(.*?)```", text, re.S)
    if not m:
        sys.exit(f"{path}: no ```card block — use TEMPLATE_BUILD_CARD.md")
    card = {}
    for line in m.group(1).splitlines():
        line = line.split("#", 1)[0].rstrip()
        if ":" in line:
            k, v = line.split(":", 1)
            card[k.strip()] = v.strip()
    loop_done = len(re.findall(r"^- \[x\]", text, re.M | re.I))
    q = re.search(r"^Q:\s*(INCREASED|UNCHANGED|DECREASED)", text, re.M)
    closed = bool(q) and "## Close" in text and text.split("## Close",1)[1].strip().count("\n") >= 9
    return card, loop_done, q.group(1) if q else None, closed

def filled(v): return bool(v) and v not in ("—", "-", "unknown", "?")

def redemption_ok():
    if not REDEMPTION.exists(): return False
    t = REDEMPTION.read_text(encoding="utf-8")
    return "Written by: ______" not in t and re.search(r"(exchanged for|redeem|agreed to accept).*[A-Za-z0-9₡]", t) is not None

def ruling(card, loop_done, q, closed):
    c = card.get
    conds = []
    # 1 provider + verbatim next-use
    if filled(c("provider")) and filled(c("provider_q2_verbatim")):
        conds.append(("Provider", True, f"{c('provider')} — Q2: \"{c('provider_q2_verbatim')}\""))
    elif filled(c("provider")):
        conds.append(("Provider", False, f"{c('provider')} named but no verbatim answer to 'what would you do with the SUPER?' — FAVOR-NOT-EXCHANGE risk"))
    else:
        conds.append(("Provider", False, "no provider named"))
    # 2 Q path
    ok2 = filled(c("beneficiaries")) and filled(c("witness"))
    conds.append(("Q path", ok2, "beneficiaries + independent witness named" if ok2 else
                  f"missing: {'beneficiaries ' if not filled(c('beneficiaries')) else ''}{'witness' if not filled(c('witness')) else ''}".strip()))
    # 3 place + test
    ok3 = filled(c("place")) and filled(c("test_question")) and c("place_has_existing_currency","").lower()=="no"
    conds.append(("Place/test", ok3, f"{c('place')} — {c('test_question')}" if ok3 else
                  "place not named" if not filled(c("place")) else
                  "place_has_existing_currency must be 'no' for this rung" if c("place_has_existing_currency","").lower()!="no" else "test question missing"))
    # 4 max loss + stop
    ok4 = filled(c("max_loss_super")) and filled(c("max_loss_hours")) and filled(c("stop_caller"))
    conds.append(("Max loss", ok4, f"{c('max_loss_super')} SUPER / {c('max_loss_hours')} h, stop: {c('stop_caller')}" if ok4 else "max loss and/or stop-caller not set"))
    status = "CLOSED" if closed else ("READY" if all(ok for _,ok,_ in conds) else "HOLD")
    # open question
    openq = "none"
    if c("mixed_payment_ok","no").lower()!="no": openq = "Decision 001 — Build touches two currencies"
    elif not redemption_ok(): openq = "REDEMPTION.md is blank — a vendor will ask what SUPER buys; vendor agent is gated until it's filled"
    # NBM ordering rule (ledger): "the move that lets reality grade the system soonest goes first."
    # Condition 2 (beneficiaries + witness) depends ONLY on the director — it is gradeable the
    # minute it is filled, and the Card's own pass test is "a meal they WANTED", so the
    # beneficiaries are upstream of any concrete provider ask. The old chain could never emit it
    # while a provider was unnamed, so for 29 days the steward named only the move that depends
    # on a stranger. Both are now reported, director-only first. (Claude, 2026-10-02)
    director_only = [name for name, ok, _ in conds if not ok and name == "Q path"]
    provider_open = not conds[0][1]
    if status == "READY":
        nbm = "Hand to director for human approval; nothing releases until James says so"
    elif status == "HOLD" and loop_done >= 8:
        nbm = "Fill the Close section and Q"
    elif director_only and provider_open:
        nbm = ("TWO open moves, director-only first — (a) name the beneficiaries and an independent "
               "witness (needs no provider, no vendor reply, no infrastructure; closes condition 2 "
               "the minute it is written, and makes the provider ask concrete: a meal these people "
               "actually want); then (b) one conversation with one candidate provider; "
               "record their Q2 answer verbatim")
    elif provider_open:
        nbm = "One conversation with one candidate provider; record their Q2 answer verbatim"
    else:
        nbm = "Name the missing people/fields above"
    return status, conds, loop_done, openq, nbm

def render(build_id, status, conds, loop_done, openq, nbm):
    today = datetime.date.today().isoformat()
    lines = [f"[SUPER-STEWARD · BUILD-{build_id} · {today}]", f"STATUS: {status}", "Conditions:"]
    for i,(name,ok,why) in enumerate(conds,1):
        lines.append(f"  {i} {name+':':<11} {'✓' if ok else '✗'} — {why}")
    lines += [f"Loop: {loop_done} / 11", f"Open question for the director: {openq}", f"NBM: {nbm}"]
    return "\n".join(lines)

def cmd_status(path):
    path = pathlib.Path(path)
    if not path.exists() and not path.is_absolute(): path = HERE / path.name   # run from anywhere
    if not path.exists(): sys.exit(f"no such card: {path}")
    card, loop_done, q, closed = parse_card(path)
    out = render(card.get("id","?"), *ruling(card, loop_done, q, closed))
    print(out)
    with LOG.open("a", encoding="utf-8") as f: f.write("\n" + out + "\n")

def cmd_new(num, title):
    dst = HERE / f"BUILD_{num}.md"
    if dst.exists(): sys.exit(f"{dst} exists")
    t = (HERE/"TEMPLATE_BUILD_CARD.md").read_text(encoding="utf-8").replace("#NNN", f"#{num}").replace("id: NNN", f"id: {num}").replace("<intention in five words>", title)
    dst.write_text(t, encoding="utf-8"); print(f"created {dst.name} — fill the card block, then: python3 super_build.py status {dst.name}")

def cmd_ladder():
    for p in sorted(HERE.glob("BUILD_*.md")):
        try:
            card, loop_done, q, closed = parse_card(p)
            status = ruling(card, loop_done, q, closed)[0]
            print(f"{p.name:<14} {status:<7} loop {loop_done}/11  Q={q or '—'}  {card.get('intention','')[:50]}")
        except SystemExit as e:
            print(f"{p.name:<14} (no card block)")

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("status","new","ladder","mint","redeem","passiton","route","swap","conform"): sys.exit(__doc__)
    if a[0]=="status": cmd_status(a[1] if len(a)>1 else HERE/"BUILD_001.md")
    elif a[0]=="new": cmd_new(a[1], " ".join(a[2:]) or "untitled")
    elif a[0]=="ladder": cmd_ladder()

# ---------------------------------------------------------------------------
# Payment / redemption distribution — AI computes, rights decide.
#   python3 super_build.py mint 001 100          # proposes minting against a READY card
#   python3 super_build.py redeem 100 "La Cocinona de Pueblo" 001
#   python3 super_build.py passiton 001          # proposes the 10% mint on Q INCREASED & R_co>=2
# Every command prints a PROPOSAL with who must approve. Nothing moves until a
# human with that right writes APPROVED <id> into LEDGER.md. The AI never holds
# the right to move value; it holds the right to compute it exactly.
# ---------------------------------------------------------------------------
PEG_CRC = 400            # 1 SUPER = ₡400 at issuance
CASHOUT = 0.95           # redemption returns 95%; 5% → White Mountain loop
PASS_IT_ON = 0.10        # bonus mint on Q INCREASED and R_co >= 2
RIGHTS = {               # who may approve what (the director drew these)
    "mint":     "director",
    "redeem":   "director",      # until transfer; then: stewardship circle
    "passiton": "witness+director",
}
LEDGER = HERE / "LEDGER.md"

def ledger_totals():
    minted = redeemed = 0
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or "|" not in line: continue
            f = [x.strip() for x in line.split("|")]
            if len(f) < 5: continue
            try: amt = int(re.sub(r"[^\d]", "", f[3]) or 0)
            except ValueError: continue
            if f[1].lower() == "treasury": minted += amt
            if f[2].lower() == "treasury": redeemed += amt
    return minted, redeemed

def proposal(kind, lines, approver):
    pid = f"{kind.upper()}-{datetime.datetime.now().strftime('%Y%m%dT%H%M%S')}"
    print(f"[PROPOSAL {pid}] — computed by super-steward; approval right: {approver}")
    for l in lines: print("  " + l)
    print(f"  To execute: a human with the '{approver}' right appends 'APPROVED {pid}' to LEDGER.md and moves the colones. The AI does not.")
    return pid

def cmd_mint(build, amount):
    card, loop_done, q, closed = parse_card(HERE / f"BUILD_{build}.md")
    status = ruling(card, loop_done, q, closed)[0]
    if status != "READY":
        print(f"REFUSED — BUILD-{build} is {status}, not READY. Run: python3 super_build.py status BUILD_{build}.md"); return
    minted, redeemed = ledger_totals()
    escrow_needed = amount * PEG_CRC
    proposal("mint", [
        f"Mint {amount} SUPER against BUILD-{build} ({card.get('intention','')[:60]})",
        f"Escrow required BEFORE mint: ₡{escrow_needed:,} into the named SUPER escrow (1 SUPER = ₡{PEG_CRC})",
        f"Outstanding after mint: {minted - redeemed + amount} SUPER (escrow must cover ₡{(minted - redeemed + amount)*PEG_CRC:,})",
        f"Ledger line: {datetime.date.today()} | treasury | {card.get('circulator') or 'circulator'} | {amount} SUPER | mint for BUILD-{build} | {build} | {card.get('witness') or 'witness'}",
    ], RIGHTS["mint"])

def cmd_redeem(amount, who, build):
    minted, redeemed = ledger_totals()
    if amount > minted - redeemed:
        print(f"REFUSED — {amount} SUPER requested but only {minted - redeemed} outstanding on the ledger."); return
    face = amount * PEG_CRC; to_holder = int(face * CASHOUT); to_loop = face - to_holder
    proposal("redeem", [
        f"Redeem {amount} SUPER from {who} (BUILD-{build})",
        f"Face value ₡{face:,} → gift card / colones to {who}: ₡{to_holder:,} ({int(CASHOUT*100)}%)",
        f"White Mountain loop (witness pay, next Build): ₡{to_loop:,} (5%)",
        f"Deadline: within 7 days of request (promise in REDEMPTION.md). Missed deadline = K4, currency pauses.",
        f"Escrow after: ₡{(minted - redeemed - amount)*PEG_CRC:,} covering {minted - redeemed - amount} SUPER",
        f"Ledger line: {datetime.date.today()} | {who} | treasury | {amount} SUPER | redemption (₡{to_holder:,} card + ₡{to_loop:,} loop) | {build} | witness",
        f"Note: R_co for this SUPER = number of hands before this line. Record it on the Card.",
    ], RIGHTS["redeem"])

def cmd_passiton(build):
    card, loop_done, q, closed = parse_card(HERE / f"BUILD_{build}.md")
    text = (HERE / f"BUILD_{build}.md").read_text(encoding="utf-8")
    rco = re.search(r"R_co:\s*(\d+)", text)
    rco = int(rco.group(1)) if rco else 1
    if not closed or q != "INCREASED" or rco < 2:
        print(f"REFUSED — pass-it-on mint requires CLOSED + Q INCREASED + R_co>=2. Now: closed={closed}, Q={q}, R_co={rco}"); return
    amt = int(int(card.get("super_committed", 0)) * PASS_IT_ON)
    proposal("passiton", [
        f"Mint {amt} SUPER (10% of BUILD-{build}) as new money created by verified good",
        f"Split: beneficiaries ({card.get('beneficiaries')}) and witness ({card.get('witness')}) — never circulator, never treasury",
        f"Escrow required BEFORE mint: ₡{amt*PEG_CRC:,} from the current tranche",
        f"Ledger line: {datetime.date.today()} | treasury | beneficiaries+witness of {build} | {amt} SUPER | pass-it-on mint (Q INCREASED, R_co={rco}) | {build} | {card.get('witness')}",
    ], RIGHTS["passiton"])

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] in ("mint", "redeem", "passiton"):
    a = sys.argv[1:]
    if a[0] == "mint": cmd_mint(a[1], int(a[2]))
    elif a[0] == "redeem": cmd_redeem(int(a[1]), a[2], a[3] if len(a) > 3 else "001")
    else: cmd_passiton(a[1])

# ---------------------------------------------------------------------------
# Interchangeability — the Super Agent chooses agent / model / tools per role.
#   python3 super_build.py route steward                # show the current choice
#   python3 super_build.py swap steward model haiku     # change it; rewrites the agent's frontmatter; logs the swap
#   python3 super_build.py swap vendor agent my-other-agent
# The Cards, ledger, rights, and four conditions never change when a role is re-routed.
# ---------------------------------------------------------------------------
import json
REG = HERE / "registry.json"
AGENTS_DIR = HERE.parent.parent / ".claude" / "agents"

def cmd_route(role):
    reg = json.loads(REG.read_text(encoding="utf-8"))
    r = reg["roles"].get(role)
    if not r: sys.exit(f"unknown role {role}; roles: {', '.join(reg['roles'])}")
    print(f"{role}: agent={r['agent']} model={r['model']} tools={','.join(r['tools'])} skills={','.join(r['skills']) or '-'} fallback={r['fallback']}\n  why: {r['why']}")

def cmd_swap(role, field, value):
    reg = json.loads(REG.read_text(encoding="utf-8"))
    r = reg["roles"].get(role)
    if not r: sys.exit(f"unknown role {role}")
    if field not in ("agent", "model", "tools", "skills"): sys.exit("field must be agent|model|tools|skills")
    old = r[field]
    r[field] = value.split(",") if field in ("tools", "skills") else value
    reg["swap_log"].append({"when": datetime.datetime.now().isoformat(timespec="seconds"), "role": role, "field": field, "from": old, "to": r[field], "by": "super-agent"})
    REG.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    # apply model/tools to the agent definition's frontmatter so the swap is real, not a note
    agent_md = AGENTS_DIR / f"{r['agent']}.md"
    if field in ("model", "tools") and agent_md.exists():
        t = agent_md.read_text(encoding="utf-8")
        line = f"{field}: {', '.join(r[field]) if field=='tools' else r[field]}"
        t2 = re.sub(rf"^{field}:.*$", line, t, count=1, flags=re.M)
        agent_md.write_text(t2, encoding="utf-8")
        print(f"applied to {agent_md.name}: {line}")
    print(f"swapped {role}.{field}: {old} → {r[field]} (logged)")

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] in ("route", "swap"):
    a = sys.argv[1:]
    if a[0] == "route": cmd_route(a[1])
    else: cmd_swap(a[1], a[2], a[3])

# ---------------------------------------------------------------------------
# Conformance — "agents that work according to system design".
#   python3 super_build.py conform ../../.claude/agents/super-steward.md [more.md ...]
# An agent the Super Agent builds or distributes must carry the design in its own text.
# ---------------------------------------------------------------------------
DESIGN = [
  ("never moves value",        r"never (move|moves|hold|holds|promise)[^.\n]*(fund|value|credit|colones|SUPER)"),
  ("never assigns Q",          r"(never|not)[^.\n]*assign[^.\n]*Q|Q[^.\n]*(never|not)[^.\n]*(you|self|circulator|doer)"),
  ("favor is a no",            r"favor[^.\n]*(no|not[^.\n]*exchange)|FAVOR-NOT-EXCHANGE"),
  ("humans direct / no sovereignty", r"[Hh]umans direct|support[^.\n]*sovereignty"),
  ("READY is not release",     r"READY[^.\n]*(not|never|≠)[^.\n]*release|does not release|do not release"),
  ("never fabricates",         r"(never|not)[^.\n]*(invent|fabricat)"),
  ("Never Be Mean / no nag / no pressure", r"[Nn]ever [Bb]e [Mm]ean|never nag|[Nn]o pressure|[Ss]often a HOLD"),
]
def cmd_conform(paths):
    ok_all = True
    for path in paths:
        t = pathlib.Path(path).read_text(encoding="utf-8")
        missing = [name for name, rx in DESIGN if not re.search(rx, t)]
        disclose = bool(re.search(r"(disclos|it is an AI|soy un asistente de inteligencia artificial|pose as a human)", t, re.I))
        talks = bool(re.search(r"(vendor|provider|message|conversation|customer)", t, re.I))
        if talks and not disclose: missing.append("discloses it is an AI (talks to people)")
        status = "CONFORMS" if not missing else "NONCONFORMING"
        ok_all &= not missing
        print(f"{pathlib.Path(path).name:<26} {status}" + ("" if not missing else " — missing: " + "; ".join(missing)))
    print("all conform" if ok_all else "fix before distributing")
    return ok_all

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "conform":
    cmd_conform(sys.argv[2:] or sorted(str(p) for p in (HERE.parent.parent/".claude"/"agents").glob("super-*.md")))
