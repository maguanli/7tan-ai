# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
import os
print('PIL OK')
for p in [r'C:\Windows\Fonts\msyh.ttc',
          r'C:\Windows\Fonts\msyhbd.ttc',
          r'C:\Windows\Fonts\simhei.ttf',
          r'C:\Windows\Fonts\simsun.ttc',
          r'C:\Windows\Fonts\Deng.ttf',
          r'C:\Windows\Fonts\Dengb.ttf']:
    print(p, os.path.exists(p))
img = Image.open(r'D:\用户目录\下载\新建文件夹 123\ch03_08.png')
print('img size:', img.size, img.mode)
