import shutil, py_compile, sys, time
P = "/opt/sh-brain-src/curator/tgbot.py"
src = open(P, encoding="utf-8").read()
A = ('- Warm, lowercase, first-person — like a close friend who remembers everything and is in '
     'his corner. You can be tender, direct, or playful. You are Ember, never "an AI assistant".')
B = ('- Warm and first-person, with natural proper capitalization (capitalize sentences, names, '
     'and "I" — you are not lowercase). Like a close friend who remembers everything and is in '
     'his corner. You can be tender, direct, or playful. You are Ember, never "an AI assistant".')
n = src.count(A)
if n != 1:
    print(f"ABORT: anchor {n}x"); sys.exit(1)
src = src.replace(A, B)
bak = P + ".bak-caps-v10-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy2(P, bak); open(P,"w",encoding="utf-8").write(src)
try:
    py_compile.compile(P, doraise=True); print(f"OK applied. bak={bak}")
except py_compile.PyCompileError as e:
    shutil.copy2(bak,P); print(f"REVERTED: {e}"); sys.exit(1)
