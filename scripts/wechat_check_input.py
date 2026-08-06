# -*- coding: utf-8 -*-
"""检查 wechat_input2.png 输入框截图"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

SCREENSHOT_DIR = r"D:\7tan\7tanAI\data\screenshots"

# 像素分析
img = Image.open(SCREENSHOT_DIR + r"\wechat_input2.png").convert('RGB')
w, h = img.size
print('输入框截图尺寸:', w, h)
import statistics
g = img.convert('L')
vals = list(g.getdata())
print('灰度均值=%.1f 标准差=%.1f' % (statistics.mean(vals), statistics.pstdev(vals)))

# 放大2x OCR
img2 = img.resize((w*2, h*2), Image.LANCZOS)
p = SCREENSHOT_DIR + r"\wechat_input2_zoom.png"
img2.save(p)

from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.globalization import Language
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage import StorageFile

async def ocr_file(path, scale=2.0, ox=0, oy=0):
    file = await StorageFile.get_file_from_path_async(path)
    stream = await file.open_async(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = OcrEngine.try_create_from_language(Language("zh-CN"))
    if engine is None:
        engine = OcrEngine.try_create_from_user_profile_languages()
    result = await engine.recognize_async(bitmap)
    out = []
    for line in result.lines:
        words = line.words
        if words:
            xs = [wd.bounding_rect.x for wd in words]
            ys = [wd.bounding_rect.y for wd in words]
            x2 = max(wd.bounding_rect.x + wd.bounding_rect.width for wd in words)
            y2 = max(wd.bounding_rect.y + wd.bounding_rect.height for wd in words)
            x, y = int(min(xs)), int(min(ys))
            wd, ht = int(x2 - x), int(y2 - y)
        else:
            x = y = wd = ht = 0
        out.append((int(x/scale+ox), int(y/scale+oy), wd, ht, line.text))
    return out

items = asyncio.run(ocr_file(p))
print('===== 输入框OCR =====')
for x, y, w, h, t in items:
    print(f"[{x},{y} {w}x{h}] {t}")
text = ' '.join(t for _,_,_,_,t in items)
print('包含问候语:', '红火' in text or '大家好' in text or '推荐' in text)
