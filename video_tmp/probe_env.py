# -*- coding: utf-8 -*-
"""探测环境：图片尺寸 / 字体 / PIL / 输出分辨率建议"""
import os, json, glob
from PIL import Image

result = {}
img_dir = r"D:\7tan\7tanAI\镜像同事_小说\images\第3章"
files = sorted(glob.glob(os.path.join(img_dir, "*.png")))
result["count"] = len(files)
sizes = set()
for f in files:
    try:
        with Image.open(f) as im:
            sizes.add(im.size)
    except Exception as e:
        result["error_" + os.path.basename(f)] = str(e)
result["sizes"] = sorted(sizes)

# 字体检查
fonts = [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc",
         r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\simsun.ttc"]
result["fonts"] = {f: os.path.exists(f) for f in fonts}

with open(r"D:\7tan\7tanAI\video_tmp\probe_result.json", "w", encoding="utf-8") as fp:
    json.dump(result, fp, ensure_ascii=False, indent=2)
print("DONE")
