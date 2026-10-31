# -*- coding: utf-8 -*-
import json, io, urllib.request

def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github+json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))

out = []
r = get("https://api.github.com/repos/deepseek-ai/dsh-superagent-prototype")
for k in ["full_name", "description", "created_at", "updated_at", "pushed_at", "stargazers_count", "forks_count", "open_issues_count", "language", "license", "default_branch", "size"]:
    v = r.get(k)
    if isinstance(v, dict):
        v = v.get("spdx_id")
    out.append("%s: %s" % (k, v))

try:
    c = get("https://api.github.com/repos/deepseek-ai/dsh-superagent-prototype/contents/")
    out.append("--- files (%d) ---" % len(c))
    for it in c:
        out.append("%-40s %s %s" % (it.get("name"), it.get("type"), it.get("size")))
except Exception as e:
    out.append("contents ERR %s" % e)

io.open(r"D:\7tan\7tanAI\data\_gh.txt", "w", encoding="utf-8").write("\n".join(out))
print("OK")
