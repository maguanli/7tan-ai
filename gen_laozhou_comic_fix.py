# -*- coding: utf-8 -*-
"""《偏差》老周漫画定妆图修正版 —— 45岁、疲惫不衰老、日式动漫漫画风（与 ch01_07_v11 同档）
纯文本生成：不垫江辰脸（防串脸）、不垫旧半写实老周（防回写实），靠 STYLE 锁画风
"""
import os, sys, json, time, base64, shutil, sqlite3, urllib.request, urllib.error

sys.path.insert(0, r"D:\7tan\7tanAI")
from src.database.db import decrypt_password

DB = r"D:\7tan\7tanAI\data\games.db"
conn = sqlite3.connect(DB)
row = conn.execute(
    "SELECT api_key, base_url, model FROM ai_configs WHERE config_key='doubao-seedream-5.0-pro'"
).fetchone()
enc_key, BASE_URL, MODEL = row
API_KEY = decrypt_password(enc_key)
print("model=%s" % MODEL, flush=True)

# ===== 与 ch01_07_v11 完全一致的日式动漫漫画 STYLE =====
STYLE = ("日式动漫漫画风格，二次元画法，粗黑描边，赛璐璐上色，扁平色块，线条清晰，"
         "精致五官，细腻光影，电影感构图，竖屏构图，细节丰富，色彩明快，背景干净，"
         "画面中所有人物统一为日式动漫漫画风，绝不要出现任何写实风格，绝不要照片质感")

# 老周 45岁（修正版：疲惫但不衰老）
LZ = ("一名45岁的中国中年男子，二次元动漫角色画法，"
      "圆脸微胖（中年发福，脸颊饱满，皮肤紧致，不是老年松弛），"
      "黑色短发（发际线略高，鬓角微微泛白，但头发浓密、绝不稀疏、绝不绝顶），"
      "温和老实的长相，眼角有浅浅的鱼尾纹，眼神疲惫但仍有精神，"
      "眼袋是熬夜导致的轻微浮肿（不是衰老松弛下垂），"
      "鼻梁略宽，嘴唇稍厚，右耳垂有一颗小痣，"
      "穿深灰色Polo衫")

PROMPT = (LZ + "，坐在白天办公室的工位前，正面半身像，神情温和憨厚、略带疲惫，"
          "像是个从不诉苦的老好人，人物居中，"
          "背景是虚化的办公室格子间，冷色调，都市悬疑氛围" + STYLE)

SIZE = "720x1280"
SEED = 20260701
TMP = r"D:\7tan\7tanAI\镜像同事_小说\novel_img\laozhou_comic_tmp.png"
OUT = r"D:\7tan\7tanAI\镜像同事_小说\定妆图\character_laozhou_comic.png"


def gen(prompt, size, seed, out_path):
    payload = {"model": MODEL, "prompt": prompt, "size": size,
               "seed": seed, "watermark": False}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE_URL.rstrip("/") + "/images/generations", data=body,
        headers={"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    item = data.get("data", [{}])[0]
    img_url = item.get("url")
    b64 = item.get("b64_json")
    if b64:
        raw = base64.b64decode(b64)
    elif img_url:
        r2 = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(r2, timeout=120) as resp2:
            raw = resp2.read()
    else:
        raise RuntimeError("no image data: " + str(data)[:300])
    with open(out_path, "wb") as f:
        f.write(raw)
    return time.time() - t0


if __name__ == "__main__":
    os.makedirs(os.path.dirname(TMP), exist_ok=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    print("生成中... size=%s seed=%s" % (SIZE, SEED), flush=True)
    try:
        t = gen(PROMPT, SIZE, SEED, TMP)
        sz = os.path.getsize(TMP)
        shutil.copy(TMP, OUT)
        print("OK 用时%.0fs -> %s (%dKB)" % (t, OUT, sz // 1024), flush=True)
    except urllib.error.HTTPError as e:
        print("HTTP %s: %s" % (e.code, e.read().decode("utf-8", "ignore")[:400]), flush=True)
    except Exception as e:
        print("FAIL: %s" % str(e)[:300], flush=True)
