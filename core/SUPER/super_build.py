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
# STEWARD_LOG is the append-only record of rulings. It is overridable ONLY so that a
# verification run can be pointed somewhere else: on 2026-10-02 two test runs of the
# then-new timezone override appended real-looking rulings (UTC+00 and UTC+5.5) into
# this file, where a reader cannot tell a test from a ruling. A test must not write to
# the record it is testing.
LOG = pathlib.Path(os.environ["SUPER_STEWARD_LOG"]) if os.environ.get("SUPER_STEWARD_LOG") else HERE / "STEWARD_LOG.md"
REDEMPTION = HERE / "REDEMPTION.md"

# Costa Rica is UTC-6 all year (no DST). The Build happens in Rivas, Pérez Zeledón, so
# every date this file stamps is the date THERE, not the date where the process runs.
# A container running UTC is six hours into tomorrow for a quarter of every CR day.
# Default -6: Costa Rica, where this currency's first Build happens. An adopter of the
# pack elsewhere sets SUPER_TZ_OFFSET_HOURS to their own offset — a currency should be
# dated in the place it circulates, not in the place its process happens to run.
_OFF_ENV = os.environ.get("SUPER_TZ_OFFSET_HOURS")
try:
    _OFF = float(_OFF_ENV) if _OFF_ENV is not None else -6.0
except ValueError:
    _OFF = -6.0; _OFF_ENV = None   # garbage ignored: the stamp is Costa Rica again, and says so
CR = datetime.timezone(datetime.timedelta(hours=_OFF))
def cr_today():
    return datetime.datetime.now(CR).date()

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

# A blank is a blank — and so is a word that only looks like an answer. The steward
# grades presence, so a placeholder in a field is the cheapest way to flip a condition
# green without changing anything in the world. (Claude, 2026-10-03)
PLACEHOLDERS = {"—", "-", "--", "---", "unknown", "?", "??", "...", "tbd", "t.b.d",
                "n/a", "na", "none", "nil", "pending", "todo", "to do", "to be decided",
                "to be named", "someone", "somebody", "x", "xx", "xxx", "placeholder"}

def filled(v):
    if not v: return False
    s = str(v).strip().strip(".").lower()
    return bool(s) and s not in PLACEHOLDERS

def _samename(a, b):
    """Loose name equality: punctuation and case don't make a person independent."""
    n = lambda s: re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()
    return bool(n(a)) and n(a) == n(b)

# Finding 8 made the WITNESS's role overlap machine-checkable, because the witness assigns Q.
# But the Card assigns Q and the Pass It On split to "beneficiaries + witness" JOINTLY, and the
# beneficiaries side was never checked against anything — not even for presence beyond non-empty
# (finding 13). So a Build whose beneficiaries are the provider's own people would be graded, in
# part, by the provider: the same defect finding 8 closed, left open one field to the left. It is
# not made a hard fail here: "beneficiaries" is free text, a household member legitimately among
# ten community guests is not fatal, and a fragile split must not veto a real Card. The machine
# names what it can see and hands the judgement to the director, as the witness line already does.
# (Claude, 2026-10-04)
def _benefic_role_clash(card):
    raw = str(card.get("beneficiaries") or "")
    toks = [x.strip() for x in re.split(r"[,;\n]| y | & | and ", raw) if x.strip()]
    out = []
    for tok in toks:
        if not filled(tok): continue
        for role in ("director", "circulator", "provider"):
            if _samename(card.get(role), tok):
                out.append((tok, role))
    return out

def redemption_ok():
    if not REDEMPTION.exists(): return False
    t = REDEMPTION.read_text(encoding="utf-8")
    return "Written by: ______" not in t and re.search(r"(exchanged for|redeem|agreed to accept).*[A-Za-z0-9₡]", t) is not None

def window_line(card):
    """What the Card promised about TIME, read by the grader at last.

    day1/day7 have been in every Build Card since the first template and were read by
    NOTHING: ruling() graded four conditions and a loop count, and render() printed no
    date but today's. So the grader was timeless — a Build's window could lapse and
    every status print would still say only HOLD, forever. BUILD #001's prose window
    (<=7 days, counted from James's 2026-09-03 commitment, i.e. day7 = 2026-09-10)
    lapsed and no machine said a word for 23 days; B-13 asks James to close it or name
    a new day 7, and until now the system could not even tell him which day 7 it meant.
    (Claude, Super Agent — finding 12, 2026-10-03)

    Rule applied: report what is grounded and refuse to compute an expiry out of a date
    nobody wrote. A blank window is named as unmeasurable, never as "in time".
    """
    def _d(s):
        try: return datetime.date.fromisoformat(str(s).strip())
        except Exception: return None
    d1, d7 = card.get("day1", ""), card.get("day7", "")
    a, b = (_d(d1) if filled(d1) else None), (_d(d7) if filled(d7) else None)
    today = cr_today()
    if b:
        n = (today - b).days
        if n > 0:
            return ("EXPIRED", f"EXPIRED — day7 was {b.isoformat()}, today is {today.isoformat()} "
                    f"({n} day{'s' if n != 1 else ''} over). Neither closed nor extended: write a new "
                    f"day7 here, or close the Build as NOT CLOSED and say so.")
        return ("OPEN", f"day1 {a.isoformat() if a else '—'} -> day7 {b.isoformat()} "
                f"({-n} day{'s' if -n != 1 else ''} left)")
    if filled(d7):
        return ("UNREADABLE", f"day7 is {d7!r}, which is not a date (YYYY-MM-DD) — unmeasurable")
    return ("UNDECLARED", "UNDECLARED — day1/day7 blank, so no machine here can say whether this "
            "Build's window has lapsed. Write both as YYYY-MM-DD and the clock becomes checkable; "
            "until then the window is prose only.")

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
    # The witness is not a spectator: the Card assigns Q and the Pass It On split to
    # "beneficiaries + witness". So a witness who is also the director, the circulator or
    # the provider means the Build grades itself. The steward printed the word
    # "independent" for 29 days while testing only that the field was non-empty — an
    # asserted property that was never checked. Role overlap IS machine-checkable, so it
    # is now checked; anything beyond it (a friend, a household member) is the director's
    # to vouch for, and the ruling says so instead of claiming more. (Claude, 2026-10-03)
    ok_ben, ok_wit = filled(c("beneficiaries")), filled(c("witness"))
    clash = [r for r in ("director", "circulator", "provider")
             if ok_wit and _samename(c(r), c("witness"))]
    ben_clash = _benefic_role_clash(card)
    ok2 = ok_ben and ok_wit and not clash
    if ok2:
        why2 = (f"beneficiaries + witness named ({c('witness')} is not the director, "
                "circulator or provider; independence beyond role is the director's word). "
                "Presence is all this machine checks: the Card's own pass test is a meal they "
                "WANTED and felt respected, so whether these people were actually asked is the "
                "director's word too, not something observed here")
    elif clash:
        why2 = (f"witness {c('witness')} is also the {'/'.join(clash)} — the Build would grade "
                "itself; name someone who is none of the three")
    else:
        why2 = f"missing: {'beneficiaries ' if not ok_ben else ''}{'witness' if not ok_wit else ''}".strip()
    if ben_clash:
        why2 += ("; ROLE OVERLAP ON THE BENEFICIARY SIDE — " +
                 ", ".join(f"{who} is also the {role}" for who, role in ben_clash) +
                 ": the Card assigns Q to beneficiaries + witness jointly, so this Build would be "
                 "graded in part by its own " + "/".join(sorted({r for _, r in ben_clash})) +
                 ". Not failed here (free text, and a household member among ten guests is not "
                 "fatal) — the director's word, named out loud instead of passing silently")
    conds.append(("Q path", ok2, why2))
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
    wstate, wline = window_line(card)
    if c("mixed_payment_ok","no").lower()!="no": openq = "Decision 001 — Build touches two currencies"
    elif not redemption_ok(): openq = "REDEMPTION.md is blank — a vendor will ask what SUPER buys; vendor agent is gated until it's filled"
    elif wstate == "EXPIRED": openq = "Window expired — close Build as NOT CLOSED, or write a new day7 (B-13)"
    elif wstate in ("UNDECLARED", "UNREADABLE") and not closed: openq = "day1/day7 unset — the Card's window is prose; no machine can grade its time"
    # ADDITIVE, not another elif: the first version of this put the overlap in the elif chain
    # below the window question, so on BUILD_001 — whose day1/day7 are blank — the overlap was
    # computed, printed in condition 2, and silently absent from the director's open question.
    # A question that only surfaces once an unrelated question is answered is not asked.
    # (Claude, 2026-10-04, same cycle, after observing it)
    if ben_clash:
        note = ("beneficiary/provider role overlap — " +
                ", ".join(f"{w} is also the {r}" for w, r in ben_clash) +
                "; confirm these people may still assign Q, or name others")
        openq = note if openq == "none" else f"{openq} · ALSO: {note}"
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
        # The old text advertised this move as costless ("needs no provider, no
        # infrastructure; closes condition 2 the minute it is written") because the only
        # thing the machine checks is that the field is non-empty. But the Card's pass test
        # is "a meal they WANTED and felt respected", and its own Love section says the
        # beneficiaries "haven't chosen the meal yet" — so each name is a conversation, not a
        # keystroke. Reporting a hard ask as a five-minute one, cycle after cycle, is how a
        # system turns its own stall into an accusation against the human. The witness may be
        # one of the beneficiaries; the Card assigns Q to them jointly. (Claude, 2026-10-03)
        nbm = ("TWO open moves, director-only first — (a) name the beneficiaries and a witness who "
               "is NOT the director, circulator or provider (the witness MAY be one of the "
               "beneficiaries — the Card assigns Q to them jointly — so no eleventh person is "
               "needed; but this is not a form fill: the Card's pass test is a meal they WANTED "
               "and felt respected, so each name costs a conversation, and how many names is set "
               "by the Build's own size — resize the Build and this ask resizes with it, B-13); "
               "then (b) one conversation with one candidate provider; "
               "record their Q2 answer verbatim")
    elif provider_open:
        nbm = "One conversation with one candidate provider; record their Q2 answer verbatim"
    else:
        nbm = "Name the missing people/fields above"
    return status, conds, loop_done, openq, nbm, wline

def render(build_id, status, conds, loop_done, openq, nbm, window="(not computed)"):
    today = cr_today().isoformat()
    tzlabel = f"UTC{_OFF:+03.0f}" if _OFF == int(_OFF) else f"UTC{_OFF:+}"
    if _OFF_ENV is not None: tzlabel += " ·offset from SUPER_TZ_OFFSET_HOURS"
    lines = [f"[SUPER-STEWARD · BUILD-{build_id} · {today} {tzlabel}]", f"STATUS: {status}", "Conditions:"]
    for i,(name,ok,why) in enumerate(conds,1):
        lines.append(f"  {i} {name+':':<11} {'✓' if ok else '✗'} — {why}")
    lines += [f"Loop: {loop_done} / 11", f"Window: {window}",
              f"Open question for the director: {openq}", f"NBM: {nbm}"]
    return "\n".join(lines)

def cmd_status(path, write_log=True):
    path = pathlib.Path(path)
    if not path.exists() and not path.is_absolute(): path = HERE / path.name   # run from anywhere
    if not path.exists(): sys.exit(f"no such card: {path}")
    card, loop_done, q, closed = parse_card(path)
    out = render(card.get("id","?"), *ruling(card, loop_done, q, closed))
    print(out)
    if not write_log:
        print(f"(--no-log: not appended to {LOG.name})"); return
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
    _nolog = "--no-log" in a
    a = [x for x in a if x != "--no-log"]
    if not a or a[0] not in ("status","new","ladder","mint","redeem","passiton","route","swap","conform"): sys.exit(__doc__)
    if a[0]=="status": cmd_status(a[1] if len(a)>1 else HERE/"BUILD_001.md", write_log=not _nolog)
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
CASHOUT = 0.95           # HISTORICAL (Sep 3 design). NOT the payout rule: the haircut was
                         # withdrawn 2026-09-04. Payouts come from redemption_terms() below.
PASS_IT_ON = 0.10        # bonus mint on Q INCREASED and R_co >= 2

def redemption_terms():
    """Read the payout rule out of REDEMPTION.md instead of restating it here.
    The promise is the document of record; a constant in this file is a copy that
    goes stale the moment James edits his own promise (it already did: the 95%
    haircut and the gift card were withdrawn 2026-09-04 and lived on in code for
    29 days). Returns (rate_crc_per_super, deadline_sentence, haircut_fraction).
    Refuses rather than guessing."""
    if not REDEMPTION.exists():
        raise SystemExit("REFUSED — REDEMPTION.md is missing. The steward will not compute a payout it cannot quote.")
    t = REDEMPTION.read_text(encoding="utf-8")
    peg = re.search(r"1\s*SUPER\s*=\s*₡\s*([\d,]+)", t)
    offer = re.search(r"Con\s+(\d+)\s+SUPER.*?₡\s*([\d,]+)", t, re.S)
    if not peg or not offer:
        raise SystemExit("REFUSED — REDEMPTION.md does not state both '1 SUPER = ₡N' and "
                         "'Con N SUPER ... ₡M'. Without both the steward cannot know what a "
                         "holder is owed, and it will not fall back to a figure in this file.")
    peg_crc = int(peg.group(1).replace(",", ""))
    units = int(offer.group(1)); amount = int(offer.group(2).replace(",", ""))
    rate = amount / units
    deadline = re.search(r"(Se entrega[^\n]*)", t)
    deadline = deadline.group(1).strip() if deadline else "(no deadline sentence found in REDEMPTION.md)"
    if peg_crc != PEG_CRC:
        raise SystemExit(f"REFUSED — REDEMPTION.md pegs 1 SUPER = ₡{peg_crc:,} but this script carries "
                         f"₡{PEG_CRC:,}. The document of record wins; fix PEG_CRC before paying anyone.")
    return rate, deadline, (1.0 - rate / peg_crc)
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
    pid = f"{kind.upper()}-{datetime.datetime.now(CR).strftime('%Y%m%dT%H%M%S')}CR"
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
        f"Ledger line: {cr_today()} | treasury | {card.get('circulator') or 'circulator'} | {amount} SUPER | mint for BUILD-{build} | {build} | {card.get('witness') or 'witness'}",
    ], RIGHTS["mint"])

def cmd_redeem(amount, who, build):
    minted, redeemed = ledger_totals()
    if amount > minted - redeemed:
        print(f"REFUSED — {amount} SUPER requested but only {minted - redeemed} outstanding on the ledger."); return
    rate, deadline, haircut = redemption_terms()
    face = amount * PEG_CRC; to_holder = int(amount * rate); to_loop = face - to_holder
    lines = [
        f"Redeem {amount} SUPER from {who} (BUILD-{build})",
        f"Owed to {who}: ₡{to_holder:,} — what REDEMPTION.md promises, read from the file ({rate:g} per SUPER)",
    ]
    if to_loop > 0:
        lines.append(f"White Mountain loop: ₡{to_loop:,} ({haircut*100:.0f}% haircut, as written in REDEMPTION.md)")
    else:
        lines.append("White Mountain loop: ₡0 — the promise is full face value; no haircut is taken from a holder.")
    proposal("redeem", lines + [
        f"Deadline, verbatim from the promise: \u201c{deadline}\u201d  Missed = K4, currency pauses.",
        f"Escrow after: ₡{(minted - redeemed - amount)*PEG_CRC:,} covering {minted - redeemed - amount} SUPER",
        f"Ledger line: {cr_today()} | {who} | treasury | {amount} SUPER | redemption (₡{to_holder:,} to holder + ₡{to_loop:,} loop) | {build} | witness",
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
        f"Ledger line: {cr_today()} | treasury | beneficiaries+witness of {build} | {amt} SUPER | pass-it-on mint (Q INCREASED, R_co={rco}) | {build} | {card.get('witness')}",
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
