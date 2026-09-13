# -*- coding: utf-8 -*-
"""扫描新弹层绿色按钮位置"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

def main():
    img = Image.open('data/screenshots/after_green_confirm.png').convert('RGB')
    green = []
    for y in range(300, 850):
        for x in range(400, 1300):
            r, g, b = img.getpixel((x, y))
            if g > 120 and g - r > 60 and g - b > 30 and b < 180:
                green.append((x, y))
    print('green pixels:', len(green))
    if green:
        xs = [p[0] for p in green]
        ys = [p[1] for p in green]
        print('green bbox: x[%d..%d] y[%d..%d]' % (min(xs), max(xs), min(ys), max(ys)))
        rows = {}
        for x, y in green:
            rows.setdefault(y // 5 * 5, []).append(x)
        for ky in sorted(rows):
            xs2 = rows[ky]
            if len(xs2) > 20:
                print('yband %d: n=%d x[%d..%d]' % (ky, len(xs2), min(xs2), max(xs2)))
    # 找"取消"按钮位置（深色文字）
    print('--- 找取消/确定文字 ---')
    import asyncio
    import winrt.windows.media.ocr as ocr
    import winrt.windows.globalization as gl
    import winrt.windows.graphics.imaging as gimg
    import winrt.windows.storage.streams as streams
    from PIL import ImageOps, ImageEnhance

    async def ocr_words(img_path):
        engine = ocr.OcrEngine.try_create_from_language(gl.Language('zh-Hans-CN'))
        with open(img_path, 'rb') as f:
            data = f.read()
        stream = streams.InMemoryRandomAccessStream()
        writer = streams.DataWriter(stream)
        writer.write_bytes(data)
        writer.store_async().get()
        stream.seek(0)
        decoder = await gimg.BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()
        result = await engine.recognize_async(bitmap)
        out = []
        for line in result.lines:
            for w in line.words:
                r = w.bounding_rect
                out.append((w.text, int(r.x), int(r.y)))
        return out

    crop = img.crop((400, 560, 900, 700))
    g = ImageOps.grayscale(crop)
    inv = ImageOps.invert(g)
    inv = ImageEnhance.Contrast(inv).enhance(2.0)
    inv = inv.resize((inv.width * 3, inv.height * 3), Image.LANCZOS)
    inv.save('data/screenshots/final_dialog_buttons.png')
    words = asyncio.run(ocr_words('data/screenshots/final_dialog_buttons.png'))
    print('=====WORDS(offset 400,560, scale 3)=====')
    for text, x, y in words:
        print(f'{text!r} @ ({400+x//3},{560+y//3})')

if __name__ == '__main__':
    main()
