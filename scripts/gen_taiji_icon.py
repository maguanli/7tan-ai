# -*- coding: utf-8 -*-
"""生成阴阳鱼太极图 APP 图标（含 round 版本），覆盖所有 mipmap 尺寸"""
import os
from PIL import Image, ImageDraw

BASE = r'D:\7tan\iching-android\app\src\main\res'
SIZES = {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144, 'xxxhdpi': 192}

# 配色（与项目 vector 图标一致）
BG      = (43, 33, 24, 255)      # #2B2118 深棕背景
CREAM   = (247, 241, 227, 255)   # #F7F1E3 米白（阳鱼）
INK     = (23, 18, 11, 255)      # 更深的墨黑（阴鱼）
GOLD    = (201, 162, 39, 255)    # #C9A227 金色（鱼眼/描环）


def draw_taiji_icon(size, rounded=True, ring=True):
    """绘制太极图标。rounded=True 圆角方形（普通图标），False 纯圆（round 图标）"""
    SS = 1024  # 超采样基准
    img = Image.new('RGBA', (SS, SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ---- 背景 ----
    margin = SS * 0.06
    if rounded:
        d.rounded_rectangle([margin, margin, SS - margin, SS - margin],
                            radius=SS * 0.22, fill=BG)
    else:
        d.ellipse([margin, margin, SS - margin, SS - margin], fill=BG)

    # ---- 太极图 ----
    cx = cy = SS / 2
    R = SS * 0.38          # 太极大圆半径
    r2 = R / 2             # 小半圆半径
    eye = R * 0.13         # 鱼眼半径

    # 1. 大圆（全黑底）
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=INK)
    # 2. 左半圆涂白（pieslice 90°~270° 是左半）
    d.pieslice([cx - R, cy - R, cx + R, cy + R], 90, 270, fill=CREAM)
    # 3. 顶部小白圆盘（白鱼头，右凸）
    d.ellipse([cx - r2, cy - R, cx + r2, cy], fill=CREAM)
    # 4. 底部小黑圆盘（黑鱼头，左凸）
    d.ellipse([cx - r2, cy, cx + r2, cy + R], fill=INK)
    # 5. 鱼眼：白鱼黑眼（上）、黑鱼白眼（下）
    d.ellipse([cx - eye, cy - r2 - eye, cx + eye, cy - r2 + eye], fill=INK)
    d.ellipse([cx - eye, cy + r2 - eye, cx + eye, cy + r2 + eye], fill=CREAM)

    # 6. 金色描环（太极图外圈）
    if ring:
        d.ellipse([cx - R - SS * 0.012, cy - R - SS * 0.012,
                   cx + R + SS * 0.012, cy + R + SS * 0.012],
                  outline=GOLD, width=int(SS * 0.012))

    # ---- 缩放到目标尺寸 ----
    return img.resize((size, size), Image.LANCZOS)


def main():
    for dpi, size in SIZES.items():
        for name in ('ic_launcher.png', 'ic_launcher_round.png'):
            icon = draw_taiji_icon(size, rounded=(name == 'ic_launcher.png'))
            out = os.path.join(BASE, f'mipmap-{dpi}', name)
            icon.save(out, 'PNG')
            print('OK', out, icon.size)


if __name__ == '__main__':
    main()
