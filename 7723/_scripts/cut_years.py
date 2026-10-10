# -*- coding: utf-8 -*-
"""把《7723(7坛) 大事记》长图按年份精准裁切
思路：Playwright 打开 HTML，读出每个「年份徽章(.yr)」的绝对 Y 坐标，
     乘以 device_scale_factor(=2) 得到 PNG 像素坐标，再用 PIL 裁剪。
输出：D:\7tan\7tanAI\7723\img\year_2009.png ... year_2015.png
"""
import os, io, sys
from PIL import Image
from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SRC_HTML = r'D:\7tan\7tanAI\7723\7723大事记.html'
SRC_PNG = r'D:\7tan\7tanAI\7723\7723大事记.png'
OUTDIR = r'D:\7tan\7tanAI\7723\img'
SCALE = 2
os.makedirs(OUTDIR, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge')
    pg = b.new_page(viewport={'width': 1000, 'height': 900}, device_scale_factor=SCALE)
    pg.goto('file:///' + SRC_HTML.replace('\\', '/'))
    pg.wait_for_timeout(600)
    info = pg.evaluate("""() => {
        const out = [];
        document.querySelectorAll('.yr').forEach(el => {
            const r = el.getBoundingClientRect();
            out.push({year: el.textContent.trim(), top: r.top + window.scrollY});
        });
        const tl = document.querySelector('.timeline').getBoundingClientRect();
        return {years: out, tlTop: tl.top + window.scrollY, tlBottom: tl.bottom + window.scrollY,
                bodyH: document.body.scrollHeight};
    }""")
    b.close()

print('页面 CSS 高度:', info['bodyH'], '| PNG 高度:', Image.open(SRC_PNG).size[1])
print('timeline:', round(info['tlTop'], 1), '->', round(info['tlBottom'], 1))
for y in info['years']:
    print('  %s  top=%.1f css  -> px %.0f' % (y['year'], y['top'], y['top'] * SCALE))

im = Image.open(SRC_PNG)
W, H = im.size
ys = info['years']
# 边界：该年徽章顶部 到 下一年徽章顶部
for i, y in enumerate(ys):
    top_css = y['top']
    if i + 1 < len(ys):
        bot_css = ys[i + 1]['top']
    else:
        bot_css = info['tlBottom']
    top_px = max(0, int(top_css * SCALE) - 12)      # 往上留一点
    bot_px = min(H, int(bot_css * SCALE) - 12)
    crop = im.crop((0, top_px, W, bot_px))
    out = os.path.join(OUTDIR, 'year_%s.png' % y['year'])
    crop.save(out)
    print('保存 %s  %dx%d  %.2f MB' % (out, crop.size[0], crop.size[1],
                                      os.path.getsize(out) / 1024 / 1024))
print('完成')
