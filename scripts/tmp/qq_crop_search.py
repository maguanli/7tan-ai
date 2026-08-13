# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image

im = Image.open("search_result.png").convert("RGB")
w, h = im.size
print("原图:", w, h)

# 搜索结果显示区（左侧面板：最佳匹配标题下方）
crop = im.crop((30, 440, 500, 760))
crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
crop.save("search_crop.png")
print("已保存 search_crop.png, 尺寸:", crop.size, "（原区域 x30-500 y440-760 放大2倍）")
