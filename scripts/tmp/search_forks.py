# -*- coding: utf-8 -*-
import io, sys, os, urllib.request, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def api(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

# 搜索 fork 仓库
try:
    data = api("https://api.github.com/search/repositories?q=stable-diffusion-stability-ai+in:name&sort=stars&per_page=10")
    for item in data.get("items", [])[:10]:
        print(item["full_name"], "| stars:", item["stargazers_count"], "| default:", item.get("default_branch"), "| size:", item.get("size"))
except Exception as e:
    print("search api failed:", e)
