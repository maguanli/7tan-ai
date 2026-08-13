# -*- coding: utf-8 -*-
"""全宽分析QQ窗口底部结构 + 4x OCR 底部区域"""
import asyncio, sys, io, os, tempfile, time
import win32gui
from PIL import ImageGrab, Image

QQ_HWND = 786944
rect = win32gui.GetWindowRect(QQ_HWND)
print('rect:', rect)
x0, y0, x1, y1 = rect

# 底部区域截图
BOTTOM = (x0, y1 - 100, x1, y1)  # 窗口底部100px
img = ImageGrab.grab(bbox=BOTTOM)
img.save(r'D:\7tan\7tanAI\qq_bottom_full.png')
print('saved bottom:', BOTTOM, img.size)

# 逐行分析非白像素分布（每4px）
px = img.load()
W, H = img.size
print('--- 行扫描 (y_rel: 非白数量) ---')
for y in range(0, H, 3):
    cnt = 0
    xs = []
    for x in range(W):
        r, g, b = px[x, y][:3]
        if not (r > 235 and g > 235 and b > 235):
            cnt += 1
            if len(xs) < 5:
                xs.append(x)
    if cnt > 0:
        print(f'y={y}: n={cnt} first_x={xs}')

# 4x OCR 底部
async def ocr():
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage import StorageFile
    scale = 4
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
        x0l = min(xs); y0l = min(ys)
        x1l = max(x + w for x, w in zip(xs, ws))
        y1l = max(y + h for y, h in zip(ys, hs))
        out.append(f"{line.text}\t{x0l+BOTTOM[0]:.0f}\t{y0l+BOTTOM[1]:.0f}\t{x1l-x0l:.0f}\t{y1l-y0l:.0f}")
    with open(r'D:\7tan\7tanAI\qq_bottom_full_ocr.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print('OCR lines:', len(out))

asyncio.run(ocr())
print('DONE')
