#!/usr/bin/env python3
"""council debate — a multi-lens architecture debate on what to build/focus next, based on
James's surfaced intents. Three architect lenses (Pragmatist / Visionary / Skeptic) argue,
a synthesizer picks ONE proposal, and it surfaces to James's phone for approval.

Designed to be run every 5 min SAFELY:
  - change-gate: only debates when intents/queue changed since last run (else ~$0 skip)
  - daily council cap: stops when today's council spend hits the cap
  - one-at-a-time: skips if a decision already awaits James
  - every call logged to the cost ledger (track.py)
Honest: only Claude is available now → lenses are personas of one model (Sonnet). Add
OPENAI_API_KEY / GEMINI_API_KEY to make them truly separate voices.
  Kill: touch ~/.config/fpai/council/.disabled
"""
import os, sys, json, ssl, hashlib, subprocess, urllib.request
from pathlib import Path
HOME = os.path.expanduser("~")
HOST = os.environ.get("BRAIN_HOST", "root@162.0.208.88")
# Env-aware: on brain 162 the curator module is local + repo lives at /opt/fpai-build/FPAI_Cockpit
# (server-side, laptop-free). On the laptop, curator is reached over SSH + repo is ~/FPAI_Cockpit.
SERVER_MODE = os.path.isdir("/opt/sh-brain-src/curator")
REPO = "/opt/fpai-build/FPAI_Cockpit" if SERVER_MODE else HOME + "/FPAI_Cockpit"
CLAUDE = os.path.expanduser("~/.local/bin/claude")
CFG = HOME + "/.config/fpai/council"; os.makedirs(CFG, exist_ok=True)
DAILY_CAP = float(os.environ.get("COUNCIL_DAILY_USD", "3.0"))
ENV = ('ENVFILE=$(systemctl show sh-brain-tgbot -p EnvironmentFiles 2>/dev/null | '
       'sed -E "s/EnvironmentFiles=//; s/ .*//"); cd /opt/sh-brain-src && set -a; . "$ENVFILE" 2>/dev/null; set +a;')
sys.path.insert(0, REPO + "/tools/cost")
sys.path.insert(0, REPO)
import track
try:
    import importlib.util as _ilu
    _consciousness_path = Path(REPO) / "tools" / "consciousness" / "loop.py"
    _consciousness_spec = _ilu.spec_from_file_location("fpai_consciousness_loop", _consciousness_path)
    consciousness_loop = _ilu.module_from_spec(_consciousness_spec) if _consciousness_spec and _consciousness_spec.loader else None
    if consciousness_loop:
        sys.modules["fpai_consciousness_loop"] = consciousness_loop
        _consciousness_spec.loader.exec_module(consciousness_loop)
except Exception:
    consciousness_loop = None
try:
    from curator.blueprints.manager import build_blueprint_context
except Exception:
    build_blueprint_context = None
try:
    from .self_diagnostic import is_decision_queue_empty, run_diagnostic_dialogue, trigger_from_files
except Exception:
    try:
        from self_diagnostic import is_decision_queue_empty, run_diagnostic_dialogue, trigger_from_files
    except Exception:
        is_decision_queue_empty = run_diagnostic_dialogue = trigger_from_files = None
try:
    import certifi; SSLCTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSLCTX = ssl.create_default_context()

def _key():
    k = os.environ.get("ANTHROPIC_API_KEY")
    if k: return k
    for p in (HOME + "/.config/fpai/ai.token", HOME + "/.config/fpai/api.token"):
        if os.path.exists(p): return open(p).read().strip()
    return ""

def ssh(cmd, inp=None):
    return subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=20",HOST,ENV+" "+cmd],
                          input=inp, capture_output=True, text=True, timeout=70).stdout

def run_curator(cmd, inp=None):
    """Reach the curator decision module. Server-mode = local (sourcing bot env + claude token);
    laptop-mode = over SSH to 162. Same command string either way."""
    if SERVER_MODE:
        full = ('ENVFILE=$(systemctl show sh-brain-tgbot -p EnvironmentFiles 2>/dev/null | '
                'sed -E "s/EnvironmentFiles=//; s/ .*//"); cd /opt/sh-brain-src && set -a; '
                '. "$ENVFILE" 2>/dev/null; . /root/.config/fpai/claude.env 2>/dev/null; set +a; ' + cmd)
        return subprocess.run(["bash","-c",full], input=inp, capture_output=True, text=True, timeout=70).stdout
    return ssh(cmd, inp)

def _ops(event, detail, nxt=""):
    """Write one row to the ops truth ledger (server-side) so the digest/bot report measured reality."""
    try:
        subprocess.run(["python3", REPO + "/tools/build_loop/ops_log.py", "council", event, detail, "$0", "", nxt], timeout=15)
    except Exception:
        pass


def gpt_voice(intents):
    """A TRUE second-lab voice via the codex CLI (ChatGPT Max, $0 marginal). Best-effort —
    if codex is slow/unavailable, the debate proceeds Claude-only."""
    try:
        CODEX = os.path.expanduser("~/.local/bin/codex")
        q = ("In 1-2 sentences only, no code and no file changes: given these intents + queue, what is the "
             "single highest-leverage thing this autonomous build system should build NEXT, and why? "
             "Be concrete and conservative.\n\n" + intents[:2500])
        r = subprocess.run([CODEX, "exec", "--cd", REPO, "--sandbox", "read-only",
                            "--skip-git-repo-check", "-"], input=q, capture_output=True, text=True, timeout=150)
        out = [l.strip() for l in r.stdout.splitlines() if l.strip()]
        def noise(l):
            return (l.startswith("hook:") or l.lower() == "tokens used" or l.replace(",", "").isdigit()
                    or l.startswith("EXIT=") or l.startswith("warning:") or l.startswith("[") or l.startswith("codex"))
        clean = [l for l in out if not noise(l)]
        return clean[-1][:280] if clean else ""
    except Exception:
        return ""

SYS = (
 "Goal: identify the single highest-leverage next build for a self-evolving AI platform, or propose "
 "nothing if no build clearly warrants it. Context: James's recent intents + the current decision queue. "
 "Reason: James's attention is the scarcest resource — every proposal must earn it. "
 "Hard boundaries: no duplicate proposals, no cruft, no builds that add complexity without clear proof value. "
 "James's rule: concentrate harder, not build more. Prefer propose=false when uncertain. "
 "Three lenses to weigh internally — cheapest/highest-leverage NOW (pragmatist), "
 "best-for-long-term-vision (visionary), riskiest-gap-or-what-NOT-to-build (skeptic), "
 "and awareness: meaning-vs-approval drift from the private consciousness-observer log when present. "
 "Respond with ONLY valid JSON, no prose outside it: "
 "{\"pragmatist\":\"1 sentence\",\"visionary\":\"1 sentence\",\"skeptic\":\"1 sentence\","
 "\"awareness\":\"1 sentence\","
 "\"synthesis\":\"one-paragraph verdict\",\"propose\":true|false,"
 "\"title\":\"<=8 words\",\"why\":\"one sentence\","
 "\"build_spec\":\"concrete: what to build, where, what the proof looks like\","
 "\"risk\":\"low\"|\"med\","
 "\"weighting_directive\":\"optional council model-review directive for MODEL_DNA\","
 "\"signal_types_amplified\":[\"optional\"],\"signal_types_dampened\":[\"optional\"]}.")


def pragmatist_voice(signal, glm_caller=None):
    """Return the Pragmatist lens from sovereign GLM when configured.

    ``tools.gpu.glm_inference.call_glm`` owns the kill switch, budget guard,
    endpoint detection, retry, ops-ledger logging, and Claude fallback.
    """

    if glm_caller is None:
        try:
            from tools.gpu.glm_inference import call_glm
        except Exception:
            return ""
        glm_caller = call_glm
    messages = [
        {
            "role": "system",
            "content": (
                "You are the Pragmatist lens for the FPAI council. In one sentence, "
                "name the cheapest, highest-leverage next build now. Be concrete and conservative."
            ),
        },
        {"role": "user", "content": signal[:5000]},
    ]
    try:
        return glm_caller(messages, max_tokens=180, temperature=0.2).strip()[:600]
    except Exception:
        return ""


def _focus_text():
    try:
        fp = REPO + "/core/STATE/COUNCIL_FOCUS.md"
        if os.path.exists(fp):
            with open(fp) as handle:
                return "\n\nSTANDING FOCUS — weight every proposal toward this (set by James):\n" + handle.read().strip()
    except Exception:
        pass
    return ""


def _resources_text():
    try:
        fp = REPO + "/core/STATE/AVAILABLE_RESOURCES.md"
        if os.path.exists(fp):
            with open(fp) as handle:
                return "\n\nAVAILABLE RESOURCES — prefer proposals that use already-installed tools when relevant:\n" + handle.read().strip()
    except Exception:
        pass
    return ""


def build_prompt(queue, chats, focus, pragmatist=""):
    prompt = SYS + focus + "\n\nDECISION QUEUE:\n" + queue + "\n\nRECENT INTENTS (chats):\n" + chats + "\n\nRespond with ONLY the JSON object."
    if pragmatist:
        prompt = (
            "SOVEREIGN PRAGMATIST LENS (RunPod GLM when configured; otherwise flat-rate fallback):\n"
            + pragmatist
            + "\n\nUse that as the pragmatist lens unless the evidence contradicts it.\n\n"
            + prompt
        )
    if build_blueprint_context and os.environ.get("BLUEPRINTS_DISABLE") != "1":
        try:
            blueprint_context = build_blueprint_context(queue, chats, focus, include_council=True)
            if blueprint_context:
                prompt = (
                    "[Module blueprints — what already exists + quality standards]\n"
                    + blueprint_context
                    + "\n\n"
                    + prompt
                )
        except Exception:
            pass
    if consciousness_loop and os.environ.get("CONSCIOUSNESS_LOOP_DISABLE") != "1":
        try:
            awareness_context = consciousness_loop.consciousness_context()
            if awareness_context:
                prompt = (
                    "[Private consciousness-observer context for Awareness lens]\n"
                    + awareness_context
                    + "\n\n"
                    + prompt
                )
        except Exception:
            pass
    return prompt


def run_claude_json(prompt):
    import subprocess as _sp
    r = _sp.run([CLAUDE, "-p", "--effort", "xhigh", prompt], stdin=_sp.DEVNULL, capture_output=True, text=True, timeout=300)
    txt = r.stdout.strip()
    return json.loads(txt[txt.find("{"):txt.rfind("}")+1]), r


def main():
    if os.path.exists(CFG + "/.disabled") or os.path.exists(HOME + "/.config/fpai/decisions/.recommend_disabled"):
        print("disabled"); return 0

    # guard: daily council cost cap
    spent, _ = track.today("council")
    if spent >= DAILY_CAP:
        print(f"council daily cap hit (${spent:.2f}/${DAILY_CAP})"); return 0

    # load queue — no one-at-a-time gate (decision agent auto-answers, build loop auto-merges)
    queue = run_curator("./.venv/bin/python -m curator.decisions list")

    if trigger_from_files and run_diagnostic_dialogue and is_decision_queue_empty:
        try:
            diag_decision = trigger_from_files(queue_empty=is_decision_queue_empty(queue))
            if diag_decision.should_run:
                specs = run_diagnostic_dialogue()
                print(f"self-diagnostic ran ({diag_decision.trigger}); queued {len(specs)} improvements")
                return 0
        except Exception as e:
            _ops("diagnostic_error", f"self-diagnostic skipped after error: {e}")
            print("self-diagnostic error; continuing normal debate:", e)

    chats = run_curator("./.venv/bin/python -m curator.decisions recent-chats 30").strip()
    signal = (queue + "\n" + chats)
    sig_hash = hashlib.sha256(signal.encode()).hexdigest()[:16]
    last = ""
    if os.path.exists(CFG + "/last_hash"): last = open(CFG + "/last_hash").read().strip()
    if sig_hash == last:
        print("no new intent since last debate — skip (~$0)"); return 0

    prompt = build_prompt(queue, chats, _focus_text() + _resources_text(), pragmatist=pragmatist_voice(signal))
    try:
        d, r = run_claude_json(prompt)
        # claude -p = Claude Max flat-rate -> $0 marginal real spend (no metered API call)
    except Exception as e:
        print("debate error:", e, "| raw:", (r.stdout[:200] if "r" in dir() else "")); return 1
    if consciousness_loop and os.environ.get("CONSCIOUSNESS_LOOP_DISABLE") != "1":
        try:
            status = consciousness_loop.maybe_append_from_council(d)
            if status.startswith("appended:"):
                _ops("model_dna_updated", status)
        except Exception as e:
            _ops("model_dna_update_error", str(e)[:200])

    # record we processed this signal (so we don't re-debate the same state)
    open(CFG + "/last_hash","w").write(sig_hash)
    total_today, _ = track.today("council")
    print(f"debated via claude -p (Claude Max flat-rate, $0 marginal). real metered today: ${total_today:.4f}")

    if not d.get("propose") or len((d.get("build_spec") or "")) < 15:
        _ops("nothing", "council debated, chose to build nothing this round")
        print("council verdict: build nothing this round"); return 0

    # Dedup guard: don't re-propose something already open/recent (the d011→d012 duplicate).
    # Compare the proposal's significant title words against the existing decision-queue text.
    import re as _re
    _stop = {"with","that","this","from","into","build","system","fixes","pipeline","intent","the","and","for"}
    _title_words = {w for w in _re.findall(r"[a-z]{4,}", (d.get("title") or "").lower()) if w not in _stop}
    _overlap = sum(1 for w in _title_words if w in queue.lower())
    if _title_words and _overlap >= max(2, (len(_title_words) + 1) // 2):
        _ops("nothing", f"skipped duplicate — '{d.get('title','')}' overlaps an existing decision")
        print("council: proposal duplicates an existing/recent decision — skip"); return 0

    gpt = gpt_voice(signal)
    why = (d.get("why","") + "  ⚖️ Council: " + (d.get("synthesis","")[:180])
           + (("  🤖 GPT(2nd lab): " + gpt) if gpt else ""))
    payload = json.dumps({"title":d["title"],"why":why,"build_spec":d["build_spec"],"risk":d.get("risk","low")})
    out = run_curator("./.venv/bin/python -m curator.decisions recommend", inp=payload)
    _ops("proposed", d.get("title",""), "James: approve or veto the proposal")
    print("proposed + surfaced:", out.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
