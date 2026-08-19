# -*- coding: utf-8 -*-
"""验证 wechat_sent2.png：聊天区底部是否出现新消息"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image
import statistics

SCREENSHOT_DIR = r"D:\7tan\7tanAI\data\screenshots"
img = Image.open(SCREENSHOT_DIR + r"\wechat_sent2.png").convert('RGB')
w, h = img.size
print('sent2 尺寸:', w, h)

# 聊天区中下部 (x 380-1460, y 500-1000) 像素分析
crop = img.crop((380, 500, 1460, 1000))
g = crop.convert('L')
vals = list(g.getdata())
print('聊天区下部 灰度均值=%.1f 标准差=%.1f' % (statistics.mean(vals), statistics.pstdev(vals)))

# 放大OCR聊天区下部
crop2 = crop.resize((crop.width*2, crop.height*2), Image.LANCZOS)
p = SCREENSHOT_DIR + r"\wechat_sent2_bottom.png"
crop2.save(p)

from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.globalization import Language
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage import StorageFile

async def ocr_file(path, scale=2.0, ox=380, oy=500):
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
print('===== 聊天区下部 OCR =====')
for x, y, w, h, t in items:
    print(f"[{x},{y} {w}x{h}] {t}")
text = ' '.join(t for _,_,_,_,t in items)
print('----')
print('找到问候内容:', '红火' in text or '玩得开心' in text or '大家好' in text)
