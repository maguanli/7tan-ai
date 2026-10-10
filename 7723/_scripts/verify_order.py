# -*- coding: utf-8 -*-
r"""确认渲染区中 年份标题 与 配图 的顺序对应"""
import io, re, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
page = open(r"D:\7tan\7tanAI\7723\_scripts\_verify_82484_img.html", encoding="utf-8").read()
i = page.find('<div class="post-content">') + len('<div class="post-content">')
depth, k = 1, i
while depth > 0:
    no, nc = page.find('<div', k), page.find('</div>', k)
    if nc < 0:
        break
    if 0 <= no < nc:
        depth += 1; k = no + 4
    else:
        depth -= 1; k = nc + 6
region = page[i:k]

events = []
for m in re.finditer(r'ubb-title"[^>]*>(\d{4})<', region):
    events.append((m.start(), 'YEAR', m.group(1)))
for m in re.finditer(r'<img[^>]+src="[^"]*uploads/image[^"]*/([0-9O]+)\.png"', region):
    events.append((m.start(), 'IMG', m.group(1)))
for m in re.finditer(r'点击查看原帖', region):
    events.append((m.start(), 'BTN', ''))
events.sort()
print("事件序列（前 40 条）:")
for pos, kind, val in events[:40]:
    print("  %-5s %s" % (kind, val))
print("\n总计：YEAR=%d  IMG=%d  BTN=%d" % (
    sum(1 for e in events if e[1] == 'YEAR'),
    sum(1 for e in events if e[1] == 'IMG'),
    sum(1 for e in events if e[1] == 'BTN')))
