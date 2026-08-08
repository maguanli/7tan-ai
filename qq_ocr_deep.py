# -*- coding: utf-8 -*-
"""3倍放大识别QQ窗口 + cnocr 辅助识别，全面读取登录界面内容"""
import asyncio, sys, io, os, tempfile, time
import win32gui, win32con
from PIL import ImageGrab, Image

QQ_HWND = 131828
rect = (800, 290, 1120, 750)
x0, y0, x1, y1 = rect

# 1) winsdk 3x 识别
async def ocr_winsdk():
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage import StorageFile
    scale = 3
    img = ImageGrab.grab(bbox=rect)
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
        out.append(f"{line.text}\t{x0l+x0:.0f}\t{y0l+y0:.0f}\t{x1l-x0l:.0f}\t{y1l-y0l:.0f}")
    with open(r'D:\7tan\7tanAI\qq_win_3x.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print('winsdk3x lines:', len(out))

asyncio.run(ocr_winsdk())

# 2) cnocr 识别（保存全窗口截图）
try:
    import cnocr
    from cnocr import CnOcr
    img = ImageGrab.grab(bbox=rect)
    img.save(r'D:\7tan\7tanAI\qq_win.png')
    ocr = CnOcr()
    res = ocr.ocr(r'D:\7tan\7tanAI\qq_win.png')
    out = []
    for item in res:
        pos = item.get('position')
        text = item.get('text')
        if pos and len(pos) == 4:
            cx = (pos[0][0] + pos[2][0]) / 2 + x0
            cy = (pos[0][1] + pos[2][1]) / 2 + y0
            out.append(f'{text}\t{cx:.0f}\t{cy:.0f}')
        else:
            out.append(f'{text}\t-\t-')
    with open(r'D:\7tan\7tanAI\qq_win_cnocr.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print('cnocr lines:', len(res))
except Exception as e:
    print('cnocr err:', e)

print('DONE')
