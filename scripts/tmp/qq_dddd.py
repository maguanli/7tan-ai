import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ddddocr

ocr = ddddocr.DdddOcr(show_ad=False)
with open(r'D:\7tan\7tanAI\qq_win.png', 'rb') as f:
    img = f.read()
res = ocr.classification(img)
print('DDDDOCR:', res)
