# -*- coding: utf-8 -*-
r"""精确切出 .post-content 渲染区，统计图片/组件/残留 UBB"""
import io, re, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
page = open(r"D:\7tan\7tanAI\7723\_scripts\_verify_82484_img.html", encoding="utf-8").read()

marker = '<div class="post-content">'
i = page.find(marker)
print("找到 post-content:", i >= 0)
start = i + len(marker)
# 配平 div
depth = 1
k = start
while depth > 0:
    no = page.find('<div', k)
    nc = page.find('</div>', k)
    if nc < 0:
        break
    if 0 <= no < nc:
        depth += 1
        k = no + 4
    else:
        depth -= 1
        k = nc + 6
region = page[start:k]
print("渲染区长度:", len(region))

imgs = re.findall(r'<img[^>]+src="([^"]+)"', region)
imgs = [u for u in imgs if 'uploads/image' in u]
print("正文图片数:", len(imgs))
print("ubb-title:", region.count('ubb-title'))
print("ubb-button/ubb-btn:", len(re.findall(r'ubb-btn', region)))
print("ubb-quote:", len(re.findall(r'ubb-quote', region)))
print("ubb-sep:", len(re.findall(r'ubb-sep', region)))
print("点击查看原帖:", region.count('点击查看原帖'))
print("残留 [img] :", region.count('[img]'), "| [/img]:", region.count('[/img]'))
print("残留 [title]:", region.count('[title]'), "| [btn= :", region.count('[btn='), "| [quote]:", region.count('[quote]'))
print("含 2009:", '2009' in region, "| 含 2015:", '2015' in region)
# 每个年份标题后是否紧跟图片
for m in re.finditer(r'ubb-title[^>]*>(\d{4})<', region):
    pass
seq = re.findall(r'(?s)(ubb-title[^>]*>(\d{4})<.*?)(<img[^>]+src="[^"]*uploads/image[^"]*")', region)
print("\n年份标题 -> 紧随配图:")
for s in re.finditer(r'ubb-title[^>]*>(\d{3,4})<', region):
    print("   title:", s.group(1))
