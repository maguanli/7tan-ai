# -*- coding: utf-8 -*-
"""《偏差》v3 修复：老周 main/full 右耳垂痣丢失，强化提示词重生成"""
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

DZ = r"D:\7tan\7tanAI\镜像同事_小说\定妆图"

STYLE = ("写实向插画，都市悬疑氛围，电影级光影，冷色调（蓝灰、深灰为主），"
         "略带颗粒质感，高细节，非二次元，非Q版，非赛博朋克，中国都市职场，东亚中国面孔")

with open(os.path.join(DZ, "character_laozhou_side.png"), "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
REF_URL = "data:image/png;base64," + b64

FACE = ("请严格保持参考图中这个中年男人的同一张脸、同一发型、同一温和气质完全不变，"
        "深灰色polo衫、卡其色长裤。"
        "★关键：他的右耳垂上有一颗非常明显的深褐色小痣，必须清晰画出，"
        "耳朵区域特写级清晰，这颗痣是人物标志（注意是人物自己的右耳，绝不是左耳）。")

tasks = [
    (os.path.join(DZ, "character_laozhou_main.png"), "1024x1024",
     FACE + "正面半身像，他坐在办公工位前，双手交叠放在桌上，神情温和、微微带笑，眼袋明显，"
     "右耳和右耳垂完整露出、无头发遮挡，冷色调光线从窗户方向照入，面部与耳朵细节清晰。"),
    (os.path.join(DZ, "character_laozhou_full.png"), "720x1280",
     FACE + "全身竖屏构图，他站在办公室茶水间门口，手里端着一杯咖啡，微微弓着背，体态略显疲惫，"
     "侧身角度让右耳和右耳垂完整露出、无头发遮挡，灯光冷白色。"),
]

def gen(out_path, size, text):
    payload = {
        "model": MODEL,
        "prompt": text + "。" + STYLE,
        "content": [{"type": "image_url", "image_url": {"url": REF_URL}},
                    {"type": "text", "text": text}],
        "size": size, "seed": 3102, "watermark": False,
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
    with open(out_path, "wb") as f:
        f.write(raw)
    return time.time() - t0

if __name__ == "__main__":
    ok = 0
    for i, (out_path, size, text) in enumerate(tasks, 1):
        print("[%d/%d] %s ..." % (i, len(tasks), os.path.basename(out_path)), flush=True)
        try:
            t = gen(out_path, size, text)
            kb = os.path.getsize(out_path) // 1024
            print("  OK %.0fs %dKB" % (t, kb), flush=True)
            ok += 1
        except urllib.error.HTTPError as e:
            print("  FAIL HTTP %d: %s" % (e.code, e.read().decode("utf-8", "ignore")[:300]), flush=True)
        except Exception as e:
            print("  FAIL %s: %s" % (type(e).__name__, str(e)[:200]), flush=True)
        time.sleep(1)
    print("done %d/%d" % (ok, len(tasks)))
