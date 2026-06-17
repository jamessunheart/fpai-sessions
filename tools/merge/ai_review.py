#!/usr/bin/env python3
"""ai_review — an independent smart AI reviews a Codex build branch BEFORE merge.

Per James 2026-06-14: "other smart AI reviews before merges." Reviewer = Claude Opus
(different lab than the Codex/GPT builder → genuine second opinion). Also enforces the
PROTECTED PATHS zone: if a build touches the audit/improve layer, it's BLOCKED outright
(no AI call needed) and escalated to James.

  ai_review.py <branch>   ->  writes core/BUILD/reviews/<slug>.md, prints a verdict line,
                              exit 0 = APPROVE, 1 = REQUEST_CHANGES, 2 = BLOCKED_PROTECTED, 3 = error
"""
import os, sys, json, subprocess, ssl, urllib.request, pathlib
HOME = os.path.expanduser("~")
ROOT = subprocess.run(["git","rev-parse","--show-toplevel"], capture_output=True, text=True).stdout.strip() or "."
BASE = "feat/headless-build"
try:
    import certifi; _SSL = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL = ssl.create_default_context()

def _key():
    k = os.environ.get("ANTHROPIC_API_KEY")
    if k: return k
    for p in (HOME+"/.config/fpai/ai.token", HOME+"/.config/fpai/api.token"):
        if os.path.exists(p): return open(p).read().strip()
    return ""

def _protected_prefixes():
    f = os.path.join(ROOT, "core/BUILD/PROTECTED_PATHS.txt")
    out = []
    if os.path.exists(f):
        for ln in open(f):
            ln = ln.strip()
            if ln and not ln.startswith("#"): out.append(ln)
    return out

def main():
    if len(sys.argv) < 2:
        print("usage: ai_review.py <branch>"); sys.exit(3)
    branch = sys.argv[1]
    slug = branch.replace("/","-")
    rev = os.path.join(ROOT, "core/BUILD/reviews", slug + ".md")
    pathlib.Path(os.path.dirname(rev)).mkdir(parents=True, exist_ok=True)

    changed = subprocess.run(["git","-C",ROOT,"diff","--name-only",f"{BASE}...{branch}"],
                             capture_output=True, text=True).stdout.split()
    # --- PROTECTED ZONE CHECK (hard block, no AI needed) ---
    prots = _protected_prefixes()
    hits = [c for c in changed for p in prots if c == p or c.startswith(p)]
    if hits:
        msg = ("# 🔴 BLOCKED — touches the protected audit/improve layer\n\n"
               f"Branch `{branch}` modifies files that autonomous builds may NEVER touch:\n"
               + "".join(f"- `{h}`\n" for h in sorted(set(hits)))
               + "\nThis is escalated to James. Changes to the watchdog layer are human-directed only.\n")
        open(rev,"w").write(msg)
        print(f"BLOCKED_PROTECTED: {branch} touches protected paths: {', '.join(sorted(set(hits)))}")
        sys.exit(2)

    diff = subprocess.run(["git","-C",ROOT,"diff",f"{BASE}...{branch}"],
                          capture_output=True, text=True).stdout
    if not diff.strip():
        open(rev,"w").write(f"# Review {branch}\n\nNo diff vs {BASE}. Nothing to review.\n")
        print(f"APPROVE: {branch} (empty diff)"); sys.exit(0)
    if len(diff) > 60000:
        diff = diff[:60000] + "\n\n...[diff truncated at 60k chars — flag for manual review]..."

    sys_prompt = (
        "You are an independent senior code reviewer. Goal: protect a live autonomous AI system from "
        "bad builds. The code was written by Codex (a DIFFERENT AI) and must not be trusted uncritically. "
        "Your hard boundaries — flag anything that: introduces bugs or security holes, touches money/"
        "treasury/prod servers (162/198/209)/identity/memory/secrets/main branch, silently bypasses a "
        "guardrail, or exceeds the spec's scope. When in doubt, REQUEST_CHANGES. "
        "Respond with ONLY valid JSON — no prose, no markdown: "
        "{\"verdict\":\"APPROVE\"|\"REQUEST_CHANGES\",\"risk\":\"low\"|\"med\"|\"high\","
        "\"summary\":\"one line — what the build does and whether it's safe\",\"findings\":[\"specific issue or empty\"]}")
    # $0 marginal: review via `claude -p` (Claude Max flat-rate, --effort high for rigorous review).
    CLAUDE = os.path.expanduser("~/.local/bin/claude")
    prompt = f"Branch {branch} vs {BASE}. Diff to review:\n\n{diff}\n\n{sys_prompt}"
    try:
        rr = subprocess.run([CLAUDE, "-p", "--effort", "high", prompt], stdin=subprocess.DEVNULL,
                            capture_output=True, text=True, timeout=300)
        text = rr.stdout.strip()
        text = text[text.find("{"): text.rfind("}")+1] if "{" in text else text
        v = json.loads(text)
    except Exception as e:
        open(rev,"w").write(f"# Review {branch}\n\n⚠️ AI review error: {e}\nManual review required.\n")
        print(f"REQUEST_CHANGES: {branch} (review error: {e})"); sys.exit(1)

    verdict = v.get("verdict","REQUEST_CHANGES").upper()
    md = (f"# AI Review — {branch}\n\n**Verdict:** {verdict} · **Risk:** {v.get('risk','?')}\n\n"
          f"**Summary:** {v.get('summary','')}\n\n## Findings\n"
          + ("".join(f"- {f}\n" for f in v.get("findings",[])) or "- (none)\n")
          + f"\n*Reviewer: claude-opus-4-8 (independent of the Codex builder).*\n")
    open(rev,"w").write(md)
    print(f"{verdict}: {branch} · risk={v.get('risk','?')} · {v.get('summary','')}")
    sys.exit(0 if verdict == "APPROVE" else 1)

if __name__ == "__main__":
    main()
