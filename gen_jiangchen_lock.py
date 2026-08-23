# -*- coding: utf-8 -*-
"""《偏差》江辰定妆图 v3 —— 用 side 基准图垫图锁脸（content 多模态数组）"""
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

STYLE = ("写实向插画，都市悬疑氛围，电影级光影，冷色调（蓝灰、深灰为主），"
         "略带颗粒质感，高细节，非二次元，非Q版，非赛博朋克")

# 三张都用同一张 side 图做参考，seed 统一 3102 保证脸稳定
tasks = [
    ("character_jiangchen_main.png", "1024x1024",
     "请严格保持参考图中这个男人的同一张脸、同一发型、同一清冷气质完全不变，"
     "只把镜头从左侧脸改为正面正对镜头。生成一张正面半身照，人物居中，"
     "深灰色连帽卫衣内搭黑色T恤，站在深夜办公室工位前，身后是虚化的写字楼格子间和发冷光的电脑屏幕，环境昏暗。"
     "表情克制、冷静、眼神坚定，左眼角下方的小痣清晰可见。冷色调主光从侧面打在脸上，突出帅气的五官。"),
    ("character_jiangchen_face.png", "1024x1024",
     "请严格保持参考图中这个男人的同一张脸、同一发型、同一清冷气质完全不变，"
     "改为面部特写，镜头推近到脸部，聚焦深邃的眼睛和微皱的眉头，突出俊朗立体的五官。"
     "神情专注、警惕、像发现了什么不对劲，瞳孔微缩，嘴角紧抿，但依然帅气。"
     "深灰色连帽卫衣领口露在画面下方，背景虚化为模糊的办公室，冷色调，光影在脸上形成明暗对比，左眼角下方小痣清晰。"),
    ("character_jiangchen_full.png", "720x1280",
     "请严格保持参考图中这个男人的同一张脸、同一发型、同一清冷气质完全不变，"
     "改为全身竖屏构图，他站在空无一人的深夜办公室过道中央，两边是整齐的工位和亮着的显示器，头顶日光灯发出冷白微暗的光。"
     "深灰色连帽卫衣、黑色修身长裤、白色简约运动鞋，双手插在卫衣口袋，身姿挺拔，站姿带一丝紧绷的警惕。"
     "地面轻微反光，压抑孤独的都市悬疑氛围，左眼角下方小痣清晰。"),
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
