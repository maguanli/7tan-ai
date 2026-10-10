# -*- coding: utf-8 -*-
"""把搜狐已转存的 11 张图与本地 12 张原图做感知比对，找出缺的是哪一张。"""
import io
import re
import urllib.request

from PIL import Image

HTML = r"D:\7tan\7tanAI\_sohu_readback.html"
LOCAL = r"D:\workspace\7tan_zhihu\miniworld\images"


def dhash(im, s=8):
    im = im.convert("L").resize((s + 1, s), Image.LANCZOS)
    px = list(im.getdata())
    bits = []
    for r in range(s):
        for c in range(s):
            bits.append(px[r * (s + 1) + c] > px[r * (s + 1) + c + 1])
    return sum(1 << i for i, b in enumerate(bits) if b)


def ham(a, b):
    return bin(a ^ b).count("1")


h = open(HTML, encoding="utf-8").read()
urls = []
for m in re.finditer(r'<img[^>]+src=["\']([^"\']*res\.mp\.sohu\.com[^"\']*)["\']', h):
    u = m.group(1)
    if u.startswith("//"):
        u = "https:" + u
    if u not in urls:
        urls.append(u)
    else:
        urls.append(u + "#dup")
print("urls:", len(urls))

remote = []
for i, u in enumerate(urls):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=30).read()
        im = Image.open(io.BytesIO(data))
        remote.append((i, im.size, dhash(im), len(data)))
    except Exception as e:
        print("  %d 下载失败 %s" % (i, e))
        remote.append((i, None, None, 0))

import os
local = []
for f in sorted(os.listdir(LOCAL)):
    p = os.path.join(LOCAL, f)
    im = Image.open(p)
    local.append((f, im.size, dhash(im), os.path.getsize(p)))

print("\n--- 远程 -> 最近的本地图 ---")
used = {}
for i, size, hh, n in remote:
    if hh is None:
        continue
    best = sorted(local, key=lambda L: ham(hh, L[2]))[:2]
    print("  #%2d %-11s %6dB  ->  %s (dist=%d)  次选 %s(%d)" % (
        i, "%dx%d" % size, n, best[0][0], ham(hh, best[0][2]), best[1][0], ham(hh, best[1][2])))
    used[best[0][0]] = used.get(best[0][0], 0) + 1

print("\n--- 本地 12 张的匹配情况 ---")
for f, size, hh, n in local:
    print("  %-11s %-9s %7dB  匹配次数=%d" % (f, "%dx%d" % size, n, used.get(f, 0)))
