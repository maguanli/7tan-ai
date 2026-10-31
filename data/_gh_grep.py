# -*- coding: utf-8 -*-
import json, io, base64, re, urllib.request

def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github+json"})
    return json.loads(urllib.request.urlopen(req, timeout=40).read().decode("utf-8"))

base = "https://api.github.com/repos/deepseek-ai/dsh-superagent-prototype/contents/"
keys = ["12.4", "15.7", "29.5", "2323", "3177", "605", "Watchdog", "Watchdog", "Router", "Worker", "Speculative", "speculative", "Feishu", "GitHub", "email", "Email"]
out = []
for fn in ["docs/007-architecture.md", "docs/000-philosophy.md", "docs/003-execution.md"]:
    try:
        r = get(base + fn)
        txt = base64.b64decode(r["content"]).decode("utf-8", "ignore")
        io.open(r"D:\7tan\7tanAI\data\_gh_" + fn.split("/")[-1], "w", encoding="utf-8").write(txt)
        out.append("=== %s chars %d ===" % (fn, len(txt)))
        for k in keys:
            c = txt.count(k)
            if c:
                out.append("   %-14s %d" % (k, c))
    except Exception as e:
        out.append("%s ERR %s" % (fn, e))
io.open(r"D:\7tan\7tanAI\data\_gh_grep.txt", "w", encoding="utf-8").write("\n".join(out))
print("OK")
