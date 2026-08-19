# -*- coding: utf-8 -*-
"""定位 QQ 聊天输入框 — 用词坐标扫描窗口底部"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import io

sys.path.insert(0, r'tools\gzh_publish')
from region_ocr import grab_region, WindowsOcrEngine

def get_words_with_pos(img, engine):
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    data = buf.getvalue()
    stream = engine._Stream()
    writer = engine._Writer(stream)
    writer.write_bytes(data)
    if hasattr(writer, 'store'):
        writer.store()
    else:
        engine._wait(writer.store_async())
    stream.seek(0)
    decoder = engine._wait(engine._BD.create_async(stream))
    bitmap = engine._wait(decoder.get_software_bitmap_async())
    result = engine._wait(engine.engine.recognize_async(bitmap))
    words = []
    for line in result.lines:
        for w in line.words:
            r = w.bounding_rect
            words.append((w.text, (r.x, r.y, r.width, r.height)))
    return words

def main():
    engine = WindowsOcrEngine('zh-CN')
    # 扫描窗口底部 300px（输入框区域）
    ox, oy, ow, oh = 480, 540, 1060, 300
    img = grab_region(ox, oy, ow, oh, scale=1.0)
    words = get_words_with_pos(img, engine)
    print('=== 窗口底部区域词坐标 ===')
    for text, (x, y, w, h) in words:
        sx, sy = int(ox + x), int(oy + y)
        print(f'[{sx},{sy} {int(w)}x{int(h)}] {text}')

if __name__ == '__main__':
    main()
