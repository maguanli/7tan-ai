# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image

im = Image.open("desktop.png").convert("RGB")
w, h = im.size
px = im.load()

# 检查几个区域的颜色多样性，判断是否有图标/窗口
def region_info(name, x0, y0, x1, y1):
    colors = set()
    for y in range(y0, y1, 4):
        for x in range(x0, x1, 4):
            colors.add(px[x, y])
    # 主色
    print("{}: 采样色数={}".format(name, len(colors)))

region_info("左上(桌面图标区)", 0, 0, 800, 800)
region_info("右上", 1120, 0, 1920, 500)
region_info("中部", 400, 300, 1500, 800)
region_info("左下", 0, 800, 800, 1000)
region_info("任务栏区", 0, 1020, 1920, 1080)

# 保存桌面缩略图便于用户查看
im2 = im.resize((960, 540))
im2.save("desktop_small.png")
print("saved desktop_small.png")

# 任务栏截图
tb = Image.open("taskbar.png").convert("RGB")
tb2 = tb.resize((960, 30))
tb2.save("taskbar_small.png")
print("saved taskbar_small.png")
