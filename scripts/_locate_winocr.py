# -*- coding: utf-8 -*-
"""用 Windows OCR (winsdk/winrt) 识别全屏，返回带坐标的文字"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 尝试 winsdk / winrt
try:
    import winsdk.windows.media.ocr as ocr
    import winsdk.windows.globalization as glob
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
    print("使用 winsdk")
except ImportError:
    try:
        from winrt.windows.media.ocr import OcrEngine
        from winrt.windows.globalization import Language
        from winrt.windows.graphics.imaging import BitmapDecoder
        from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
        ocr = None
        print("使用 winrt")
    except ImportError as e:
        print("winsdk/winrt 都不可用:", e)
        sys.exit(1)

import mss, io as _io
from PIL import Image

KEYWORD = "四十岁"

# 创建引擎
if ocr is not None:
    lang = glob.Language("zh-CN")
    engine = ocr.OcrEngine.try_create_from_language(lang)
else:
    lang = Language("zh-CN")
    engine = OcrEngine.try_create_from_language(lang)
if engine is None:
    print("创建 zh-CN 引擎失败，用默认")
    if ocr is not None:
        engine = ocr.OcrEngine.try_create_from_user_profile_languages()
    else:
        engine = OcrEngine.try_create_from_user_profile_languages()
if engine is None:
    print("无可用 OCR 引擎")
    sys.exit(1)
print("引擎:", engine.recognizer_language.language_tag)

def recognize_with_positions(pil_img):
    buf = _io.BytesIO()
    pil_img.save(buf, format="PNG")
    data = buf.getvalue()
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(data)
    if hasattr(writer, "store"):
        writer.store()
    else:
        writer.store_async().get()
    stream.seek(0)
    decoder = BitmapDecoder.create_async(stream).get()
    bitmap = decoder.get_software_bitmap_async().get()
    result = engine.recognize_async(bitmap).get()
    items = []
    for line in result.lines:
        for word in line.words:
            r = word.bounding_rect
            items.append((word.text, r.x, r.y, r.width, r.height))
    return items, result.text

# 全屏截图
with mss.mss() as sct:
    shot = sct.grab(sct.monitors[1])
img = Image.frombytes("RGB", shot.size, shot.rgb)
print("截图:", img.size)

# 先 50% 缩放识别（加速），坐标*2
small = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)
items, full_text = recognize_with_positions(small)
print("识别词数:", len(items))

hits = []
for t, x, y, w, h in items:
    if KEYWORD in t.replace(' ', ''):
        hits.append((t, int(x*2), int(y*2), int(w*2), int(h*2)))

if hits:
    print("=== 命中「四十岁」 ===")
    for t, x, y, w, h in hits:
        print(f"text={t!r} x={x} y={y} w={w} h={h} 中心=({x+w//2},{y+h//2})")
else:
    print("未命中，输出部分文字(前40):")
    cnt = 0
    for t, x, y, w, h in items:
        print(f"  [{int(x*2)},{int(y*2)}] {t!r}")
        cnt += 1
        if cnt >= 40:
            break
