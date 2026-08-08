import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import ImageGrab
from cnocr import CnOcr

rect = (480, 200, 1540, 840)
img = ImageGrab.grab(bbox=rect)
img.save(r'D:\7tan\7tanAI\qq_win.png')

ocr = CnOcr()
res = ocr.ocr(r'D:\7tan\7tanAI\qq_win.png')
with open(r'D:\7tan\7tanAI\qq_ocr.txt', 'w', encoding='utf-8') as f:
    for item in res:
        pos = item.get('position')
        text = item.get('text')
        if pos and len(pos) == 4:
            cx = (pos[0][0] + pos[2][0]) / 2 + rect[0]
            cy = (pos[0][1] + pos[2][1]) / 2 + rect[1]
            f.write(f'{text}\t{cx:.0f}\t{cy:.0f}\n')
        else:
            f.write(f'{text}\t-\t-\n')
print('DONE', len(res))
