# -*- coding: utf-8 -*-
"""调试：用 region_ocr 引擎识别图片文件，输出带坐标的文字（UTF-8 输出到文件）"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import region_ocr as ro

path = sys.argv[1] if len(sys.argv) > 1 else r'D:\7tan\7tanAI\tools\ocr_work\wechat_state1.png'
out_txt = sys.argv[2] if len(sys.argv) > 2 else r'D:\7tan\7tanAI\tools\ocr_work\ocr_result.txt'

img = Image.open(path)
engine = ro.WindowsOcrEngine('zh-CN', debug=False)
# 直接调用底层，取 lines 坐标
buf = io.BytesIO()
img.save(buf, format='PNG')
data = buf.getvalue()

from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
from winrt.windows.graphics.imaging import BitmapDecoder

stream = InMemoryRandomAccessStream()
writer = DataWriter(stream)
writer.write_bytes(data)
if hasattr(writer, 'store'):
    writer.store()
else:
    writer.store_async().get()
stream.seek(0)
decoder = BitmapDecoder.create_async(stream).get()
if hasattr(decoder, 'get_software_bitmap_async'):
    bitmap = decoder.get_software_bitmap_async().get()
else:
    bitmap = decoder.get_software_bitmap()
result = engine.engine.recognize_async(bitmap).get()

lines_out = []
for line in result.lines:
    r = line.bounding_rect
    lines_out.append({'x': int(r.x), 'y': int(r.y), 'w': int(r.width), 'h': int(r.height), 'text': line.text})

with open(out_txt, 'w', encoding='utf-8') as f:
    f.write("=== LINES ===\n")
    for ln in lines_out:
        f.write(f"{ln['x']},{ln['y']},{ln['w']},{ln['h']} | {ln['text']}\n")
    f.write(f"\n=== FULL TEXT ===\n{result.text}\n")
print(f"LINES={len(lines_out)} CHARS={len(result.text)} saved={out_txt}")
