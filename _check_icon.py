# -*- coding: utf-8 -*-
"""检查图标文件与屏幕实际显示"""
import hashlib, os, sys
from PIL import Image, ImageGrab

def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()[:12]

print('=== 1. 文件对比 ===')
files = {
    'sidebar_icon(实际用)': r'D:\7tan\7tanAI\data\logo\sidebar_icon.png',
    'icon_d(用户指定)':     r'D:\7tan\7tanAI\designs\sidebar_icons\icon_d.png',
    'icon_d_v2(机器人)':    r'D:\7tan\7tanAI\designs\sidebar_icons\icon_d_v2.png',
}
for name, p in files.items():
    if os.path.exists(p):
        im = Image.open(p)
        md = md5(p)
        a = im.split()[-1] if im.mode in ('RGBA', 'LA') else None
        bbox = a.getbbox() if a else im.getbbox()
        print(f'{name}: {os.path.basename(p)} SIZE={im.size} MODE={im.mode} MD5={md} alpha_bbox={bbox} bytes={os.path.getsize(p)}')
    else:
        print(f'{name}: NOT FOUND ({p})')

print()
print('=== 2. 屏幕左上侧边栏实际显示 ===')
try:
    shot = ImageGrab.grab(bbox=(0, 0, 300, 260))
    shot.save(r'D:\7tan\7tanAI\_sidebar_now.png')
    # 统计图标区域（顶部 0-80px）颜色
    region = shot.crop((0, 0, 300, 90))
    colors = region.convert('RGB').getcolors(300*90)
    colors.sort(reverse=True)
    print('top colors (region 0,0,300,90):')
    for cnt, col in colors[:10]:
        print(f'  {col} x{cnt}')
except Exception as e:
    print('screenshot error:', e)
