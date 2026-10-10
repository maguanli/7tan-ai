# -*- coding: utf-8 -*-
r"""按年份直接渲染截图（不再裁旧长图）
Playwright 打开 HTML -> 取每个 .yr 与下一个 .yr 之间区域 -> clip 截图(full_page)
输出 D:\7tan\7tanAI\7723\img\y{year}.png
"""
import os, io, sys
from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
SRC = r'D:\7tan\7tanAI\7723\7723大事记.html'
OUTDIR = r'D:\7tan\7tanAI\7723\img'
os.makedirs(OUTDIR, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge')
    pg = b.new_page(viewport={'width': 1000, 'height': 1000}, device_scale_factor=2)
    pg.goto('file:///' + SRC.replace('\\', '/'))
    pg.wait_for_timeout(700)
    info = pg.evaluate("""() => {
        const yrs = [...document.querySelectorAll('.yr')];
        const tl = document.querySelector('.timeline').getBoundingClientRect();
        const tlBottom = tl.bottom + window.scrollY;
        const arr = yrs.map(el => {
            const r = el.getBoundingClientRect();
            return {year: el.textContent.trim(), top: r.top + window.scrollY};
        });
        const out = [];
        for (let i = 0; i < arr.length; i++) {
            const top = arr[i].top;
            const bot = (i + 1 < arr.length) ? arr[i + 1].top : tlBottom;
            out.push({year: arr[i].year, top: top, bot: bot});
        }
        return out;
    }""")
    print('年份区域:', [(x['year'], round(x['top']), round(x['bot'])) for x in info])
    for x in info:
        y = max(0, x['top'] - 14)
        h = (x['bot'] - x['top']) + 14
        out = os.path.join(OUTDIR, 'y%s.png' % x['year'])
        pg.screenshot(path=out, full_page=True,
                      clip={'x': 30, 'y': y, 'width': 940, 'height': h})
        print('保存 %s  %dx%d  %.2fMB' % (out, 940 * 2, int(h * 2), os.path.getsize(out) / 1048576))
    b.close()
print('done')
