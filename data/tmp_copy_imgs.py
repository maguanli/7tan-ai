# -*- coding: utf-8 -*-
import os, shutil

srcs = [
    "downloads/article_taifeng/img/typhoon_1.jpg",
    "downloads/article_taifeng/img/typhoon_wuxi_storm.jpg",
    "downloads/article_taifeng/img/airport_2.jpg",
    "downloads/article_taifeng/img/hotel_a.jpg",
    "downloads/article_taifeng/img/phone_1.jpg",
    "downloads/article_taifeng/img/hotel_c.jpg",
]
dst = "data/gzh_render/台风酒店退款/img"
os.makedirs(dst, exist_ok=True)
for s in srcs:
    if os.path.exists(s):
        shutil.copy(s, os.path.join(dst, os.path.basename(s)))
        print("COPIED", s)
    else:
        print("MISSING", s)
print("DONE")
