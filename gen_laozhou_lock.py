# -*- coding: utf-8 -*-
"""《偏差》老周定妆图 v2 —— 用 main 基准图垫图锁脸（content 多模态数组）"""
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
REF = os.path.join(OUT, "character_laozhou_main.png")
with open(REF, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
REF_URL = "data:image/png;base64," + b64

STYLE = ("写实向插画，都市悬疑氛围，电影级光影，冷色调（蓝灰、深灰为主），"
         "略带颗粒质感，高细节，非二次元，非Q版，非赛博朋克")

# 三张都用同一张 main 图做参考，seed 统一 3102 保证脸稳定
tasks = [
    ("character_laozhou_side.png", "1024x1024",
     "请严格保持参考图中这个中年男人的同一张脸、同一发型、同一温和气质完全不变，"
     "只把镜头从正面改为右侧脸45度侧面，清晰露出右耳垂上一颗明显的小痣。"
     "他坐在办公工位前，转头看向旁边的同事，脸上带着温和的笑容，眼袋明显。"
     "深灰色polo衫、卡其色长裤。身后是模糊的办公室环境，冷色调光线从窗户方向照入，面部细节清晰。"),
    ("character_laozhou_face.png", "1024x1024",
     "请严格保持参考图中这个中年男人的同一张脸、同一发型、同一温和气质完全不变，"
     "改为面部特写，镜头推近到脸部，聚焦在温和却难掩疲惫的笑容上，眼袋沉重，眼角皱纹明显，"
     "眼神里带着隐忍和一丝不易察觉的麻木。深灰色polo衫领口露在画面下方，"
     "背景虚化为模糊的办公室，柔和冷调光线，右耳垂一颗小痣清晰可见。"),
    ("character_laozhou_full.png", "720x1280",
     "请严格保持参考图中这个中年男人的同一张脸、同一发型、同一温和气质完全不变，"
     "改为全身竖屏构图，他站在办公室茶水间门口，手里端着一杯咖啡，微微弓着背，体态略显疲惫。"
     "深灰色polo衫、卡其色长裤、棕色皮带、手腕一只旧手表。"
     "周围是普通的公司办公环境，灯光是冷白色，右耳垂一颗小痣清晰可见。"),
]

def gen(ref_url, text, size, out_path):
    payload = {
        "model": MODEL,
        "prompt": text + "。" + STYLE,
        "content": [
            {"type": "image_url", "image_url": {"url": ref_url}},
            {"type": "text", "text": text}
        ],
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
    for fname, size, text in tasks:
        out_path = os.path.join(OUT, fname)
        print("[gen] %s %s ..." % (fname, size), flush=True)
        try:
            t = gen(REF_URL, text, size, out_path)
            kb = os.path.getsize(out_path) // 1024
            print("  OK %.0fs %dKB" % (t, kb), flush=True)
            ok += 1
        except urllib.error.HTTPError as e:
            print("  FAIL HTTP %d: %s" % (e.code, e.read().decode("utf-8", "ignore")[:300]), flush=True)
        except Exception as e:
            print("  FAIL %s: %s" % (type(e).__name__, str(e)[:200]), flush=True)
        time.sleep(1)
    print("done %d/3" % ok)
