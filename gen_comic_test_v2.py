# -*- coding: utf-8 -*-
"""《偏差》风格测试v2：完全复刻《全球只有我是NPC》的动漫风格 STYLE"""
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
print("model=%s" % MODEL, flush=True)

OUT = r"D:\7tan\7tanAI\镜像同事_小说\定妆图"
REF = os.path.join(OUT, "character_jiangchen_side.png")
with open(REF, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
REF_URL = "data:image/png;base64," + b64

# ★《全球只有我是NPC》原版风格（从 downloads/fanqie/video/gen_frames_ch3.py 提取）
STYLE = ("高质量动漫风格插画，精致五官，双眼对称自然，细腻光影，电影感构图，竖屏构图，"
         "细节丰富，色彩明快，背景干净")

TEXT = ("请保持参考图中这个年轻中国男人的同一张脸、同一发型、同一气质不变，"
        "27岁，黑色短发，深灰色连帽卫衣，正面半身像，人物居中。"
        "深夜办公室工位前，身后是虚化的写字楼格子间和发冷光的电脑屏幕。"
        "表情克制、冷静、眼神坚定帅气，左眼角下方一颗小痣清晰可见。")

def gen():
    payload = {
        "model": MODEL,
        "prompt": TEXT + "。" + STYLE,
        "image": REF_URL,          # 图片接口标准垫图字段
        "size": "720x1280",        # NPC 原版竖屏尺寸
        "seed": 8888, "watermark": False,
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
    out_path = os.path.join(OUT, "character_jiangchen_comic_test2.png")
    with open(out_path, "wb") as f:
        f.write(raw)
    return time.time() - t0, os.path.getsize(out_path) // 1024

if __name__ == "__main__":
    try:
        t, kb = gen()
        print("OK %.0fs %dKB -> character_jiangchen_comic_test2.png" % (t, kb), flush=True)
    except urllib.error.HTTPError as e:
        print("FAIL HTTP %d: %s" % (e.code, e.read().decode("utf-8", "ignore")[:400]), flush=True)
    except Exception as e:
        print("FAIL %s: %s" % (type(e).__name__, str(e)[:300]), flush=True)
