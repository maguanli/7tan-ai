# -*- coding: utf-8 -*-
"""生成 360x360 头像版 + 圆形预览图 + 预览页"""
import os
from PIL import Image, ImageDraw

OUT = os.path.join("data", "logo")
names = ["candidate_1_golden_curve", "candidate_2_sunrise_peak", "candidate_3_wave_rise"]

scores = {
    "candidate_1_golden_curve": "8.5分 · 深蓝夜空 + 金色曲线 + 登顶小人",
    "candidate_2_sunrise_peak": "9分 · 暖橙日出 + 登峰举旗小人",
    "candidate_3_wave_rise": "8分 · 白底蓝浪 + 欢呼小人",
}

cards = []
for n in names:
    src = os.path.join(OUT, n + ".png")
    im = Image.open(src).convert("RGB")
    s = min(im.size)
    im2 = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2))
    im2 = im2.resize((360, 360), Image.LANCZOS)
    im2.save(os.path.join(OUT, n + "_360.png"))
    # 圆形裁剪
    mask = Image.new("L", (360, 360), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((0, 0, 360, 360), fill=255)
    circ = Image.new("RGBA", (360, 360), (255, 255, 255, 0))
    circ.paste(im2, (0, 0), mask)
    circ.save(os.path.join(OUT, n + "_circle.png"))
    cards.append(n)
    print("OK", n)

html = [
    '<!DOCTYPE html><html><head><meta charset="utf-8"><title>LOGO 候选预览</title>',
    '<style>body{background:#f5f5f5;font-family:Microsoft YaHei;text-align:center;padding:40px}'
    'h1{color:#333}.card{display:inline-block;background:#fff;border-radius:16px;padding:30px 36px;margin:16px;'
    'box-shadow:0 4px 16px rgba(0,0,0,.08);vertical-align:top}'
    '.card img{width:200px;height:200px;border-radius:50%;box-shadow:0 4px 12px rgba(0,0,0,.2)}'
    '.name{font-size:18px;font-weight:bold;margin-top:16px}.score{color:#b8860b;font-size:14px;margin-top:6px}'
    '.tip{color:#888;margin-top:30px;font-size:14px}</style></head><body>',
    '<h1>🎨 大起大落的一生 · LOGO 候选（Seedream 5.0 Pro）</h1>',
]
for n in cards:
    html.append(
        '<div class="card"><img src="%s_circle.png"><div class="name">%s</div>'
        '<div class="score">%s</div></div>' % (n, n.split("_")[1].title() + " " + n.split("_")[2].title(), scores[n])
    )
html.append('<div class="tip">圆形为公众号头像实际效果 · 另有 360×360 高清版可直接上传</div></body></html>')
with open(os.path.join(OUT, "preview_seedream.html"), "w", encoding="utf-8") as f:
    f.write("".join(html))
print("preview OK")
