#!/usr/bin/env python3
"""recursive_improver — watch James's recent communications and propose the
highest-leverage RECURSIVE system improvements.

The first turn of the loop James asked for (2026-06-14): "system should watch my
communications and build recursive improvements." This WATCHES + PROPOSES — it
never auto-deploys. Output: core/BUILD/improvement_proposals/<date>.md.
Run on-demand, or via a daily LaunchAgent (laptop, not prod).

Deep goal (Routing): James stays upstream; the system needs him less each cycle.
"""
import os, json, glob, urllib.request, datetime, pathlib, sys, ssl
try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL_CTX = ssl.create_default_context()

HOME = os.path.expanduser("~")
MEM = HOME + "/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory"
REPO = HOME + "/FPAI_Cockpit"
OUT_DIR = REPO + "/core/BUILD/improvement_proposals"


def collect_comms() -> str:
    parts = []
    tgp = HOME + "/.config/fpai/tg_brain_bridge/conversation.jsonl"
    if os.path.exists(tgp):
        lines = []
        for l in open(tgp, errors="replace"):
            try:
                m = json.loads(l); lines.append(f"{m.get('role','?')}: {m.get('text','')}")
            except Exception:
                pass
        if lines:
            parts.append("== Telegram conversation (James's pocket) ==\n" + "\n".join(lines[-40:]))
    for e in sorted(glob.glob(MEM + "/identity/sessions/*.md"), reverse=True)[:2]:
        parts.append(f"== Session: {os.path.basename(e)} ==\n" + open(e, errors="replace").read()[:4000])
    return "\n\n".join(parts)


def _api_key() -> str:
    k = os.environ.get("ANTHROPIC_API_KEY")
    if k:
        return k
    for p in (HOME + "/.config/fpai/ai.token", HOME + "/.config/fpai/api.token"):
        if os.path.exists(p):
            return open(p).read().strip()
    return ""


def call_llm(comms: str) -> str:
    key = _api_key()
    if not key:
        print("no ANTHROPIC_API_KEY / token"); sys.exit(1)
    system = ("You are the recursive improver for James's Full Potential OS. You WATCH his recent "
              "communications and propose the highest-leverage RECURSIVE system improvements — "
              "structural fixes that reduce FUTURE friction, not one-offs. Deep goal: James stays "
              "upstream; the system needs him less each cycle. For each improvement give: a short title, "
              "a 2-line spec (what / where it lives / the proof it works), and a tag — [SAFE-AUTO] "
              "(reversible, local, no prod-server or money) or [NEEDS-JAMES] (deploy/prod/money/"
              "irreducible decision). Output 1-3, ranked by leverage. Tight markdown, no preamble.")
    user = ("James's recent communications:\n\n" + comms[:12000] +
            "\n\nDiscern the recurring friction / unmet intent, then propose the recursive improvements.")
    body = json.dumps({
        "model": "claude-sonnet-4-6", "max_tokens": 1200,
        "system": system, "messages": [{"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120, context=_SSL_CTX) as r:
        data = json.loads(r.read())
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def route_to_codex(date: str, proposals_path: str, proposals: str) -> str:
    """Route the proposals into the Codex builder intake (core/BUILD/intents/),
    so watch -> spec -> Codex flows. Codex builds SAFE-AUTO items behind the
    merge-gate; NEEDS-JAMES items wait for his approval. Codex never auto-deploys
    until the merge-gate (SPEC_build-registry-and-merge-gate.md) exists."""
    intents = pathlib.Path(REPO) / "core/BUILD/intents"
    intents.mkdir(parents=True, exist_ok=True)
    safe = proposals.count("[SAFE-AUTO]")
    needs = proposals.count("[NEEDS-JAMES]")
    intent_path = intents / f"{date}-recursive-improvements.md"
    intent_path.write_text(
        f"# Intent — recursive improvements ({date})\n"
        f"**status:** open · **source:** recursive_improver (watched James's comms)\n\n"
        f"Codex: process the proposals in `{os.path.relpath(proposals_path, REPO)}`.\n\n"
        f"- Build the **[SAFE-AUTO]** items ({safe}) on `codex/<slug>` branches off "
        f"`feat/headless-build`, behind the merge-gate. Review diff, then surface to James to merge.\n"
        f"- Leave **[NEEDS-JAMES]** items ({needs}) as proposals — James decides.\n"
        f"- 🔴 GUARDRAIL: do NOT merge to main. If `core/BUILD/REGISTRY.json` doesn't exist yet, "
        f"build `docs/codex/specs/SPEC_build-registry-and-merge-gate.md` FIRST — it is the gate that "
        f"makes everything after it safe.\n")
    return str(intent_path)


def main():
    comms = collect_comms()
    if not comms.strip():
        print("no comms to watch"); return
    proposals = call_llm(comms)
    pathlib.Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    path = f"{OUT_DIR}/{date}.md"
    with open(path, "w") as f:
        f.write(f"# Recursive improvement proposals — {date}\n\n")
        f.write("_Watched James's recent communications (Telegram + sessions). "
                "Proposals only — nothing auto-deployed; SAFE-AUTO items routed to Codex._\n\n")
        f.write(proposals + "\n")
    intent = route_to_codex(date, path, proposals)
    # Surface to James's ONE chat (Telegram) — proactive reach-out.
    try:
        import subprocess
        safe = proposals.count("[SAFE-AUTO]"); needs = proposals.count("[NEEDS-JAMES]")
        msg = (f"🔭 <b>Watched your comms — {safe + needs} improvements proposed</b> "
               f"({safe} SAFE-AUTO, {needs} need you).\nFull list: core/BUILD/improvement_proposals/{date}.md")
        subprocess.run([f"{REPO}/tools/build_loop/notify_telegram.sh", msg], timeout=20)
    except Exception:
        pass
    print(f"WROTE {path}\nROUTED TO CODEX: {intent}\n\n{proposals}")


if __name__ == "__main__":
    main()
