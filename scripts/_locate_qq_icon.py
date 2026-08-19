# -*- coding: utf-8 -*-
"""截全屏 + OCR 定位 QQ 图标位置（用于真实鼠标双击打开 QQ）"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import winsdk.windows.media.ocr as ocr
import winsdk.windows.globalization as glob
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

import mss, io as _io
from PIL import Image

async def recognize_with_positions(pil_img):
    buf = _io.BytesIO()
    pil_img.save(buf, format="PNG")
    data = buf.getvalue()
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(data)
    if hasattr(writer, "store"):
        writer.store()
    else:
        await writer.store_async()
    stream.seek(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = ocr.OcrEngine.try_create_from_language(glob.Language("zh-CN"))
    result = await engine.recognize_async(bitmap)
    items = []
    for line in result.lines:
        for word in line.words:
            r = word.bounding_rect
            items.append((word.text, r.x, r.y, r.width, r.height))
    return items

async def main():
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[1])
    img = Image.frombytes("RGB", shot.size, shot.rgb)
    img.save(r"D:\7tan\7tanAI\data\screenshots\_desktop_now.png")
    print("截图已保存:", img.size)

    # 放大找桌面图标文字（桌面图标文字较小，用原图识别）
    items = await recognize_with_positions(img)
    print("识别词数:", len(items))

    # 找 QQ 相关
    keywords = ["QQ", "qq", "腾讯"]
    hits = []
    for t, x, y, w, h in items:
        tt = t.replace(" ", "")
        for kw in keywords:
            if kw in tt:
                hits.append((t, int(x), int(y), int(w), int(h)))
                break
    if hits:
        print("=== QQ 相关文字位置 ===")
        for t, x, y, w, h in hits:
            print(f"text={t!r} x={x} y={y} w={w} h={h} 中心=({x+w//2},{y+h//2})")
    else:
        print("未命中 QQ，输出全部文字(前60):")
        items.sort(key=lambda it: (it[2], it[1]))
        for i, (t, x, y, w, h) in enumerate(items[:60]):
            print(f"  [{int(x)},{int(y)} {int(w)}x{int(h)}] {t!r}")

asyncio.run(main())
