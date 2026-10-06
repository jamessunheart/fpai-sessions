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
    # The loop counter used to count EVERY checked box anywhere in the Card. BUILD_001
    # carries 15 boxes: 11 loop steps and the 4 council pass/fail points (finding 17). So
    # the first time the director ticked "Provider understood SUPER and accepted freely"
    # the steward would have reported loop 1/11 with no loop step done — a progress number
    # inflated by a grade. Measured, not supposed: 15 boxes in BUILD_001, 11 in BUILD_002.
    # Scoped to the "## Loop" section; Cards without one keep the old whole-file count so
    # nothing silently reads zero. (Claude, 2026-10-04, finding 17)
    _loopsec = re.search(r"^##[ \t]*Loop[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    loop_done = len(re.findall(r"^- \[x\]", _loopsec.group(1) if _loopsec else text, re.M | re.I))
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
# FINDING 28 (Claude, 2026-10-06) — AN EXCLUSION RULE IS ONLY AS REAL AS THE FIELD IT NAMES.
# Two independence tests built by findings 8 and 13 — the witness clash above and
# _benefic_role_clash below — both iterate ("director", "circulator", "provider"). _samename
# returns False the moment its first argument is blank, and `circulator:` was EMPTY in every Card
# that exists (BUILD_001, BUILD_002, the template). So for the whole life of this system the
# circulator arm of both tests could not fire: a Build could be graded by the very party that
# circulated it and no machine here would have said a word. The printed NBM told the director the
# witness must not be "the director, circulator or provider" — naming a role no Card defined.
# This function makes the hole visible on every status run instead of leaving it silent.
def role_fields_blank(card):
    """Role fields that the independence rules exclude but no Card names — the rules that
    reference them are vacuous until these are filled."""
    return [r for r in ("director", "circulator", "provider") if not filled(card.get(r))]

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

_ES_MONTHS = {"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,"julio":7,
              "agosto":8,"setiembre":9,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12}

def redemption_expiry_line():
    """What the PROMISE says about TIME, read by the grader at last.

    window_line() reads the BUILD's clock. Nothing ever read the INSTRUMENT's.
    REDEMPTION.md has carried "Vale hasta el 31 de diciembre de 2026" in James's name
    since 2026-09-03; it is in M2 (delivered to a provider), in M-NUDGE-2 (drafted), and
    in DECISION_BOT.md. No file, no code and twenty-six cycles ever counted the days left
    on it, and no document anywhere says what happens to unredeemed SUPER on the far side
    of that date. A currency with an expiry nobody counts is a currency whose last day
    arrives as a surprise to its holder. (Claude, Super Agent — finding 27, 2026-10-06)

    Reports only what REDEMPTION.md states. Never invents a date, never extends one.
    """
    if not REDEMPTION.exists():
        return ("NO FILE", "REDEMPTION.md absent — the instrument has no written validity at all")
    t = REDEMPTION.read_text(encoding="utf-8")
    d = None
    m = re.search(r"hasta el\s+(\d{1,2})\s+de\s+([a-zA-Zéí]+)\s+de\s+(\d{4})", t)
    if m and m.group(2).lower() in _ES_MONTHS:
        try: d = datetime.date(int(m.group(3)), _ES_MONTHS[m.group(2).lower()], int(m.group(1)))
        except Exception: d = None
    if d is None:
        m = re.search(r"(?:valid|vale)[^\n]{0,40}?(\d{4}-\d{2}-\d{2})", t, re.I)
        if m:
            try: d = datetime.date.fromisoformat(m.group(1))
            except Exception: d = None
    if d is None:
        return ("UNSTATED", "no validity date readable in REDEMPTION.md — unmeasurable, not unlimited")
    n = (d - cr_today()).days
    if n < 0:
        return ("EXPIRED", f"EXPIRED — the promise read 'vale hasta {d.isoformat()}', {-n} day(s) ago. "
                "Any SUPER still held is a claim on a lapsed promise. This is the director's to answer.")
    if n == 0:
        return ("LAST DAY", f"LAST DAY — {d.isoformat()} is today; after 3pm CR same-day redemption is gone")
    return ("OPEN", f"{d.isoformat()} — {n} day(s) left on the promise. UNANSWERED (B-24): what happens "
            "to SUPER a holder has not redeemed by then. Any new day7 must fall inside this.")

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

def grade_line(text):
    """What the Card promised about the GRADE, read by the grader at last.

    Gemini's independent council answer (#11, 2026-09-03) is logged in NBM.md as DONE,
    with its one required change: replace MORE ALIVE as the arbiter of Q with a concrete
    four-point pass/fail. The checklist WAS written into BUILD_001.md the same day, under
    a header that says "James adopts or strikes" -- and then read by NO code in this file.
    ruling() grades four RELEASE conditions (may this Build start?) plus a loop count and,
    since finding 12, a window. Nothing ever looked at the four boxes that decide whether
    the Build PASSED. So a Build could reach CLOSED with every release condition green and
    its own council-recommended grade entirely untouched, and every status print would
    look complete. Same shape as finding 12: a promise kept in prose and in no machine.
    (Claude, Super Agent -- finding 17, 2026-10-04)

    Rule applied, and the limit on it: this function REPORTS, it does not grade. The
    Card's header hands adoption to James; a machine that quietly turned an unadopted
    council recommendation into a hard gate would be converting support into sovereignty.
    So the state is named out loud and the decision stays his.
    """
    m = re.search(r"^##[ \t]*Pass/fail[^\n]*\n(.*?)(?=^## |\Z)", text or "", re.S | re.M)
    if not m:
        return ("ABSENT", "ABSENT -- this Card carries no concrete pass/fail grade, so nothing "
                "here can say what PASSED would mean for it; the four release conditions only "
                "say it may start")
    body = m.group(1)
    boxes = re.findall(r"^[ \t]*-[ \t]*\[([ xX])\]", body, re.M)
    n = len(boxes)
    done = sum(1 for b in boxes if b.lower() == "x")
    if n == 0:
        return ("UNREADABLE", "a Pass/fail section exists but holds no checkboxes -- unmeasurable")
    if done == 0:
        return ("UNCHECKED", f"0/{n} checked (council 4-point grade, Gemini #11; the header hands "
                "adoption to James). Presence is all this machine checks: who ticks a box and on "
                "what evidence is the director's word")
    if done < n:
        return ("PARTIAL", f"{done}/{n} checked -- not a pass until all {n} are, per the Card's own line")
    return ("COMPLETE", f"{n}/{n} checked -- the Card's own grade is satisfied (on the director's word)")

def ruling(card, loop_done, q, closed, text=""):
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
    # FINDING 28: name the exclusion fields that are empty, every run. Not a condition and not a
    # failure — a statement of which independence rules currently test nothing. (Claude, 2026-10-06)
    _blank_roles = role_fields_blank(card)

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
    gstate, gline = grade_line(text)
    if c("mixed_payment_ok","no").lower()!="no": openq = "Decision 001 — Build touches two currencies"
    elif not redemption_ok(): openq = "REDEMPTION.md is blank — a vendor will ask what SUPER buys; vendor agent is gated until it's filled"
    elif wstate == "EXPIRED": openq = "Window expired — close Build as NOT CLOSED, or write a new day7 (B-13)"
    elif wstate in ("UNDECLARED", "UNREADABLE") and not closed: openq = "day1/day7 unset — the Card's window is prose; no machine can grade its time"
    # ADDITIVE, not another elif: the first version of this put the overlap in the elif chain
    # below the window question, so on BUILD_001 — whose day1/day7 are blank — the overlap was
    # computed, printed in condition 2, and silently absent from the director's open question.
    # A question that only surfaces once an unrelated question is answered is not asked.
    # (Claude, 2026-10-04, same cycle, after observing it)
    # ADDITIVE for the same reason: a Build that reaches CLOSED with its own pass/fail
    # grade unticked has been closed on release conditions alone. Not raised while the Build
    # is still open — the state is printed every time on the Grade: line, and inventing an
    # extra ask out of it would be noise. (Claude, 2026-10-04, finding 17)
    if closed and gstate != "COMPLETE":
        gnote = ("this Build is CLOSED and its own pass/fail grade reads " + gstate + " (" + gline +
                 ") — say PASSED or NOT PASSED against those four points, or strike them from the Card")
        openq = gnote if openq == "none" else f"{openq} · ALSO: {gnote}"
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
    # FINDING 28 (Claude, 2026-10-06): report the independence FIELDS every run, not just the
    # independence RULES. An exclusion against an empty field can never fire.
    if _blank_roles:
        _lbl = [(r + " (already reported as condition 1)" if r == "provider" else r)
                for r in _blank_roles]
        iline = ("BLANK: " + ", ".join(_lbl) +
                 " — the witness clash test and the beneficiary overlap test both exclude these "
                 "roles, and _samename() is False against an empty field, so those rules test "
                 "nothing until the Card names them (finding 28)")
    else:
        iline = ("director=%s | circulator=%s | provider=%s — both overlap tests can fire on all "
                 "three" % (c("director"), c("circulator"), c("provider") or "(unnamed, condition 1)"))
    return status, conds, loop_done, openq, nbm, wline, gline, iline

def render(build_id, status, conds, loop_done, openq, nbm, window="(not computed)", grade="(not computed)", independence="(not computed)"):
    today = cr_today().isoformat()
    tzlabel = f"UTC{_OFF:+03.0f}" if _OFF == int(_OFF) else f"UTC{_OFF:+}"
    if _OFF_ENV is not None: tzlabel += " ·offset from SUPER_TZ_OFFSET_HOURS"
    lines = [f"[SUPER-STEWARD · BUILD-{build_id} · {today} {tzlabel}]", f"STATUS: {status}", "Conditions:"]
    for i,(name,ok,why) in enumerate(conds,1):
        lines.append(f"  {i} {name+':':<11} {'✓' if ok else '✗'} — {why}")
    rstate, rline = redemption_expiry_line()
    lines += [f"Loop: {loop_done} / 11", f"Window: {window}",
              f"Redemption validity ({rstate}): {rline}", f"Grade: {grade}",
              f"Independence fields: {independence}",
              f"Open question for the director: {openq}", f"NBM: {nbm}"]
    return "\n".join(lines)

def cmd_status(path, write_log=True):
    path = pathlib.Path(path)
    if not path.exists() and not path.is_absolute(): path = HERE / path.name   # run from anywhere
    if not path.exists(): sys.exit(f"no such card: {path}")
    card, loop_done, q, closed = parse_card(path)
    out = render(card.get("id","?"), *ruling(card, loop_done, q, closed,
                                            text=path.read_text(encoding="utf-8")))
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

def ledger_amount(field):
    """Read the SUPER amount out of a ledger line's amount column.

    2026-10-04 (finding 18b): this used to strip EVERY non-digit from the field, so
    "100 SUPER (of 100)" read as 100100 and "50 SUPER (partial, 2 of 2)" as 5022 —
    it could only ever read a number BIGGER than the one a human wrote, and the
    ledger's own five day-one lines are written in exactly that style
    ("0 SUPER (earned 3)" read as 3). An outstanding total that inflates is one
    cmd_redeem refuses against, so the error pointed at paying out more than was
    ever minted. The amount is now the FIRST integer in the field, which is the
    format every line of this ledger and every line the proposals emit already use.
    Returns None when the field names no leading number, so the caller can say
    UNREADABLE instead of guessing a figure — a ledger line nobody can parse must
    not silently count as zero.
    """
    m = re.match(r"\s*(-?\d[\d,]*)", field or "")
    if not m: return None
    try: return int(m.group(1).replace(",", ""))
    except ValueError: return None

def ledger_totals():
    """(minted, redeemed, unreadable) in SUPER, from the treasury's side of the ledger."""
    minted = redeemed = 0; unreadable = []
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or "|" not in line: continue
            f = [x.strip() for x in line.split("|")]
            if len(f) < 5: continue
            if f[1].lower() != "treasury" and f[2].lower() != "treasury": continue
            amt = ledger_amount(f[3])
            if amt is None:
                unreadable.append(line.strip()); continue
            if f[1].lower() == "treasury": minted += amt
            if f[2].lower() == "treasury": redeemed += amt
    return minted, redeemed, unreadable

def proposal(kind, lines, approver):
    pid = f"{kind.upper()}-{datetime.datetime.now(CR).strftime('%Y%m%dT%H%M%S')}CR"
    print(f"[PROPOSAL {pid}] — computed by super-steward; approval right: {approver}")
    for l in lines: print("  " + l)
    print(f"  To execute: a human with the '{approver}' right appends 'APPROVED {pid}' to LEDGER.md and moves the colones. The AI does not.")
    return pid

def cmd_mint(build, amount):
    path = card_path_or_refuse(build, "mint")
    if path is None: return
    card, loop_done, q, closed = parse_card(path)
    status = ruling(card, loop_done, q, closed)[0]
    if status != "READY":
        print(f"REFUSED — BUILD-{build} is {status}, not READY. Run: python3 super_build.py status BUILD_{build}.md"); return
    minted, redeemed, unreadable = ledger_totals()
    if unreadable:
        print("REFUSED — LEDGER.md has %d line(s) whose amount column this steward cannot read, so it "
              "cannot know what is outstanding. It will not mint against a total it had to guess:" % len(unreadable))
        for l in unreadable: print("    " + l)
        return
    # 2026-10-04 (finding 18a): the amount used to come straight from argv and be
    # compared with NOTHING — not the Card's committed figure, not its declared max
    # loss, not the outstanding total. `mint 001 1000000` printed a proposal for
    # ₡400,000,000 of backing against a 100-SUPER Card and every line read as normal
    # procedure. cmd_passiton derives its amount FROM the Card and cmd_redeem refuses
    # above outstanding, so the primary mint path was the only money path with no
    # bound — and it is the one that creates the liability. This is NOT a cap of the
    # steward's invention: max_loss_super is condition 4 of the Card, the director's
    # own declared stop, and super_committed is what he signed. The document of record
    # wins, exactly as redemption_terms() lets REDEMPTION.md win over PEG_CRC. To mint
    # more, the director edits the Card; a machine must not let a figure past the
    # ceiling the Card itself declares.
    def _int(v):
        try: return int(str(v).strip())
        except (TypeError, ValueError): return None
    committed = _int(card.get("super_committed")); ceiling = _int(card.get("max_loss_super"))
    if ceiling is None:
        print(f"REFUSED — BUILD-{build}'s Card declares no readable max_loss_super, so nothing here "
              f"knows the loss the director agreed to risk. Write it on the Card first."); return
    if amount > ceiling:
        print(f"REFUSED — {amount} SUPER exceeds BUILD-{build}'s own max_loss_super of {ceiling} "
              f"(condition 4, the director's declared stop; super_committed: {committed}). "
              f"₡{amount*PEG_CRC:,} of backing would be required against a Card that risks "
              f"₡{ceiling*PEG_CRC:,}. The Card is the document of record: raise it there, in the "
              f"director's hand, and run this again."); return
    # FINDING 28 (Claude, 2026-10-06): the ledger line below printed `card.get('circulator') or
    # 'circulator'` — with the field blank, an APPEND-ONLY ledger would have recorded the literal
    # word "circulator" in the column where a party's name goes, and the same for the witness
    # column. A party is a person, not a role word. Refused rather than printed.
    _ph = [r for r in ("circulator", "witness") if not filled(card.get(r))]
    if _ph:
        print(f"REFUSED — BUILD-{build}'s Card leaves {' and '.join(_ph)} blank, so this mint's "
              f"ledger line would record the role word(s) {', '.join(repr(x) for x in _ph)} where a "
              f"party's name belongs. LEDGER.md is append-only: a placeholder written there is "
              f"permanent. Name them on the Card and run this again. (finding 28)")
        return
    escrow_needed = amount * PEG_CRC
    over = [] if committed is None or amount <= committed else [
        f"NOTE — {amount} SUPER is MORE than the Card's super_committed ({committed}), though within "
        f"max_loss_super ({ceiling}). Within the declared stop, so not refused; named here because a "
        f"mint above what was signed should never pass as routine."]
    proposal("mint", over + [
        f"Mint {amount} SUPER against BUILD-{build} ({card.get('intention','')[:60]})",
        f"Escrow required BEFORE mint: ₡{escrow_needed:,} into the named SUPER escrow (1 SUPER = ₡{PEG_CRC})",
        f"Within the Card: super_committed {committed} · max_loss_super {ceiling} — this steward checks the "
        f"amount against the CARD only. Whether ₡{escrow_needed:,} is actually in the named escrow is not "
        f"readable from any file here; it is the director's word, and 100% backing is the whole promise.",
        f"Outstanding after mint: {minted - redeemed + amount} SUPER (escrow must cover ₡{(minted - redeemed + amount)*PEG_CRC:,})",
        f"Ledger line: {cr_today()} | treasury | {card.get('circulator')} | {amount} SUPER | mint for BUILD-{build} | {build} | {card.get('witness')}",
    ], RIGHTS["mint"])

def cmd_redeem(amount, who, build):
    minted, redeemed, unreadable = ledger_totals()
    if unreadable:
        print("REFUSED — LEDGER.md has %d line(s) whose amount column this steward cannot read, so the "
              "outstanding total is unknown and no payout may be computed from it:" % len(unreadable))
        for l in unreadable: print("    " + l)
        return
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
        f"Note: R_co for this SUPER = number of hands before this line. Record it on the Card as a "
        f"line reading exactly 'R_co: <n>' — that is the only string cmd_passiton can read, and "
        f"no Card or template carries the field yet (2026-10-04, finding 19).",
    ], RIGHTS["redeem"])

def card_path_or_refuse(build, cmd):
    """Return the Card path for a Build id, or refuse readably if it is not there.

    2026-10-04 (finding 19b, in the copy strangers run): cmd_mint and cmd_passiton
    called parse_card(HERE / f"BUILD_{build}.md") straight, so a missing Card raised a
    raw FileNotFoundError traceback — while cmd_status, the one command that moves no
    money, has always printed a clean "no such card". The published pack ships
    TEMPLATE_BUILD_CARD.md and NO Build Cards, so the two usage lines in this file's own
    header ("mint 001 100", "passiton 001") crash on first run for every adopter.
    A money command must refuse, not crash: a traceback tells a stranger the tool is
    broken, when the truth is that the Build does not exist yet.
    """
    path = HERE / f"BUILD_{build}.md"
    if not path.exists():
        print(f"REFUSED — {cmd} needs a Build Card and {path.name} is not in {HERE}.")
        print(f"  Create it first:  python3 super_build.py new {build} <intention>")
        print( "  (The published pack carries TEMPLATE_BUILD_CARD.md and no Cards on purpose —")
        print( "  a Card names real people, and those belong to whoever runs the Build.)")
        return None
    return path

def card_rco(text):
    """Read R_co — revolutions before cash-out — out of a Build Card.

    2026-10-04 (finding 19): cmd_passiton used `re.search(r"R_co:\\s*(\\d+)", text)` and
    then `int(...) if rco else 1`, so a Card with NO R_co line reported "R_co=1" —
    a number no human ever wrote, printed as the stated reason for refusing a MINT.
    Three different states (never recorded / recorded as 1 / recorded unreadably)
    all came out as the same measured 1, and since neither BUILD_001.md,
    BUILD_002.md nor TEMPLATE_BUILD_CARD.md has an R_co field, the UNRECORDED case
    is every Build that exists. This is finding 18's rule one function over, in the
    only money path cycle 18 did not re-audit: THE MACHINE THAT COMPUTES MONEY MUST
    REFUSE WHAT IT CANNOT READ, AND MAY NEVER READ A BIGGER NUMBER THAN A HUMAN
    WROTE — and its corollary, that where a machine cannot see a promise at all its
    proposal must say so. The default failed SAFE (it refused, so it could not
    over-mint), which is exactly why it survived: a fabricated number that blocks
    is still a fabricated number, and here it was also the thing making Pass It On
    and DECISION_BOT.md's transfer gate ("R_co >= 2 on 3 consecutive Builds")
    unreachable by construction rather than by evidence.

    Returns (value, state) with state RECORDED / UNRECORDED / UNREADABLE.
    Never invents a value: UNRECORDED and UNREADABLE both return None.
    """
    m = re.search(r"^[ \t]*R_co:[ \t]*(.*)$", text, re.M)
    if not m:
        return None, "UNRECORDED"
    raw = m.group(1).split("#", 1)[0].strip()
    if not raw:
        return None, "UNRECORDED"
    n = re.match(r"(\d+)", raw)
    if not n:
        return None, "UNREADABLE"
    return int(n.group(1)), "RECORDED"

def cmd_passiton(build):
    path = card_path_or_refuse(build, "pass-it-on")
    if path is None: return
    card, loop_done, q, closed = parse_card(path)
    text = path.read_text(encoding="utf-8")
    rco, rstate = card_rco(text)
    why = []
    if not closed:
        why.append("the Build is not CLOSED")
    if q != "INCREASED":
        why.append(f"Q is {q or 'unset'}, and this mint requires INCREASED")
    if rstate == "UNRECORDED":
        why.append("R_co is UNRECORDED — this steward will not read a revolution count "
                   "nobody wrote, so it refuses instead of assuming 1")
    elif rstate == "UNREADABLE":
        why.append("R_co is UNREADABLE — the line exists but names no leading number, "
                   "so this steward refuses rather than guess a figure")
    elif rco < 2:
        why.append(f"R_co is {rco} as recorded on the Card, and this mint requires >= 2 "
                   f"(R_co = 1 means SUPER went one hop and came back to the treasury)")
    if why:
        print(f"REFUSED — pass-it-on mint requires CLOSED + Q INCREASED + R_co >= 2. "
              f"Now: closed={closed}, Q={q or 'unset'}, R_co={rco if rstate == 'RECORDED' else rstate}.")
        for w in why:
            print(f"  · {w}")
        if rstate != "RECORDED":
            print(f"  To make this checkable, BUILD_{build}.md needs one line reading exactly:  R_co: <n>")
            print( "  NOT a defect in the Card: no Build Card and no TEMPLATE_BUILD_CARD.md carries that")
            print( "  field, so this gate has never been reachable for any Build. Adding it to the")
            print( "  template is the director's word, bundled with B-23 — this steward will not grow")
            print( "  his Card on its own (governance rule: AI must never quietly convert support into")
            print(f"  sovereignty). Until then the honest reading is {rstate}, never 1.")
        return
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
