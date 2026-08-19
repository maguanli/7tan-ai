# -*- coding: utf-8 -*-
"""验证 tesseract 可用性 + 定位「论四十岁」"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pytesseract
from PIL import Image

# 版本与语言包
try:
    print("tesseract 版本:", pytesseract.get_tesseract_version())
except Exception as e:
    print("tesseract 不可用:", e)
    sys.exit(1)

langs = pytesseract.get_languages(config='')
print("可用语言:", langs)

img = Image.open(r"D:\7tan\7tanAI\data\screenshots\_fullscreen.png")
print("图片尺寸:", img.size)

# 用 image_to_data 获取带位置的结果
data = pytesseract.image_to_data(img, lang='chi_sim+eng', output_type=pytesseract.Output.DICT)
n = len(data['text'])
hits = []
for i in range(n):
    t = (data['text'][i] or '').strip()
    if t:
        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
        if '论四十岁' in t.replace(' ', '') or ('四十岁' in t.replace(' ', '')):
            hits.append((t, x, y, w, h))

if hits:
    print("=== 命中「四十岁」 ===")
    for t, x, y, w, h in hits:
        print(f"text={t!r} x={x} y={y} w={w} h={h} 中心=({x+w//2},{y+h//2})")
else:
    print("未命中关键词，输出前30条文字:")
    cnt = 0
    for i in range(n):
        t = (data['text'][i] or '').strip()
        if t:
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            print(f"  [{x},{y}] {t!r}")
            cnt += 1
            if cnt >= 30:
                break
