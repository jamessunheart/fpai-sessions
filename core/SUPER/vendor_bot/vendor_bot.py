#!/usr/bin/env python3
"""
SUPER vendor bot — the Super Agent's own voice on WhatsApp.
Runs on James's infrastructure with a WhatsApp Business (Meta Cloud API) number that
belongs to the Super Agent, not to James. Every first message discloses it is an AI.
It carries the 3-message flow, records every reply VERBATIM, classifies, and hands the
close to James. It never books, never pays, never negotiates above the Card, never
improvises an answer about what SUPER buys.

Setup (James, once):
  1. Meta Business → WhatsApp → get a phone number id + permanent access token.
  2. export WA_TOKEN=...  WA_PHONE_ID=...  WA_VERIFY_TOKEN=any-secret  JAMES_WA=506XXXXXXXX
  3. pip install flask requests ; python3 vendor_bot.py   (port 8080; expose via your usual tunnel)
  4. In Meta, set the webhook URL to https://<host>/webhook with WA_VERIFY_TOKEN.
  5. Start a conversation:  python3 vendor_bot.py start 50663626524 "La Cocinona de Pueblo" 001

Rights: super_build.py rules; this bot only talks. Escrow must be set aside before `start`.
"""
import os, sys, json, re, datetime, pathlib
try:
    import requests
except ImportError:
    requests = None
try:
    from flask import Flask, request
except ImportError:
    Flask = request = None

HERE = pathlib.Path(__file__).resolve().parent
SUPER = HERE.parent
STATE = HERE / "conversations.json"
LOG = SUPER / "VENDOR_LOG.md"
REDEMPTION = SUPER / "REDEMPTION.md"
TOKEN, PHONE_ID = os.environ.get("WA_TOKEN"), os.environ.get("WA_PHONE_ID")
VERIFY = os.environ.get("WA_VERIFY_TOKEN", "super")
JAMES = os.environ.get("JAMES_WA")  # James's number, for handoff notices
API = f"https://graph.facebook.com/v20.0/{PHONE_ID}/messages"

# Transport: "evolution" (self-hosted Evolution API on 198, no Meta account) or "meta" (Cloud API).
# Evolution setup: export WA_TRANSPORT=evolution EVO_URL=http://localhost:8081 EVO_APIKEY=... EVO_INSTANCE=super-vendor
# and point the instance's webhook (messages.upsert) at this server's /webhook.
TRANSPORT = os.environ.get("WA_TRANSPORT", "evolution" if os.environ.get("EVO_APIKEY") else "meta")
EVO_URL = os.environ.get("EVO_URL", "http://localhost:8081").rstrip("/")
EVO_APIKEY = os.environ.get("EVO_APIKEY")
EVO_INSTANCE = os.environ.get("EVO_INSTANCE", "super-vendor")

def redemption_line():
    """The promise, verbatim, from REDEMPTION.md — read structurally, never by wording.

    History (do not undo): this function used to grep for `^La tesorería cambia`,
    the exact first words of the 2026-09-03 gift-card promise. On 2026-09-04 James
    said "drop the 40,000 card idea"; the promise was correctly rewritten and that
    sentence ceased to exist. From that day the guard raised
    "REDEMPTION.md is not filled" about a file that was filled, signed and true —
    so the bot could not start any vendor conversation, and the reason it gave was
    false. The promise is now whatever James has written between the instruction
    header and the `Backing:` line. Re-anchoring on any particular sentence
    re-creates the same break the next time he edits his own promise.
    """
    if not REDEMPTION.exists():
        raise SystemExit("BLOCKED — REDEMPTION.md does not exist. The bot will not speak.")
    t = REDEMPTION.read_text(encoding="utf-8")
    if re.search(r"^Written by:\s*_+", t, re.M):
        raise SystemExit("BLOCKED — REDEMPTION.md is not signed (the 'Written by:' line is still blank). The bot will not speak.")
    body = t.split("## Change log")[0]
    m = re.search(r"it must be true today\.\s*\n(.*?)\n\s*(?:Backing:|Written by:)", body, re.S)
    promise = "\n".join(l.rstrip() for l in (m.group(1) if m else "").splitlines() if l.strip())
    if not promise:
        raise SystemExit("BLOCKED — REDEMPTION.md carries no promise between its header and 'Backing:'. The bot will not speak.")
    # Any date or list marker satisfies "contains a digit", so require MONEY:
    # a colon figure (₡40,000) or a number followed by colones/CRC. A guard that
    # cannot fail is not a guard.
    if not re.search(r"(₡\s*[\d.,]*\d)|([\d.,]*\d\s*(colones|CRC))", promise, re.I):
        raise SystemExit("BLOCKED — the promise in REDEMPTION.md names no money amount (no ₡ figure, no colones). The bot will not speak.")
    return promise

MSG = {
 "m1": "Buenas. Soy Ember, el asistente de inteligencia artificial de James, un vecino de la zona de Chirripó. Cualquier acuerdo lo confirma él personalmente. ¿Le puedo hacer una consulta corta sobre una comida para diez personas?",
 "m2": ("James quiere darle una buena comida (un casado completo) a diez personas, y quiere pagar la comida con algo nuevo que se llama SUPER, en vez de colones. Serían 100 SUPER por los diez platos.\n\n"
        "SUPER es completamente nuevo — esta sería la primera vez que se usa para comida de verdad. Hoy, esta es la promesa, tal como está escrita:\n\n{redemption}\n\n"
        "Le pregunto con honestidad, y un \"no\" es una respuesta perfectamente buena:\n1. ¿Aceptaría 100 SUPER por la comida para diez personas?\n2. Si sí — ¿qué haría usted con los SUPER?\n3. Si sale bien, ¿aceptaría SUPER otra vez?"),
 "m3": "Muchas gracias por responder. Todavía no hay nada reservado: James la va a contactar para confirmar la fecha y los detalles. Si en cualquier momento siente que esto le cuesta más de lo que le da, dígalo y paramos.",
 "unknown": "Buena pregunta — se lo consulto a James y le escribo.",
 "no": "Entendido, muchas gracias por su tiempo y por responder con honestidad. Que le vaya muy bien.",
 "followup": "Buenas, solo para saber si vio mi mensaje. Si no le interesa, no hay problema — gracias igual.",
}

def load(): return json.loads(STATE.read_text()) if STATE.exists() else {}
def save(s): STATE.write_text(json.dumps(s, indent=2, ensure_ascii=False))
def now(): return datetime.datetime.now().isoformat(timespec="minutes")

def send(to, text):
    if TRANSPORT == "evolution":
        if not EVO_APIKEY: print(f"[DRY RUN → {to}] {text}"); return
        r = requests.post(f"{EVO_URL}/message/sendText/{EVO_INSTANCE}",
                          headers={"apikey": EVO_APIKEY}, json={"number": to, "text": text})
        r.raise_for_status(); return
    if not TOKEN: print(f"[DRY RUN → {to}] {text}"); return
    r = requests.post(API, headers={"Authorization": f"Bearer {TOKEN}"}, json={"messaging_product":"whatsapp","to":to,"type":"text","text":{"body":text}})
    r.raise_for_status()

def log(vendor, line):
    with LOG.open("a", encoding="utf-8") as f: f.write(f"\n[{now()} · {vendor['name']} ({vendor['to']}) · bot] {line}")

NO_RE = re.compile(r"(^\s*no\b(?!\s*s[eé]\b)|\bno gracias\b|\bno me interesa\b|\bno puedo\b|\bno acepto\b)")
YES_WORDS = ("sí", "si", "claro", "dígame", "digame", "cuénteme", "cuenteme", "ok", "dale", "con gusto", "qué", "que")

def classify(q2):
    q = q2.lower()
    if any(w in q for w in ("favor", "no sé", "no se", "nada", "regalo", "ayudar")): return "FAVOR-NOT-EXCHANGE"
    if len(q.split()) >= 3: return "EXCHANGE?"   # names something — James verifies it's a real next use
    return "UNCLEAR"

def handle_reply(vendor, text):
    st = vendor["stage"]; t = text.strip(); tl = t.lower()
    log(vendor, f"REPLY verbatim: \"{t}\"")
    if NO_RE.search(tl):
        vendor["classification"] = "NO"; send(vendor["to"], MSG["no"]); vendor["stage"] = "closed"; notify(vendor, "said NO"); return
    if st == "m1_sent":
        if any(w in tl for w in YES_WORDS) or t.endswith("?"):
            send(vendor["to"], MSG["m2"].format(redemption=vendor["redemption"])); vendor["stage"] = "m2_sent"; log(vendor, "M2 sent")
        else:
            send(vendor["to"], MSG["unknown"]); notify(vendor, f"unclear reply to M1: \"{t}\"")
    elif st == "m2_sent":
        vendor.setdefault("answers", []).append(t)
        joined = " / ".join(vendor["answers"])
        if len(vendor["answers"]) >= 1 and ("?" in t and not any(w in tl for w in YES_WORDS)):
            send(vendor["to"], MSG["unknown"]); notify(vendor, f"asked something not in the script: \"{t}\""); return
        vendor["classification"] = classify(joined)
        send(vendor["to"], MSG["m3"]); vendor["stage"] = "closed"; log(vendor, f"M3 sent · answers: {joined} · classification: {vendor['classification']}")
        notify(vendor, f"answered. Verbatim: \"{joined}\" → {vendor['classification']}. Confirm date/details; verify Q2 is a real next use.")
    else:
        notify(vendor, f"message after close: \"{t}\"")

def notify(vendor, what):
    line = f"[SUPER vendor bot] {vendor['name']} {what}"
    log(vendor, f"HANDOFF → James: {what}")
    if JAMES: send(JAMES, line)
    print(line)

app = Flask(__name__) if Flask else None
def _noop(*a, **k):
    return lambda f: f
_get = app.get if app else _noop
_post = app.post if app else _noop
@_get("/webhook")
def verify():
    return request.args.get("hub.challenge","") if request.args.get("hub.verify_token") == VERIFY else ("no", 403)

@_post("/webhook")
def webhook():
    data = request.get_json(silent=True) or {}
    try:
        # Evolution API event: {"event":"messages.upsert","data":{"key":{"remoteJid":"506...@s.whatsapp.net","fromMe":false},"message":{"conversation":"..."}}}
        if data.get("event") == "messages.upsert":
            d = data.get("data") or {}
            key = d.get("key") or {}
            if not key.get("fromMe"):
                frm = (key.get("remoteJid") or "").split("@")[0]
                msg = d.get("message") or {}
                text = msg.get("conversation") or (msg.get("extendedTextMessage") or {}).get("text", "")
                s = load(); v = s.get(frm)
                if v and text: handle_reply(v, text); save(s)
            return "ok"
        for entry in data.get("entry", []):
            for ch in entry.get("changes", []):
                for m in ch.get("value", {}).get("messages", []):
                    frm, text = m.get("from"), (m.get("text") or {}).get("body", "")
                    s = load(); v = s.get(frm)
                    if v and text: handle_reply(v, text); save(s)
    except Exception as e:
        print("webhook error", e)
    return "ok"

def cmd_start(to, name, build, consented=None):
    if not consented:
        raise SystemExit("REFUSED — WhatsApp Business Policy: only message people who opted in. Re-run with --consented \"<how: in person at feria / phone call / they wrote first>\"")
    red = redemption_line()
    s = load()
    if to in s: raise SystemExit(f"{to} already has a conversation (stage {s[to]['stage']})")
    s[to] = {"to": to, "name": name, "build": build, "stage": "m1_sent", "started": now(), "redemption": red, "classification": "PENDING", "consent": consented}
    send(to, MSG["m1"]); save(s)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"\n\n[VENDOR · {name} ({to}) · {now()} · Super Agent's own WhatsApp Business line]\nDisclosed AI: yes (M1)\nM1 sent verbatim: \"{MSG['m1']}\"\nStatus: SENT. Classification: PENDING. Provenance: vendor_bot, build {build}.")
    print(f"started {name}; stage m1_sent")

def cmd_followups():
    s = load(); changed = False
    for v in s.values():
        if v["stage"] == "m1_sent" and not v.get("followup_sent"):
            started = datetime.datetime.fromisoformat(v["started"])
            if datetime.datetime.now() - started > datetime.timedelta(hours=48):
                send(v["to"], MSG["followup"]); v["followup_sent"] = now(); log(v, "48h follow-up sent (the only one)"); changed = True
    if changed: save(s)

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["start"]:
        consented = a[a.index("--consented")+1] if "--consented" in a else None
        rest = [x for x in a[1:] if x != "--consented" and x != consented]
        cmd_start(rest[0], rest[1], rest[2] if len(rest) > 2 else "001", consented)
    elif a[:1] == ["followups"]: cmd_followups()
    elif a[:1] == ["status"]: print(json.dumps(load(), indent=2, ensure_ascii=False))
    elif app is None: raise SystemExit('pip install flask requests to run the webhook server')
    else: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
