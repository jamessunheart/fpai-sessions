#!/usr/bin/env python3
"""track — append a real-metered AI call to the cost ledger + read today's total.
Reuses ~/.config/fpai/cost/{ledger.jsonl,rates.json}. Autonomous API calls (recommender,
council debate, ai_review) bill REAL money (not the flat Max plan), so they log billing="metered".

  track.py log <label> <model> <in_tok> <out_tok>   -> append + print est_usd
  track.py today [label_prefix]                      -> today's metered total (+ breakdown)
  track.py remaining                                 -> daily cap minus today's metered spend
"""
import os, sys, json, datetime
HOME = os.path.expanduser("~")
COST = HOME + "/.config/fpai/cost"
LEDGER = COST + "/ledger.jsonl"
RATES = COST + "/rates.json"

def _rates():
    try:
        return json.load(open(RATES))
    except Exception:
        return {"rates": {}, "caps": {"daily_usd": 20.0}}

def _cost(model, it, ot):
    r = _rates()["rates"]; m = r.get(model) or r.get("_default") or {"in":5.0,"out":15.0}
    return round(it/1e6*m["in"] + ot/1e6*m["out"], 6)

def log(label, model, it, ot):
    usd = _cost(model, int(it), int(ot))
    rec = {"timestamp": datetime.datetime.now().astimezone().isoformat(),
           "label": label, "model": model, "input_tokens": int(it), "output_tokens": int(ot),
           "est_usd": usd, "billing": "metered", "source": "autonomous"}
    os.makedirs(COST, exist_ok=True)
    with open(LEDGER, "a") as f: f.write(json.dumps(rec) + "\n")
    return usd

def today(prefix=""):
    today_s = datetime.date.today().isoformat()
    total = 0.0; by = {}
    if os.path.exists(LEDGER):
        for ln in open(LEDGER):
            try: r = json.loads(ln)
            except Exception: continue
            if r.get("billing") != "metered": continue          # only real money
            if not str(r.get("timestamp","")).startswith(today_s): continue
            lab = r.get("label","?")
            if prefix and not lab.startswith(prefix): continue
            total += float(r.get("est_usd",0)); by[lab] = by.get(lab,0)+float(r.get("est_usd",0))
    return round(total,4), by

def cap():
    return float(_rates().get("caps",{}).get("daily_usd",20.0))

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv)>1 else "today"
    if cmd == "log":
        print(f"{log(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5]):.6f}")
    elif cmd == "remaining":
        t,_ = today(); print(f"{max(0.0, cap()-t):.4f}")
    else:
        t, by = today(sys.argv[2] if len(sys.argv)>2 else "")
        print(f"today metered: ${t:.4f} / ${cap():.0f} cap")
        for k,v in sorted(by.items(), key=lambda x:-x[1]): print(f"  {k}: ${v:.4f}")
