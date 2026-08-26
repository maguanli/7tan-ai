# -*- coding: utf-8 -*-
"""拉取全部 Release 资产列表，合并更新 assets.json"""
import json, os, urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com/repos/maguanli/7tan-ai"


def req(url):
    r = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + TOKEN,
        "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


releases = req(API + "/releases")
all_assets = []
for rel in releases:
    assets = req(API + "/releases/%s/assets" % rel["id"])
    all_assets.extend(assets)
    print("[%s] %d assets" % (rel["tag_name"], len(assets)))

all_assets.sort(key=lambda a: a.get("created_at", ""))
out = r"D:\7tan\7tanAI\assets.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(all_assets, f, ensure_ascii=False, indent=2)
print("SAVED %d assets -> %s" % (len(all_assets), out))
