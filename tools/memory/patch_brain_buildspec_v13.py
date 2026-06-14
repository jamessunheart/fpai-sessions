import shutil, py_compile, sys, time
P = "/opt/sh-brain-src/curator/tgbot.py"
src = open(P, encoding="utf-8").read()

A = '''            q = _pl.Path("/opt/fpai/build_queue/intents.jsonl")
            q.parent.mkdir(parents=True, exist_ok=True)
            with q.open("a") as _f:
                _f.write(_json.dumps({"intent": intent, "chat_id": str(chat_id),
                                      "update_id": update_id,
                                      "ts": datetime.now(timezone.utc).isoformat(),
                                      "status": "open"}) + "\\n")
            log.info("build queued: %s", intent[:120])
            await tg.send("got it — queued for build. i will report back when it is done.")'''

B = '''            # Route the idea to a real spec now (system-carried artifact + proof),
            # then queue it for the build lane. Drafting != deploying — safe.
            spec = ""
            try:
                from .llm import complete
                _r = await complete(
                    "You are Ember drafting a tight build spec from James's one-line intent. "
                    "Output plainly, under 110 words: what it does (1 line) - the approach (2-3 bullets) - "
                    "where it likely lives - the proof it works. No preamble, no markdown fences.",
                    "Build intent: " + intent,
                    max_tokens=320, temperature=0.3, force_json=False)
                spec = (_r.text or "").strip()
            except Exception as _se:
                log.warning("spec draft failed: %s", _se)
            q = _pl.Path("/opt/fpai/build_queue/intents.jsonl")
            q.parent.mkdir(parents=True, exist_ok=True)
            with q.open("a") as _f:
                _f.write(_json.dumps({"intent": intent, "spec": spec, "chat_id": str(chat_id),
                                      "update_id": update_id,
                                      "ts": datetime.now(timezone.utc).isoformat(),
                                      "status": "specced" if spec else "open"}) + "\\n")
            log.info("build queued: %s", intent[:120])
            if spec:
                await tg.send("Here is how I would build it:\\n\\n" + spec +
                              "\\n\\nQueued for the build lane — say \\"approve\\" and a builder picks it up.")
            else:
                await tg.send("Got it — queued for build. I will report back when it is done.")'''

n = src.count(A)
if n != 1:
    print(f"ABORT: anchor {n}x"); sys.exit(1)
src = src.replace(A, B)
bak = P + ".bak-buildspec-v13-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy2(P, bak); open(P,"w",encoding="utf-8").write(src)
try:
    py_compile.compile(P, doraise=True); print(f"OK applied. bak={bak}")
except py_compile.PyCompileError as e:
    shutil.copy2(bak,P); print(f"REVERTED: {e}"); sys.exit(1)
