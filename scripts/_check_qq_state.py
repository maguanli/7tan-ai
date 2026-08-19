# -*- coding: utf-8 -*-
"""等待 QQ 完全加载 + 全屏 OCR 看当前状态"""
import sys, io, asyncio, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import mss
from PIL import Image

# 等待更久
print("再等 10 秒让 QQ 加载...")
time.sleep(10)

with mss.mss() as sct:
    shot = sct.grab(sct.monitors[1])
img = Image.frombytes("RGB", shot.size, shot.rgb)
img.save(r"D:\7tan\7tanAI\data\screenshots\_qq_state.png")
print("截图已保存:", img.size)

import winsdk.windows.media.ocr as ocr
import winsdk.windows.globalization as glob
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

async def recognize(pil_img):
    import io as _io
    buf = _io.BytesIO()
    pil_img.save(buf, format="PNG")
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(buf.getvalue())
    if hasattr(writer, "store"):
        writer.store()
    else:
        await writer.store_async()
    stream.seek(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = ocr.OcrEngine.try_create_from_language(glob.Language("zh-CN"))
    result = await engine.recognize_async(bitmap)
    out = []
    for line in result.lines:
        for word in line.words:
            r = word.bounding_rect
            out.append((word.text, r.x, r.y, r.width, r.height))
    return out

async def main():
    items = await recognize(img)
    print("识别词数:", len(items))
    items.sort(key=lambda it: (it[2], it[1]))
    for t, x, y, w, h in items[:80]:
        print(f"  [{int(x)},{int(y)} {int(w)}x{int(h)}] {t!r}")

asyncio.run(main())
