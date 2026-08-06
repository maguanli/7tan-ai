# -*- coding: utf-8 -*-
"""查看 winrt OcrLine / OcrWord 可用属性"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import region_ocr as ro
from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
from winrt.windows.graphics.imaging import BitmapDecoder

img = Image.open(r'D:\7tan\7tanAI\tools\ocr_work\wechat_state1.png')
engine = ro.WindowsOcrEngine('zh-CN')
buf = io.BytesIO(); img.save(buf, format='PNG'); data = buf.getvalue()
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

print("OCR OK, text len =", len(result.text))
print("lines =", len(result.lines))
if result.lines:
    line0 = result.lines[0]
    print("line0 attrs:", [a for a in dir(line0) if not a.startswith('_')])
    print("line0 text:", repr(line0.text[:60]))
    if line0.words:
        w0 = line0.words[0]
        print("word0 attrs:", [a for a in dir(w0) if not a.startswith('_')])
        print("word0 text:", repr(w0.text))
        print("word0 rect:", w0.bounding_rect)
