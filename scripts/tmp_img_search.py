# -*- coding: utf-8 -*-
"""Commons 补充检索：闹钟 / 日历 / 办公桌"""
import json, sys, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "7TanBot/1.0 (https://www.7tan.com; admin@7tan.com)"}

QUERIES = [
    ("alarm",    "alarm clock"),
    ("alarm2",   "Wecker"),
    ("calendar", "calendar"),
    ("calendar2","Kalender"),
    ("desk",     "office desk computer"),
]

def search(q, limit=6):
    url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
           "&generator=search&gsrsearch=" + urllib.parse.quote("filetype:bitmap " + q) +
           "&gsrnamespace=6&gsrlimit=%d&prop=imageinfo&iiprop=url%%7Csize&iiurlwidth=1600" % limit)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    pages = (data.get("query") or {}).get("pages") or {}
    out = []
    for p in sorted(pages.values(), key=lambda x: x.get("index", 99)):
        ii = (p.get("imageinfo") or [{}])[0]
        u = ii.get("thumburl") or ii.get("url")
        if u:
            out.append((p.get("title", "?")[5:], u.split("?")[0], ii.get("width"), ii.get("height")))
    return out

for key, q in QUERIES:
    print("\n=== %s ===  (%s)" % (key, q))
    try:
        rs = search(q)
        if not rs: print("  (无结果)")
        for i, (t, u, w, h) in enumerate(rs, 1):
            print("  [%d] %s (%sx%s)" % (i, t[:66], w, h))
            print("      %s" % u)
    except Exception as e:
        print("  ERR:", e)
