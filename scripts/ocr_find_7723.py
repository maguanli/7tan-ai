# -*- coding: utf-8 -*-
"""截屏并用 winsdk OCR 识别所有文字+坐标，找 7723 群位置"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import mss, asyncio, io, tempfile, os
from PIL import Image

# 1. 截屏
with mss.mss() as sct:
    monitor = sct.monitors[0]
    img = sct.grab(monitor)
    pil = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
    pil.save(r"scripts\screen_now.png")
print(f"截图完成: scripts/screen_now.png {pil.size}")

# 2. OCR 识别坐标
async def main():
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage import StorageFile

    path = r"scripts\screen_now.png"
    scale = 1
    img = Image.open(path).convert('RGB')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    fd, tmp = tempfile.mkstemp(suffix='.png')
    with os.fdopen(fd, 'wb') as f:
        f.write(buf.getvalue())
    sf = await StorageFile.get_file_from_path_async(tmp)
    stream = await sf.open_async(0)
    dec = await BitmapDecoder.create_async(stream)
    bitmap = await dec.get_software_bitmap_async()
    lang = Language('zh-Hans-CN')
    engine = OcrEngine.try_create_from_language(lang)
    result = await engine.recognize_async(bitmap)
    os.remove(tmp)

    lines_out = []
    for i, line in enumerate(result.lines):
        words = line.words
        xs, ys = [], []
        for w in words:
            try:
                r = w.bounding_rect
                xs.append(r.x); ys.append(r.y)
            except Exception:
                pass
        if xs:
            x = int(min(xs)); y = int(min(ys))
            x2 = int(max(r.x + r.width for r in [w.bounding_rect for w in words]))
            y2 = int(max(r.y + r.height for r in [w.bounding_rect for w in words]))
            txt = line.text
            lines_out.append((x, y, x2, y2, txt))
            print(f"({x:4d},{y:4d})-({x2:4d},{y2:4d}) {txt}")
        else:
            lines_out.append((0, 0, 0, 0, line.text))
            print(f"NOXY: {line.text}")
    print(f"TOTAL={len(lines_out)}")

    # 找 7723
    for x, y, x2, y2, txt in lines_out:
        if '7723' in txt or '手机游戏' in txt or '超级群' in txt:
            print(f"\n>>> 目标: ({x},{y})-({x2},{y2}) text={txt}")

asyncio.run(main())
