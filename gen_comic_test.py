# -*- coding: utf-8 -*-
"""《偏差》漫画风测试：用 side 基准图垫图，改漫画风格重绘江辰正面"""
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

# ★漫画风统一段（与《全球只有我是NPC》一致的日式动漫漫画风格）
STYLE = ("日式动漫漫画插画风格（2D动漫），清晰干净的轮廓线条，赛璐璐上色，"
         "画面精致有质感，都市悬疑氛围，冷色调（蓝灰、深灰为主），"
         "人物五官动漫化但保留辨识度，高完成度，"
         "禁止：写实照片、真人3D、欧美漫画、像素风、厚涂写实")

TEXT = ("请保持参考图中这个男人的同一张脸、同一发型、同一气质不变，"
        "用日式动漫漫画风格重新绘制为正面半身像，人物居中。"
        "27岁中国男性，黑色短发，深灰色连帽卫衣，站在深夜办公室工位前，"
        "身后是虚化的写字楼格子间和发冷光的电脑屏幕。"
        "表情克制、冷静、眼神坚定帅气，左眼角下方一颗小痣清晰可见。"
        "冷色调光影，漫画质感，五官精致。")

def gen():
    payload = {
        "model": MODEL,
        "prompt": TEXT + "。" + STYLE,
        "content": [
            {"type": "image_url", "image_url": {"url": REF_URL}},
            {"type": "text", "text": TEXT + "。" + STYLE}
        ],
        "size": "1024x1024", "seed": 8888, "watermark": False,
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
    out_path = os.path.join(OUT, "character_jiangchen_comic_test.png")
    with open(out_path, "wb") as f:
        f.write(raw)
    return time.time() - t0, os.path.getsize(out_path) // 1024

if __name__ == "__main__":
    try:
        t, kb = gen()
        print("OK %.0fs %dKB -> character_jiangchen_comic_test.png" % (t, kb), flush=True)
    except urllib.error.HTTPError as e:
        print("FAIL HTTP %d: %s" % (e.code, e.read().decode("utf-8", "ignore")[:400]), flush=True)
    except Exception as e:
        print("FAIL %s: %s" % (type(e).__name__, str(e)[:300]), flush=True)
