# -*- coding: utf-8 -*-
"""重新生成江辰 main 正面主图（content 数组锁脸）"""
import os, sys, json, time, base64, sqlite3, urllib.request, urllib.error

sys.path.insert(0, os.getcwd())
from src.database.db import decrypt_password

DB = os.path.join("data", "games.db")
conn = sqlite3.connect(DB)
row = conn.execute(
    "SELECT api_key, base_url, model FROM ai_configs WHERE config_key='doubao-seedream-5.0-pro'"
).fetchone()
enc_key, BASE_URL, MODEL = row
API_KEY = decrypt_password(enc_key)

OUT = r"D:\7tan\7tanAI\镜像同事_小说\定妆图"
REF = os.path.join(OUT, "character_jiangchen_side.png")
with open(REF, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
REF_URL = "data:image/png;base64," + b64

STYLE = ("写实向插画，都市悬疑氛围，电影级光影，冷色调（蓝灰、深灰为主），"
         "略带颗粒质感，高细节，非二次元，非Q版，非赛博朋克")

text = ("请严格保持参考图中这个男人的同一张脸、同一发型、同一清冷帅气气质完全不变，"
        "只把镜头从左侧脸改为正面正对镜头。生成一张正面半身照，人物居中，"
        "深灰色连帽卫衣内搭黑色T恤，站在深夜办公室工位前，身后是虚化的写字楼格子间和发冷光的电脑屏幕，环境昏暗。"
        "表情克制、冷静、眼神坚定明亮有正气，左眼角下方的小痣清晰可见。冷色调主光从侧面打在脸上，突出帅气的五官。")

payload = {
    "model": MODEL,
    "prompt": text + "。" + STYLE,
    "content": [
        {"type": "image_url", "image_url": {"url": REF_URL}},
        {"type": "text", "text": text}
    ],
    "size": "1024x1024", "seed": 3102, "watermark": False,
}
body = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(BASE_URL.rstrip("/") + "/images/generations", data=body,
                             headers={"Authorization": "Bearer " + API_KEY,
                                      "Content-Type": "application/json"}, method="POST")
t0 = time.time()
with urllib.request.urlopen(req, timeout=600) as resp:
    data = json.loads(resp.read().decode("utf-8"))
item = data.get("data", [{}])[0]
img_url = item.get("url"); b64out = item.get("b64_json")
if b64out:
    raw = base64.b64decode(b64out)
elif img_url:
    r2 = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(r2, timeout=120) as resp2:
        raw = resp2.read()
else:
    raise RuntimeError("no image: " + str(data)[:300])
out_path = os.path.join(OUT, "character_jiangchen_main.png")
with open(out_path, "wb") as f:
    f.write(raw)
print("OK saved %s %.0fs %dKB" % (out_path, time.time()-t0, len(raw)//1024), flush=True)
