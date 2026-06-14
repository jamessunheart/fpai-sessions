#!/usr/bin/env python3
"""decisions — the one-chat decision queue.

Anything in the system that needs James's call goes here; it surfaces to his
Telegram ONE AT A TIME (no flood, no delay), and the system keeps moving as he
answers. The Gate function, realized through the one-chat vision.

  decisions.py add "<question>" "<opt1|opt2|...>"  — queue a decision
  decisions.py surface-next                         — send the next OPEN one to Telegram (skips if one is awaiting)
  decisions.py record <id> "<answer>"               — record James's answer, then surface the next
  decisions.py list                                 — show the queue

James answers in Telegram by replying:  <id>: <his answer>   (e.g. "d001: safe default")
"""
import json, os, sys, subprocess, time

HOME = os.path.expanduser("~")
Q = os.path.join(HOME, ".config/fpai/decisions/queue.jsonl")
NOTIFY = os.path.join(HOME, "FPAI_Cockpit/tools/build_loop/notify_telegram.sh")


def load():
    if not os.path.exists(Q):
        return []
    return [json.loads(l) for l in open(Q) if l.strip()]


def save(items):
    os.makedirs(os.path.dirname(Q), exist_ok=True)
    with open(Q, "w") as f:
        f.write("\n".join(json.dumps(i) for i in items) + ("\n" if items else ""))


def nid(items):
    return "d" + str(len(items) + 1).zfill(3)


def add(q, opts=""):
    items = load()
    items.append({"id": nid(items), "question": q, "options": opts,
                  "status": "open", "answer": None, "created": int(time.time())})
    save(items)
    print("queued:", items[-1]["id"])


def surface_next():
    items = load()
    if any(i["status"] == "awaiting" for i in items):
        aw = next(i for i in items if i["status"] == "awaiting")
        print(f"already awaiting {aw['id']} — one at a time, not surfacing another")
        return
    nxt = next((i for i in items if i["status"] == "open"), None)
    if not nxt:
        print("no open decisions")
        return
    opts = " / ".join(nxt["options"].split("|")) if nxt["options"] else ""
    n_left = sum(1 for i in items if i["status"] == "open") - 1
    msg = (f"🟡 <b>Decision needed</b> [{nxt['id']}]\n{nxt['question']}\n"
           + (f"\nOptions: {opts}\n" if opts else "\n")
           + f"\nReply: <code>{nxt['id']}: your answer</code>"
           + (f"\n({n_left} more queued after this)" if n_left > 0 else ""))
    try:
        subprocess.run([NOTIFY, msg], timeout=20)
    except Exception as e:
        print("notify failed:", e)
    nxt["status"] = "awaiting"
    nxt["surfaced_at"] = int(time.time())
    save(items)
    print("surfaced:", nxt["id"])


def record(did, answer):
    items = load()
    found = False
    for i in items:
        if i["id"] == did:
            i["status"] = "answered"
            i["answer"] = answer
            found = True
            break
    save(items)
    print("recorded:" if found else "id not found:", did)
    if found:
        surface_next()  # advance to the next decision — the loop keeps moving


def show():
    items = load()
    if not items:
        print("(no decisions)")
    for i in items:
        print(f"  {i['id']} · {i['status']:9} · {i['question'][:64]}" + (f"  → {i['answer']}" if i.get("answer") else ""))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "add":
        add(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
    elif cmd == "surface-next":
        surface_next()
    elif cmd == "record":
        record(sys.argv[2], sys.argv[3])
    else:
        show()


if __name__ == "__main__":
    main()
