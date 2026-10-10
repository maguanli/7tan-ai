# -*- coding: utf-8 -*-
r"""核验线上 82484 帖子正文是否含「现在」结尾节（带缓存穿透）"""
import io, sys, time, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
url = "https://www.7tan.com/bbs/82484/?_cb=%d" % int(time.time())
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
h = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
print("抓取URL:", url)
print("页面长度:", len(h))
print("[title]现在[/title] :", "[title]现在[/title]" in h)
print("含 '2026 年 4 月 11 日' :", "2026 年 4 月 11 日" in h)
print("含 '7坛游戏社区（7tan.com）' :", "7坛游戏社区（7tan.com）" in h)
j = h.find("告诉大家一个遗憾的消息")
k = h.find("点击查看原帖", j)
seg = h[k:k+900] if k > 0 else "(未定位)"
print("---- 遗憾帖按钮之后的正文片段 ----")
print(seg)
