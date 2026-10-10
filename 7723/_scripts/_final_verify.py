# -*- coding: utf-8 -*-
r"""82484 最终全量核验：结尾节 + 65 原帖按钮 + 7 配图 + 标题"""
import io, sys, time, re, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
url = "https://www.7tan.com/bbs/82484/?_cb=%d" % int(time.time())
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
h = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")

# 只取正文渲染区（topic-content 到 post-actions 之间）
m = re.search(r'class="topic-content"(.*?)post-actions', h, re.S)
body = m.group(1) if m else h

print("== 标题 ==")
t = re.search(r'<title>(.*?)</title>', h)
print(t.group(1) if t else "?")

print("== 结尾「现在」节 ==")
print("  渲染出 ubb-title 现在 :", '<div class="ubb-title">现在</div>' in body)
print("  上线日期字样          :", '2026 年 4 月 11 日' in body)
print("  7tan 首页按钮         :", 'href="https://www.7tan.com/"' in body and '访问 7坛游戏社区' in body)

print("== 原有内容未丢 ==")
print("  『点击查看原帖』按钮数 :", body.count('点击查看原帖'))
print("  原帖链接 bbs/NNNN/ 数  :", len(re.findall(r'/bbs/\d+/', body)))
print("  配图 <img ... uploads/image> 数 :", len(re.findall(r'uploads/image/[^"]+\.png', body)))
print("  各年标题 div.ubb-title  :", re.findall(r'<div class="ubb-title">([^<]+)</div>', body))
