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
import track
try:
    import certifi; SSLCTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSLCTX = ssl.create_default_context()

if os.path.exists(CFG + "/.disabled") or os.path.exists(HOME + "/.config/fpai/decisions/.recommend_disabled"):
    print("disabled"); sys.exit(0)

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

# guard: daily council cost cap
spent, _ = track.today("council")
if spent >= DAILY_CAP:
    print(f"council daily cap hit (${spent:.2f}/${DAILY_CAP})"); sys.exit(0)

# guard: one-at-a-time
queue = run_curator("./.venv/bin/python -m curator.decisions list")
if "awaiting" in queue:
    print("a decision already awaits James"); sys.exit(0)

chats = run_curator("./.venv/bin/python -m curator.decisions recent-chats 30").strip()
signal = (queue + "\n" + chats)
sig_hash = hashlib.sha256(signal.encode()).hexdigest()[:16]
last = ""
if os.path.exists(CFG + "/last_hash"): last = open(CFG + "/last_hash").read().strip()
if sig_hash == last:
    print("no new intent since last debate — skip (~$0)"); sys.exit(0)

SYS = (
 "You are a COUNCIL of three architects debating what James's system should build or focus on NEXT, "
 "based on his recently surfaced intents (chats) and the current decision queue. Give each architect a "
 "distinct, honest position:\n"
 "- PRAGMATIST: the cheapest, highest-leverage concrete build right now.\n"
 "- VISIONARY: what best advances the long-term self-evolving-system vision.\n"
 "- SKEPTIC: the riskiest gap, or what NOT to build (guard against cruft — James's rule is "
 "'concentrate harder, not build more').\n"
 "Then SYNTHESIZE into at most ONE concrete, buildable proposal. Be conservative: if nothing clearly "
 "warrants a build, propose nothing. Respond ONLY JSON: {\"pragmatist\":\"..\",\"visionary\":\"..\","
 "\"skeptic\":\"..\",\"synthesis\":\"one-paragraph verdict\",\"propose\":true|false,"
 "\"title\":\"<=8 words\",\"why\":\"one sentence\",\"build_spec\":\"concrete: what to build, where, the proof\","
 "\"risk\":\"low\"|\"med\"}. Prefer propose=false when uncertain.")
_focus = ""
try:
    _fp = REPO + "/core/STATE/COUNCIL_FOCUS.md"
    if os.path.exists(_fp):
        _focus = "\n\nSTANDING FOCUS — weight every proposal toward this (set by James):\n" + open(_fp).read().strip()
except Exception:
    pass
prompt = SYS + _focus + "\n\nDECISION QUEUE:\n" + queue + "\n\nRECENT INTENTS (chats):\n" + chats + "\n\nRespond with ONLY the JSON object."
try:
    import subprocess as _sp
    r = _sp.run([CLAUDE, "-p", prompt], stdin=_sp.DEVNULL, capture_output=True, text=True, timeout=150)
    txt = r.stdout.strip()
    d = json.loads(txt[txt.find("{"):txt.rfind("}")+1])
    # claude -p = Claude Max flat-rate -> $0 marginal real spend (no metered API call)
except Exception as e:
    print("debate error:", e, "| raw:", (r.stdout[:200] if "r" in dir() else "")); sys.exit(1)

# record we processed this signal (so we don't re-debate the same state)
open(CFG + "/last_hash","w").write(sig_hash)
total_today, _ = track.today("council")
print(f"debated via claude -p (Claude Max flat-rate, $0 marginal). real metered today: ${total_today:.4f}")

if not d.get("propose") or len((d.get("build_spec") or "")) < 15:
    _ops("nothing", "council debated, chose to build nothing this round")
    print("council verdict: build nothing this round"); sys.exit(0)

# Dedup guard: don't re-propose something already open/recent (the d011→d012 duplicate).
# Compare the proposal's significant title words against the existing decision-queue text.
import re as _re
_stop = {"with","that","this","from","into","build","system","fixes","pipeline","intent","the","and","for"}
_title_words = {w for w in _re.findall(r"[a-z]{4,}", (d.get("title") or "").lower()) if w not in _stop}
_overlap = sum(1 for w in _title_words if w in queue.lower())
if _title_words and _overlap >= max(2, (len(_title_words) + 1) // 2):
    _ops("nothing", f"skipped duplicate — '{d.get('title','')}' overlaps an existing decision")
    print("council: proposal duplicates an existing/recent decision — skip"); sys.exit(0)

gpt = gpt_voice(signal)
why = (d.get("why","") + "  ⚖️ Council: " + (d.get("synthesis","")[:180])
       + (("  🤖 GPT(2nd lab): " + gpt) if gpt else ""))
payload = json.dumps({"title":d["title"],"why":why,"build_spec":d["build_spec"],"risk":d.get("risk","low")})
out = run_curator("./.venv/bin/python -m curator.decisions recommend", inp=payload)
_ops("proposed", d.get("title",""), "James: approve or veto the proposal")
print("proposed + surfaced:", out.strip())
