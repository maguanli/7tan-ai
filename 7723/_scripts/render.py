# -*- coding: utf-8 -*-
"""把 HTML 长图用 Playwright(系统 Edge) 渲染成整张 PNG
用法: python render.py  (先运行 build.py 生成 HTML)"""
import os
from playwright.sync_api import sync_playwright

SRC = r'D:\7tan\7tanAI\7723\7723大事记.html'
DST = r'D:\7tan\7tanAI\7723\7723大事记.png'

with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge')          # 本机未装 playwright 浏览器时走系统 Edge
    pg = b.new_page(viewport={'width': 1000, 'height': 900}, device_scale_factor=2)
    pg.goto('file:///' + SRC.replace('\\', '/'))
    pg.wait_for_timeout(800)
    print('page size', pg.evaluate("document.body.scrollWidth"),
          'x', pg.evaluate("document.body.scrollHeight"))
    pg.screenshot(path=DST, full_page=True)
    b.close()
print('saved', DST, os.path.getsize(DST))
