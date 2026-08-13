import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from PIL import ImageGrab, Image

# 密码框区域放大3倍
img = ImageGrab.grab(bbox=(1050, 495, 1350, 545))
img = img.resize((img.width * 3, img.height * 3), Image.LANCZOS)
img.save(r'D:\7tan\7tanAI\data\screenshots\pwd_zoom3x.png')
print('SAVED', img.size)
