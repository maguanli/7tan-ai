# -*- coding: utf-8 -*-
"""高分辨率OCR微信窗口 + 保存截图"""
import sys, asyncio, io
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import mss
from PIL import Image

def grab_region(x, y, w, h, scale=1.0):
    with mss.mss() as sct:
        monitor = {"left": int(x), "top": int(y), "width": int(w), "height": int(h)}
        shot = sct.grab(monitor)
    img = Image.frombytes("RGB", shot.size, shot.rgb)
    if scale and scale != 1.0:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
    return img

async def ocr_async(pil_img):
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
        return "[OCR FAIL]"
    result = await engine.recognize_async(bitmap)
    return result.text

def main():
    args = sys.argv[1:]
    x, y, w, h = (int(v) for v in args[0].split(',')) if args else (50, 100, 766, 514)
    out_png = args[1] if len(args) > 1 else 'data/screenshots/wechat_win.png'
    img = grab_region(x, y, w, h, scale=1.0)
    img.save(out_png)
    print(f"截图已保存: {out_png} ({img.width}x{img.height})")
    text = asyncio.run(ocr_async(img))
    print("===== OCR 结果 =====")
    print(text)
    print("===== END =====")

if __name__ == '__main__':
    main()
