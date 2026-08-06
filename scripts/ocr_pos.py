# -*- coding: utf-8 -*-
"""OCR 并输出每行文字坐标（用 OcrWord.bounding_rect 定位）"""
import sys, asyncio, io
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import mss
from PIL import Image

def grab_region(x, y, w, h):
    with mss.mss() as sct:
        monitor = {"left": int(x), "top": int(y), "width": int(w), "height": int(h)}
        shot = sct.grab(monitor)
    return Image.frombytes("RGB", shot.size, shot.rgb)

async def ocr_lines_async(pil_img, offset_x=0, offset_y=0):
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    data = buf.getvalue()
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(data)
    await writer.store_async()
    stream.seek(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        engine = OcrEngine.try_create_from_language(Language("zh-CN"))
    if engine is None:
        print("[OCR FAIL]")
        return []
    result = await engine.recognize_async(bitmap)
    lines = []
    for line in result.lines:
        # 合并 words 的边界框
        xs, ys, xe, ye = [], [], [], []
        for w in line.words:
            r = w.bounding_rect
            xs.append(r.x); ys.append(r.y)
            xe.append(r.x + r.width); ye.append(r.y + r.height)
        if xs:
            lx, ly = int(min(xs) + offset_x), int(min(ys) + offset_y)
            lw, lh = int(max(xe) - min(xs)), int(max(ye) - min(ys))
            lines.append((line.text, lx, ly, lw, lh))
    return lines

def main():
    args = sys.argv[1:]
    x, y, w, h = (int(v) for v in args[0].split(',')) if args else (50, 100, 766, 514)
    img = grab_region(x, y, w, h)
    lines = asyncio.run(ocr_lines_async(img, offset_x=x, offset_y=y))
    for text, lx, ly, lw, lh in lines:
        print(f'[{lx},{ly} {lw}x{lh}] {text}')
    print('===== END =====')

if __name__ == '__main__':
    main()
