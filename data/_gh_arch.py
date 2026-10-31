# -*- coding: utf-8 -*-
import io, re, sys

p = r"D:\7tan\7tanAI\data\_gh_007-architecture.md"
t = io.open(p, "r", encoding="utf-8", errors="ignore").read()
low = t.lower()
for k in ["router", "worker", "watchdog", "subagent", "sub-agent", "session", "trigger", "speculative", "fast path", "slow path", "daemon"]:
    print("%-12s %d" % (k, low.count(k)))
print("---- headings ----")
for m in re.finditer(r"(?m)^#{1,3} .+$", t):
    print(m.group(0)[:100])
