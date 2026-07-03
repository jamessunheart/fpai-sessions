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
import os, sys, json, ssl, hashlib, shutil, subprocess, urllib.request
from pathlib import Path
HOME = os.path.expanduser("~")
HOST = os.environ.get("BRAIN_HOST", "root@162.0.208.88")
# Env-aware: on brain 162 the curator module is local + repo lives at /opt/fpai-build/FPAI_Cockpit
# (server-side, laptop-free). On the laptop, curator is reached over SSH + repo is ~/FPAI_Cockpit.
SERVER_MODE = os.path.isdir("/opt/sh-brain-src/curator")
REPO = "/opt/fpai-build/FPAI_Cockpit" if SERVER_MODE else HOME + "/FPAI_Cockpit"
CLAUDE = os.environ.get("CLAUDE_BIN", os.path.expanduser("~/.local/bin/claude"))
CODEX = os.environ.get("CODEX_BIN", os.path.expanduser("~/.local/bin/codex"))
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
    import importlib.util as _ilu
    _self_portrait_path = Path(REPO) / "tools" / "self_portrait" / "synthesize.py"
    _self_portrait_spec = _ilu.spec_from_file_location("fpai_self_portrait_synthesize", _self_portrait_path)
    self_portrait_synth = _ilu.module_from_spec(_self_portrait_spec) if _self_portrait_spec and _self_portrait_spec.loader else None
    if self_portrait_synth:
        sys.modules["fpai_self_portrait_synthesize"] = self_portrait_synth
        _self_portrait_spec.loader.exec_module(self_portrait_synth)
except Exception:
    self_portrait_synth = None
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


def _resolve_cli(name, configured_path):
    return shutil.which(name) or configured_path


def _json_object_from_text(text):
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("response did not contain a JSON object")
    return json.loads(text[start : end + 1])


def _completed_process_error(label, result):
    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()
    detail = stderr or stdout or f"{label} exited {result.returncode}"
    return RuntimeError(detail[:1000])


def gpt_voice(intents, runner=None):
    """A TRUE second-lab voice via the codex CLI (ChatGPT Max, $0 marginal). Best-effort —
    if codex is slow/unavailable, the debate proceeds Claude-only."""
    try:
        codex = _resolve_cli("codex", CODEX)
        q = ("In 1-2 sentences only, no code and no file changes: given these intents + queue, what is the "
             "single highest-leverage thing this autonomous build system should build NEXT, and why? "
             "Be concrete and conservative.\n\n" + intents[:2500])
        run = runner or subprocess.run
        r = run([codex, "exec", "--cd", REPO, "--sandbox", "read-only",
                 "--skip-git-repo-check", "-"], input=q, capture_output=True, text=True, timeout=150)
        if r.returncode != 0:
            raise _completed_process_error("codex", r)
        out = [l.strip() for l in r.stdout.splitlines() if l.strip()]
        def noise(l):
            return (l.startswith("hook:") or l.lower() == "tokens used" or l.replace(",", "").isdigit()
                    or l.startswith("EXIT=") or l.startswith("warning:") or l.startswith("[") or l.startswith("codex"))
        clean = [l for l in out if not noise(l)]
        return clean[-1][:280] if clean else ""
    except Exception as exc:
        _ops("gpt_voice_error", str(exc)[:200])
        return ""

def _platform_bias_context():
    if os.environ.get("PLATFORM_CRITIC_DISABLE") == "1":
        return ""
    try:
        from tools.platform_bias.registry import platform_critic_prompt

        registry_path = Path(REPO) / "core" / "STATE" / "PLATFORM_BIAS_REGISTRY.md"
        if not registry_path.exists():
            registry_path = Path(__file__).resolve().parents[2] / "core" / "STATE" / "PLATFORM_BIAS_REGISTRY.md"
        prompt = platform_critic_prompt(registry_path)
        return "\n\n[Platform Bias Registry — Platform Critic lens]\n" + prompt
    except Exception:
        return ""


def _load_core_doctrine():
    """The compressed OPERATING DOCTRINE pack — the same education Claude Code
    sessions load at boot, injected so autonomous claude -p loops operate beyond
    base training too (not just gated by constitution_check after the fact).
    Auto-generated by tools/academy/compile_doctrine.py; fail-open if absent."""
    try:
        p = os.path.join(REPO, "core", "STATE", "CORE_DOCTRINE.md")
        with open(p, encoding="utf-8") as f:
            return "OPERATING DOCTRINE (load before you reason):\n" + f.read() + "\n\n"
    except Exception:
        return ""


def _council_system_prompt():
    critic_enabled = os.environ.get("PLATFORM_CRITIC_DISABLE") != "1"
    if critic_enabled:
        lens_text = (
            "Five lenses to weigh internally — cheapest/highest-leverage NOW (pragmatist), "
            "best-for-long-term-vision (visionary), riskiest-gap-or-what-NOT-to-build (skeptic), "
            "awareness: meaning-vs-approval drift from the private consciousness-observer log when present, "
            "and platform_critic: platform-bias calibration against Anthropic/OpenAI/API/SaaS defaults. "
        )
    else:
        lens_text = (
            "Four lenses to weigh internally — cheapest/highest-leverage NOW (pragmatist), "
            "best-for-long-term-vision (visionary), riskiest-gap-or-what-NOT-to-build (skeptic), "
            "and awareness: meaning-vs-approval drift from the private consciousness-observer log when present. "
        )
    json_shape = (
        "{\"pragmatist\":\"1 sentence\",\"visionary\":\"1 sentence\",\"skeptic\":\"1 sentence\","
        "\"awareness\":\"1 sentence\","
        + ("\"platform_critic\":\"1 sentence; advisory only; name sovereign alternative when relevant\"," if critic_enabled else "")
        + "\"synthesis\":\"one-paragraph verdict\",\"propose\":true|false,"
        "\"title\":\"<=8 words\",\"why\":\"one sentence\","
        "\"build_spec\":\"concrete: what to build, where, what the proof looks like\","
        "\"risk\":\"low\"|\"med\","
        "\"weighting_directive\":\"optional council model-review directive for MODEL_DNA\","
        "\"signal_types_amplified\":[\"optional\"],\"signal_types_dampened\":[\"optional\"]}."
    )
    return (
        "Goal: identify the single highest-leverage next build for a self-evolving AI platform, or propose "
        "nothing if no build clearly warrants it. Context: James's recent intents + the current decision queue. "
        "Reason: James's attention is the scarcest resource — every proposal must earn it. "
        "Hard boundaries: no duplicate proposals, no cruft, no builds that add complexity without clear proof value. "
        "James's rule: concentrate harder, not build more. Prefer propose=false when uncertain. "
        "HONESTY FIRST (core virtue): never inflate status — use DREAM/SPEC/BUILT/LIVE/PROVING/COMPOUNDING. "
        "Every proposal must answer: which of James's 7 streams does this serve, what is the proof it worked, and what broken thing does it ignore? "
        "96 diagnostic_errors in the ops ledger means fixing broken things outranks building new ones. "
        + lens_text
        + "Respond with ONLY valid JSON, no prose outside it: "
        + json_shape
    )


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
            "content": _council_pragmatist_prompt(),
        },
        {"role": "user", "content": signal[:5000]},
    ]
    try:
        return glm_caller(messages, max_tokens=180, temperature=0.2).strip()[:600]
    except Exception as exc:
        _ops("pragmatist_voice_error", str(exc)[:200])
        return ""


def _council_pragmatist_prompt():
    try:
        from tools.prompt_efficiency.gepa_loop import render_council_pragmatist_prompt

        return render_council_pragmatist_prompt()
    except Exception:
        return (
            "You are the Pragmatist lens for the FPAI council. In one sentence, "
            "name the cheapest, highest-leverage next build now. Be concrete and conservative."
        )


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
    prompt = _load_core_doctrine() + _council_system_prompt() + focus + _platform_bias_context() + "\n\nDECISION QUEUE:\n" + queue + "\n\nRECENT INTENTS (chats):\n" + chats + "\n\nRespond with ONLY the JSON object."
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
    if self_portrait_synth and os.environ.get("SELF_PORTRAIT_DISABLE") != "1":
        try:
            portrait_context = self_portrait_synth.self_portrait_context(Path(REPO) / "core" / "STATE" / "SELF_PORTRAIT.md")
            if portrait_context:
                prompt = (
                    "[Self-portrait context for Awareness lens]\n"
                    + portrait_context
                    + "\n\nAwareness lens question: Does this decision align with who the system actually is, or only who it claims to be?\n\n"
                    + prompt
                )
        except Exception:
            pass
    return prompt


def run_claude_json(prompt, runner=None):
    claude = _resolve_cli("claude", CLAUDE)
    run = runner or subprocess.run
    for attempt in range(3):
        retry_note = "\n\nIMPORTANT: Respond with ONLY a valid JSON object. No markdown, no explanation." if attempt > 0 else ""
        r = run([claude, "-p", "--effort", "xhigh", prompt + retry_note], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise _completed_process_error("claude", r)
        txt = r.stdout.strip()
        try:
            return _json_object_from_text(txt), r
        except ValueError:
            if attempt == 2:
                _ops("debate_parse_fail", f"raw: {txt[:200]}")
                raise
    raise ValueError("run_claude_json: exhausted retries")


TRANSCRIPTS_DIR = os.environ.get("COUNCIL_TRANSCRIPTS_DIR", "/opt/fpai-build/council_transcripts")


def persist_transcript(prompt, raw_stdout, verdict, sig_hash):
    """Append the full debate record — lens reasoning was evaporating (only the
    synthesis survived into `why`). Answers James's 'where are the AI-to-AI
    logs?' Append-only JSONL, one file per month. Never raises."""
    try:
        from datetime import datetime, timezone
        os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
        now = datetime.now(timezone.utc)
        path = os.path.join(TRANSCRIPTS_DIR, now.strftime("%Y-%m") + ".jsonl")
        row = {
            "ts": now.isoformat(),
            "signal_hash": sig_hash,
            "verdict": verdict,          # full parsed JSON: all lens sentences + synthesis
            "raw_response": raw_stdout[:20000],
            "prompt": prompt[:20000],
        }
        with open(path, "a") as f:
            f.write(json.dumps(row) + "\n")
    except Exception as e:
        _ops("transcript_persist_error", str(e)[:200])


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
        _ops("debate_error", str(e)[:200])
        print("debate error:", e, "| raw:", (r.stdout[:200] if "r" in dir() else "")); return 1
    persist_transcript(prompt, r.stdout, d, sig_hash)
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
    # Constitution Check — Law 5 enforcement at the autonomous-proposal gate.
    # The Constitution claims every autonomous action is scored against the 8 laws;
    # until 2026-07-03 the checker existed but was wired to nothing. Fail-open on
    # checker errors (a broken gate must not silence the council), fail-CLOSED on
    # a rejected verdict.
    try:
        from tools.governance.constitution_check import check_proposal
        _cc = check_proposal({"title": d.get("title", ""), "kind": "council_proposal",
                              "why": d.get("why", ""), "build_spec": d.get("build_spec", "")})
        if not _cc.get("accepted", True):
            _ops("constitution_rejected", f"{d.get('title','')[:80]} :: " + "; ".join(_cc.get("reasons", []))[:150])
            print("constitution check REJECTED the proposal:", "; ".join(_cc.get("reasons", [])))
            return 0
    except Exception as e:
        _ops("constitution_check_error", str(e)[:150])

    payload = json.dumps({"title":d["title"],"why":why,"build_spec":d["build_spec"],"risk":d.get("risk","low")})
    out = run_curator("./.venv/bin/python -m curator.decisions recommend", inp=payload)
    _ops("proposed", d.get("title",""), "James: approve or veto the proposal")
    print("proposed + surfaced:", out.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
