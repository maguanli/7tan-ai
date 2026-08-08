# -*- coding: utf-8 -*-
"""OCR with word bounding boxes — 找目标文字在屏幕上的坐标"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import io

sys.path.insert(0, r'tools\gzh_publish')
from region_ocr import grab_region, WindowsOcrEngine

def get_words_with_pos(img, engine):
    """识别图片，返回 [(text, (x,y,w,h))] 坐标为图片内坐标"""
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
    # 左侧群列表区域
    ox, oy, ow, oh = 480, 200, 320, 640
    img = grab_region(ox, oy, ow, oh, scale=1.0)
    words = get_words_with_pos(img, engine)

    print('=== 左侧区域识别词及屏幕坐标 ===')
    for text, (x, y, w, h) in words:
        sx, sy = int(ox + x), int(oy + y)
        print(f'[{sx},{sy} {int(w)}x{int(h)}] {text}')

    # 组合成行，找目标
    lines = {}
    for text, (x, y, w, h) in words:
        key = round(y / 12)
        lines.setdefault(key, []).append((int(x), text, int(y)))
    print('\n=== 含7723/超级群的行 ===')
    for key in sorted(lines):
        items = sorted(lines[key])
        line_text = ''.join(t for _, t, _ in items)
        if '7723' in line_text or '超级群' in line_text or '游戏' in line_text:
            y = items[0][2]
            x0 = items[0][0]
            x1 = items[-1][0]
            print(f'y={oy+y} x={ox+x0}~{ox+x1} text={line_text}')

if __name__ == '__main__':
    main()
