"""
Funnel CLI — the single command interface.

Usage examples (from SERVICES/apprentice-studio/):
    python funnel.py status                          # Funnel snapshot
    python funnel.py next                            # Your top recommended action
    python funnel.py ingest data/inbound.json        # Ingest applications JSON
    python funnel.py source <name> <email> <why>     # Add an outbound prospect
    python funnel.py outreach <id> "<reason>"        # Draft outbound message
    python funnel.py screen [<id>]                   # Auto-screen one or all APPLIED
    python funnel.py advance <id> [--note "..."]     # Advance to next stage + draft comms
    python funnel.py decline <id> [--note "..."]     # Decline + draft message
    python funnel.py challenge <id>                  # Generate 48-hour brief
    python funnel.py grade <id> --deployed Y --code 0.7 --ai 0.9 --sys 0.6 --refl 0.8
    python funnel.py dossier <id>                    # Generate interview dossier
    python funnel.py interviewed <id> --score 0.85
    python funnel.py offer <id>                      # Generate offer + onboarding pack
    python funnel.py show <id>                       # Full candidate detail
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from . import challenge as challenge_mod
from . import comms as comms_mod
from . import interview as interview_mod
from . import offer as offer_mod
from . import screener as screener_mod
from . import sourcer as sourcer_mod
from .pipeline import get_funnel
from .stages import Candidate, Decision, Stage


# --- pretty printing ------------------------------------------------------

C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_BLUE = "\033[34m"
C_MAGENTA = "\033[35m"


def _bold(s: str) -> str:
    return f"{C_BOLD}{s}{C_RESET}"


def _dim(s: str) -> str:
    return f"{C_DIM}{s}{C_RESET}"


def _stage_color(stage: Stage) -> str:
    return {
        Stage.HIRED: C_GREEN,
        Stage.OFFER_SENT: C_GREEN,
        Stage.INTERVIEWED: C_BLUE,
        Stage.CHALLENGE_GRADED: C_BLUE,
        Stage.CHALLENGE_SENT: C_MAGENTA,
        Stage.SCREENED: C_YELLOW,
        Stage.APPLIED: C_YELLOW,
        Stage.CONTACTED: C_DIM,
        Stage.SOURCED: C_DIM,
        Stage.DECLINED: C_RED,
        Stage.WITHDRAWN: C_RED,
    }.get(stage, "")


# --- commands -------------------------------------------------------------

def cmd_status(_args) -> None:
    funnel = get_funnel()
    counts = funnel.funnel_summary()

    print(_bold("Apprentice Studio — Funnel Status"))
    print(_dim(datetime.now().strftime("%Y-%m-%d %H:%M")))
    print()

    funnel_order = [
        Stage.SOURCED, Stage.CONTACTED, Stage.APPLIED, Stage.SCREENED,
        Stage.CHALLENGE_SENT, Stage.CHALLENGE_GRADED, Stage.INTERVIEWED,
        Stage.OFFER_SENT, Stage.HIRED, Stage.DECLINED, Stage.WITHDRAWN,
    ]
    width = max(len(s.value) for s in funnel_order) + 2
    for stage in funnel_order:
        n = counts.get(stage.value, 0)
        bar = "█" * min(n, 30)
        color = _stage_color(stage)
        print(f"  {color}{stage.value.ljust(width)}{C_RESET} {n:>3}  {bar}")

    print()
    needs = funnel.needs_action()
    print(_bold(f"Awaiting human action: {len(needs)}"))
    if needs:
        print()
        print(f"  {'ID'.ljust(12)} {'Stage'.ljust(20)} {'Score'.ljust(7)} Name")
        print(f"  {'-' * 12} {'-' * 20} {'-' * 7} {'-' * 30}")
        for c in needs[:15]:
            best = max(
                c.challenge_score or 0, c.screening_score or 0, c.interview_score or 0
            )
            color = _stage_color(c.stage)
            print(
                f"  {c.id.ljust(12)} "
                f"{color}{c.stage.value.ljust(20)}{C_RESET} "
                f"{best:>5.2f}  {c.name}"
            )
        if len(needs) > 15:
            print(_dim(f"  … and {len(needs) - 15} more"))
    print()
    cmd_next(_args)


def cmd_next(_args) -> None:
    funnel = get_funnel()
    needs = funnel.needs_action()
    if not needs:
        print(_bold("Next action:"))
        print("  No candidates awaiting human action. Funnel is up to date.")
        print()
        print(_dim("Suggestions:"))
        print(_dim("  - Source more outbound prospects: python funnel.py source <name> <email> <why>"))
        print(_dim("  - Ingest new applications: python funnel.py ingest data/inbound.json"))
        return

    top = needs[0]
    best = max(top.challenge_score or 0, top.screening_score or 0, top.interview_score or 0)
    suggestion = _suggested_action(top)

    print(_bold("Next action:"))
    print(f"  {top.name} ({top.id}) — {top.stage.value}, score {best:.2f}")
    print(f"  {suggestion}")


def cmd_ingest(args) -> None:
    funnel = get_funnel()
    src = Path(args.path)
    if not src.exists():
        print(f"File not found: {src}", file=sys.stderr)
        sys.exit(1)

    payload = json.loads(src.read_text(encoding="utf-8"))
    items = payload if isinstance(payload, list) else payload.get("applications", [])

    added = 0
    for item in items:
        name = item.get("name") or item.get("full_name") or ""
        email = item.get("email") or ""
        if not name or not email:
            continue
        application = {k: v for k, v in item.items() if k not in {"name", "email", "full_name"}}
        funnel.add_application(name, email, application, source=item.get("source", "inbound"))
        added += 1

    print(f"Ingested {added} applications from {src}")
    print()
    cmd_status(args)


def cmd_source(args) -> None:
    funnel = get_funnel()
    cand = funnel.add_outbound(args.name, args.email, args.why)
    print(f"Sourced: {cand.name} ({cand.id})")


def cmd_outreach(args) -> None:
    funnel = get_funnel()
    cand = funnel.candidates.get(args.id)
    if not cand:
        print(f"Unknown candidate: {args.id}", file=sys.stderr)
        sys.exit(1)
    msg = sourcer_mod.draft_outbound_message(cand, args.reason)
    path = funnel.write_draft(cand.id, "outbound-message.md", msg)
    funnel.decide(cand.id, Decision.ADVANCE, by="sourcer", note="Outreach drafted")
    print(f"Outreach drafted: {path}")


def cmd_screen(args) -> None:
    funnel = get_funnel()
    if args.id:
        cand = funnel.candidates.get(args.id)
        if not cand:
            print(f"Unknown candidate: {args.id}", file=sys.stderr)
            sys.exit(1)
        result = screener_mod.screen(cand)
        funnel.save()
        print(f"{cand.name}: {result.score:.2f}")
        print(f"  {result.rationale}")
    else:
        results = screener_mod.screen_all(funnel)
        if not results:
            print("No APPLIED candidates to screen.")
            return
        for cand, result in sorted(results, key=lambda x: -x[1].score):
            print(f"  {cand.id}  {result.score:.2f}  {cand.name}  ({', '.join(result.strengths) or '—'})")


def cmd_advance(args) -> None:
    funnel = get_funnel()
    cand = funnel.candidates.get(args.id)
    if not cand:
        print(f"Unknown candidate: {args.id}", file=sys.stderr)
        sys.exit(1)

    prev_stage = cand.stage
    cand = funnel.decide(args.id, Decision.ADVANCE, by="human", note=args.note)

    draft_path = _draft_for_stage(funnel, cand, prev_stage)
    print(f"{cand.name}: {prev_stage.value} → {cand.stage.value}")
    if draft_path:
        print(f"Draft to review/send: {draft_path}")


def cmd_decline(args) -> None:
    funnel = get_funnel()
    cand = funnel.candidates.get(args.id)
    if not cand:
        print(f"Unknown candidate: {args.id}", file=sys.stderr)
        sys.exit(1)

    prev_stage = cand.stage
    cand = funnel.decide(args.id, Decision.DECLINE, by="human", note=args.note)

    msg = comms_mod.draft_decline(cand, prev_stage)
    path = funnel.write_draft(cand.id, "decline.md", msg)
    print(f"{cand.name}: declined at {prev_stage.value}")
    print(f"Decline draft: {path}")


def cmd_challenge(args) -> None:
    funnel = get_funnel()
    cand = funnel.candidates.get(args.id)
    if not cand:
        print(f"Unknown candidate: {args.id}", file=sys.stderr)
        sys.exit(1)
    deadline = datetime.now() + timedelta(hours=48)
    brief = challenge_mod.generate_brief(cand, deadline=deadline)
    path = funnel.write_draft(cand.id, "BUILD_CHALLENGE.md", brief)
    print(f"Challenge brief: {path}")


def cmd_grade(args) -> None:
    funnel = get_funnel()
    cand = funnel.candidates.get(args.id)
    if not cand:
        print(f"Unknown candidate: {args.id}", file=sys.stderr)
        sys.exit(1)

    grade_obj = challenge_mod.grade(
        cand,
        deployed_url_works=args.deployed.lower().startswith("y"),
        code_quality=args.code,
        ai_collaboration=args.ai,
        system_thinking=args.sys,
        reflection_quality=args.refl,
        notes=args.note or "",
    )
    funnel.save()
    print(f"{cand.name}: challenge score {grade_obj.score:.2f}")
    print(f"  {grade_obj.rationale}")


def cmd_dossier(args) -> None:
    funnel = get_funnel()
    cand = funnel.candidates.get(args.id)
    if not cand:
        print(f"Unknown candidate: {args.id}", file=sys.stderr)
        sys.exit(1)
    md = interview_mod.dossier(cand)
    path = funnel.write_draft(cand.id, "interview-dossier.md", md)
    print(f"Interview dossier: {path}")


def cmd_interviewed(args) -> None:
    funnel = get_funnel()
    cand = funnel.candidates.get(args.id)
    if not cand:
        print(f"Unknown candidate: {args.id}", file=sys.stderr)
        sys.exit(1)
    interview_mod.log_interview(cand, score=args.score, note=args.note or "")
    if cand.stage == Stage.CHALLENGE_GRADED:
        funnel.decide(cand.id, Decision.ADVANCE, by="human",
                      note=f"Interview score: {args.score}")
    funnel.save()
    print(f"{cand.name}: interview logged, score {args.score:.2f}, stage {cand.stage.value}")


def cmd_offer(args) -> None:
    funnel = get_funnel()
    cand = funnel.candidates.get(args.id)
    if not cand:
        print(f"Unknown candidate: {args.id}", file=sys.stderr)
        sys.exit(1)

    letter = offer_mod.generate_offer_letter(cand)
    onboarding = offer_mod.generate_onboarding(cand)
    welcome = offer_mod.generate_welcome_message(cand)

    p1 = funnel.write_draft(cand.id, "offer-letter.md", letter)
    p2 = funnel.write_draft(cand.id, "onboarding-week-1.md", onboarding)
    p3 = funnel.write_draft(cand.id, "welcome-message.md", welcome)

    if cand.stage == Stage.INTERVIEWED:
        funnel.decide(cand.id, Decision.ADVANCE, by="human", note="Offer drafted")

    print(f"{cand.name}: offer pack drafted")
    print(f"  Offer letter:   {p1}")
    print(f"  Onboarding:     {p2}")
    print(f"  Welcome msg:    {p3}")


def cmd_show(args) -> None:
    funnel = get_funnel()
    cand = funnel.candidates.get(args.id)
    if not cand:
        print(f"Unknown candidate: {args.id}", file=sys.stderr)
        sys.exit(1)
    data = cand.to_dict()
    print(json.dumps(data, indent=2))


# --- helpers --------------------------------------------------------------

def _suggested_action(c: Candidate) -> str:
    s = c.stage
    if s == Stage.SCREENED:
        return f"Review screening, then either: python funnel.py advance {c.id}  OR  python funnel.py decline {c.id}"
    if s == Stage.CHALLENGE_SENT:
        return f"Wait for submission, then: python funnel.py grade {c.id} --deployed Y --code 0.7 --ai 0.8 --sys 0.6 --refl 0.7"
    if s == Stage.CHALLENGE_GRADED:
        return f"Generate dossier + schedule interview: python funnel.py dossier {c.id}"
    if s == Stage.INTERVIEWED:
        return f"Generate offer pack: python funnel.py offer {c.id}"
    if s == Stage.OFFER_SENT:
        return f"Wait for signature, then: python funnel.py advance {c.id}  (sets HIRED)"
    if s == Stage.APPLIED:
        return f"Auto-screen: python funnel.py screen {c.id}"
    if s == Stage.SOURCED:
        return f"Draft outbound: python funnel.py outreach {c.id} '<reason>'"
    if s == Stage.CONTACTED:
        return "Wait for response. Followup if 7+ days silence."
    return "—"


def _draft_for_stage(funnel, cand: Candidate, prev_stage: Stage) -> Optional[Path]:
    """When advancing, draft the matching comms artifact and return its path."""
    if prev_stage == Stage.SCREENED:
        deadline = datetime.now() + timedelta(hours=48)
        msg = comms_mod.draft_advance_to_challenge(cand, deadline)
        brief = challenge_mod.generate_brief(cand, deadline=deadline)
        funnel.write_draft(cand.id, "BUILD_CHALLENGE.md", brief)
        return funnel.write_draft(cand.id, "advance-to-stage-2.md", msg)
    if prev_stage == Stage.CHALLENGE_GRADED:
        msg = comms_mod.draft_advance_to_interview(
            cand,
            interview_window="\n- Tue 2-3pm\n- Wed 10-11am\n- Thu 4-5pm\n(all your local time)",
        )
        return funnel.write_draft(cand.id, "advance-to-stage-3.md", msg)
    if prev_stage == Stage.INTERVIEWED:
        letter = offer_mod.generate_offer_letter(cand)
        onb = offer_mod.generate_onboarding(cand)
        welcome = offer_mod.generate_welcome_message(cand)
        funnel.write_draft(cand.id, "offer-letter.md", letter)
        funnel.write_draft(cand.id, "onboarding-week-1.md", onb)
        return funnel.write_draft(cand.id, "welcome-message.md", welcome)
    return None


# --- entry ----------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="funnel", description="Apprentice Studio funnel")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("status", help="Show funnel snapshot + next actions").set_defaults(func=cmd_status)
    sub.add_parser("next", help="Show top recommended next action").set_defaults(func=cmd_next)

    p_ingest = sub.add_parser("ingest", help="Ingest applications JSON")
    p_ingest.add_argument("path")
    p_ingest.set_defaults(func=cmd_ingest)

    p_source = sub.add_parser("source", help="Add outbound prospect")
    p_source.add_argument("name")
    p_source.add_argument("email")
    p_source.add_argument("why", help="Why this person")
    p_source.set_defaults(func=cmd_source)

    p_out = sub.add_parser("outreach", help="Draft outbound message")
    p_out.add_argument("id")
    p_out.add_argument("reason")
    p_out.set_defaults(func=cmd_outreach)

    p_screen = sub.add_parser("screen", help="Auto-screen one or all APPLIED")
    p_screen.add_argument("id", nargs="?")
    p_screen.set_defaults(func=cmd_screen)

    p_adv = sub.add_parser("advance", help="Advance candidate to next stage")
    p_adv.add_argument("id")
    p_adv.add_argument("--note", default=None)
    p_adv.set_defaults(func=cmd_advance)

    p_dec = sub.add_parser("decline", help="Decline candidate")
    p_dec.add_argument("id")
    p_dec.add_argument("--note", default=None)
    p_dec.set_defaults(func=cmd_decline)

    p_chal = sub.add_parser("challenge", help="Generate 48-hr build challenge brief")
    p_chal.add_argument("id")
    p_chal.set_defaults(func=cmd_challenge)

    p_grade = sub.add_parser("grade", help="Grade a build challenge submission")
    p_grade.add_argument("id")
    p_grade.add_argument("--deployed", required=True, help="Y/N")
    p_grade.add_argument("--code", type=float, required=True)
    p_grade.add_argument("--ai", type=float, required=True)
    p_grade.add_argument("--sys", type=float, required=True)
    p_grade.add_argument("--refl", type=float, required=True)
    p_grade.add_argument("--note", default="")
    p_grade.set_defaults(func=cmd_grade)

    p_dos = sub.add_parser("dossier", help="Generate interview dossier")
    p_dos.add_argument("id")
    p_dos.set_defaults(func=cmd_dossier)

    p_int = sub.add_parser("interviewed", help="Log interview score + advance")
    p_int.add_argument("id")
    p_int.add_argument("--score", type=float, required=True)
    p_int.add_argument("--note", default="")
    p_int.set_defaults(func=cmd_interviewed)

    p_off = sub.add_parser("offer", help="Generate offer + onboarding pack")
    p_off.add_argument("id")
    p_off.set_defaults(func=cmd_offer)

    p_show = sub.add_parser("show", help="Show full candidate detail")
    p_show.add_argument("id")
    p_show.set_defaults(func=cmd_show)

    return p


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
