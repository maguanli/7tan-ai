# -*- coding: utf-8 -*-
import json, io, base64, urllib.request

def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github+json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))

r = get("https://api.github.com/repos/deepseek-ai/dsh-superagent-prototype/readme")
txt = base64.b64decode(r["content"]).decode("utf-8", "ignore")
io.open(r"D:\7tan\7tanAI\data\_gh_readme.md", "w", encoding="utf-8").write(txt)
print("README chars", len(txt))

try:
    d = get("https://api.github.com/repos/deepseek-ai/dsh-superagent-prototype/contents/docs")
    for it in d:
        print("docs/", it["name"], it["type"], it.get("size"))
except Exception as e:
    print("docs err", e)
