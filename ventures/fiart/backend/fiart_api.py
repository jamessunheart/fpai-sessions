#!/usr/bin/env python3
"""Fi-art API — Phase 1 backend. Stdlib only (http.server + sqlite3), no deps.
Endpoints (same-origin via nginx /api/ proxy):
  GET  /api/health
  GET  /api/notes
  GET  /api/note?id=ID
  POST /api/mint     {title,denomination,description,educational_theme,creator,covenant}
  POST /api/collect  {note_id, collector}
Server enforces: Open-only mint, art-only fields, money-claim scan, covenant required.
Seeds from sibling notes.json on first run."""
import json, sqlite3, os, time, re, html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB   = os.environ.get("FIART_DB", "/var/lib/fiart/fiart.db")
PORT = int(os.environ.get("FIART_PORT", "8990"))
SEED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes_seed.json")

BANNED = [
    "legal tender","government-backed","government backed","federal reserve","treasury note",
    "guaranteed profit","guaranteed return","guaranteed appreciation","risk-free","risk free",
    "yield","interest rate","deposit","bank account","cash equivalent","redeemable for cash",
    "redeem for cash","investment opportunity","apy","roi guaranteed","banknote","money replacement",
    "fdic","insured","community insurance","default coverage","passive income","floor price guaranteed",
    "fractional revenue","guaranteed cash","guaranteed balance","savings account",
]

def scan_claims(text):
    t = (text or "").lower()
    return [p for p in BANNED if p in t]

def db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS notes(
        id TEXT PRIMARY KEY, type TEXT, title TEXT, denomination TEXT, creator TEXT,
        verified INTEGER, redeemable TEXT, redeemable_for TEXT, cash_redeemable INTEGER,
        backed_by TEXT, honored_by TEXT, transferable TEXT, expiration TEXT, risk_label TEXT,
        educational_theme TEXT, description TEXT, price REAL, currency TEXT, status TEXT,
        created_at INTEGER)""")
    c.execute("""CREATE TABLE IF NOT EXISTS collections(
        id INTEGER PRIMARY KEY AUTOINCREMENT, note_id TEXT, collector TEXT, created_at INTEGER)""")
    c.commit()
    if c.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 0 and os.path.exists(SEED):
        for n in json.load(open(SEED)):
            cols = ["id","type","title","denomination","creator","verified","redeemable",
                    "redeemable_for","cash_redeemable","backed_by","honored_by","transferable",
                    "expiration","risk_label","educational_theme","description","price","currency","status"]
            vals = [n.get(k) for k in cols]
            vals = [1 if v is True else 0 if v is False else v for v in vals]
            c.execute(f"INSERT INTO notes({','.join(cols)},created_at) VALUES({','.join('?'*len(cols))},?)",
                      vals + [int(time.time())])
        c.commit()
    c.close()

def row_to_note(r):
    d = dict(r)
    d["verified"] = bool(d.get("verified"))
    d["cash_redeemable"] = bool(d.get("cash_redeemable"))
    rv = d.get("redeemable")
    d["redeemable"] = True if rv in ("1",1,"true","True") else False if rv in ("0",0,"false","False") else rv
    return d

class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a): pass

    def do_GET(self):
        try:
            if self.path == "/api/health":
                return self._send(200, {"ok": True, "service": "fiart-api"})
            if self.path == "/api/notes":
                c = db(); rows = c.execute("SELECT * FROM notes ORDER BY created_at DESC").fetchall(); c.close()
                return self._send(200, {"notes": [row_to_note(r) for r in rows]})
            if self.path.startswith("/api/note"):
                from urllib.parse import urlparse, parse_qs
                nid = parse_qs(urlparse(self.path).query).get("id", [""])[0]
                c = db(); r = c.execute("SELECT * FROM notes WHERE id=?", (nid,)).fetchone(); c.close()
                return self._send(200, {"note": row_to_note(r)} if r else {"note": None})
            return self._send(404, {"error": "not found"})
        except Exception as e:
            return self._send(500, {"error": str(e)})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/mint":
                return self.mint(data)
            if self.path == "/api/collect":
                return self.collect(data)
            return self._send(404, {"error": "not found"})
        except Exception as e:
            return self._send(500, {"error": str(e)})

    def mint(self, d):
        if not d.get("covenant"):
            return self._send(403, {"error": "Creator Covenant must be signed before minting."})
        title = (d.get("title") or "").strip()
        if not title:
            return self._send(400, {"error": "Title required."})
        blob = " ".join(str(d.get(k, "")) for k in ("title","denomination","description","educational_theme"))
        hits = scan_claims(blob)
        if hits:
            return self._send(422, {"error": "Money-claim language blocked for art-only note.", "hits": hits})
        nid = "OPEN-" + str(int(time.time() * 1000))[-9:]
        note = dict(
            id=nid, type="open", title=html.escape(title)[:160],
            denomination=html.escape((d.get("denomination") or "ART").strip())[:24],
            creator=html.escape((d.get("creator") or "anonymous").strip())[:60], verified=0,
            redeemable="0", redeemable_for="Nothing — art only", cash_redeemable=0,
            backed_by="Meaning, beauty & culture", honored_by="No one", transferable="Yes",
            expiration="None", risk_label="Art-only",
            educational_theme=html.escape((d.get("educational_theme") or "—").strip())[:120],
            description=html.escape((d.get("description") or "").strip())[:600],
            price=None, currency="Fiart Marketplace Credit", status="live")
        c = db()
        cols = list(note.keys())
        c.execute(f"INSERT INTO notes({','.join(cols)},created_at) VALUES({','.join('?'*len(cols))},?)",
                  [note[k] for k in cols] + [int(time.time())])
        c.commit(); c.close()
        return self._send(201, {"ok": True, "id": nid, "note": row_to_note(note)})

    def collect(self, d):
        nid, who = d.get("note_id"), html.escape((d.get("collector") or "anonymous").strip())[:60]
        if not nid:
            return self._send(400, {"error": "note_id required."})
        c = db()
        if not c.execute("SELECT 1 FROM notes WHERE id=?", (nid,)).fetchone():
            c.close(); return self._send(404, {"error": "note not found"})
        c.execute("INSERT INTO collections(note_id,collector,created_at) VALUES(?,?,?)",
                  (nid, who, int(time.time())))
        c.commit()
        cnt = c.execute("SELECT COUNT(*) FROM collections WHERE note_id=?", (nid,)).fetchone()[0]
        c.close()
        return self._send(201, {"ok": True, "note_id": nid, "collectors": cnt})

if __name__ == "__main__":
    init()
    print(f"Fi-art API on :{PORT} (db={DB})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
