# -*- coding: utf-8 -*-
import io, re

p = r"D:\7tan\7tanAI\data\_gh_007-architecture.md"
t = io.open(p, "r", encoding="utf-8", errors="ignore").read()

def ctx(word, n=260, limit=3):
    out = []
    for m in re.finditer(word, t, re.I):
        s = max(0, m.start() - n // 2)
        out.append(t[s:s + n].replace("\n", " "))
        if len(out) >= limit:
            break
    return out

for w in ["router", "MasterAssessor", "subagent"]:
    print("########", w)
    for c in ctx(w):
        print("  ...", c, "\n")

# sections about Sessions and Triggers
for name in ["### Store", "### Sources", "### MasterAssessor"]:
    i = t.find(name)
    if i >= 0:
        print("=========", name)
        print(t[i:i + 700])
