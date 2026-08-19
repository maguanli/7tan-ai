# -*- coding: utf-8 -*-
"""全屏截图 + winsdk OCR，输出 文本\tx\ty\tw\th 到文件"""
import asyncio, sys, io, os, tempfile
from PIL import ImageGrab, Image

async def main():
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage import StorageFile
    scale = 1.5
    img = ImageGrab.grab()  # 全屏
    w, h = img.size
    img2 = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img2.save(buf, format='PNG')
    fd, tmp = tempfile.mkstemp(suffix='.png')
    with os.fdopen(fd, 'wb') as f:
        f.write(buf.getvalue())
    sf = await StorageFile.get_file_from_path_async(tmp)
    stream = await sf.open_async(0)
    dec = await BitmapDecoder.create_async(stream)
    bitmap = await dec.get_software_bitmap_async()
    engine = OcrEngine.try_create_from_language(Language('zh-Hans-CN'))
    result = await engine.recognize_async(bitmap)
    os.remove(tmp)
    out = []
    for line in result.lines:
        xs = [wd.bounding_rect.x / scale for wd in line.words]
        ys = [wd.bounding_rect.y / scale for wd in line.words]
        ws = [wd.bounding_rect.width / scale for wd in line.words]
        hs = [wd.bounding_rect.height / scale for wd in line.words]
        if not xs:
            continue
        x0 = min(xs); y0 = min(ys)
        x1 = max(x + w for x, w in zip(xs, ws))
        y1 = max(y + h for y, h in zip(ys, hs))
        out.append(f"{line.text}\t{x0:.0f}\t{y0:.0f}\t{x1-x0:.0f}\t{y1-y0:.0f}")
    with open(r'D:\7tan\7tanAI\qq_login_ocr.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print('DONE lines=%d screen=%dx%d' % (len(out), w, h))

asyncio.run(main())
