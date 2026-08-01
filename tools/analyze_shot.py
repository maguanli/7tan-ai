"""分析桌面截图：统计颜色分布，判断窗口是否正常渲染"""
import sys
from collections import Counter
from PIL import Image

path = sys.argv[1]
img = Image.open(path).convert("RGB")
w, h = img.size
print(f"size: {w}x{h}")

# 缩小采样
small = img.resize((160, 90))
px = list(small.getdata())
total = len(px)
counter = Counter(px)

# 判断主色调
top = counter.most_common(8)
for color, cnt in top:
    print(f"  #{color[0]:02X}{color[1]:02X}{color[2]:02X} : {cnt/total*100:.1f}%")

# 统计暗/亮占比
dark = sum(c for c, n in counter.items() if sum(c) < 120) / total
light = sum(c for c, n in counter.items() if sum(c) >= 500) / total
mid = 1 - dark - light
print(f"dark={dark*100:.1f}% light={light*100:.1f}% mid={mid*100:.1f}%")

# 多样性（颜色数）
print(f"distinct_colors={len(counter)}")

if light > 0.98:
    print("RESULT: 全白/接近全白 -> 窗口空白!")
elif dark > 0.98:
    print("RESULT: 全黑/接近全黑 -> 窗口空白!")
else:
    print("RESULT: 有内容渲染")
