# -*- coding: utf-8 -*-
"""ch01_05 用原版枪 gen_jiangchen_npc_style.py 参数重做：
STYLE/SEED/SIZE 一字不改、无垫图，只把剧情文本换成 ch01_05 情节"""
import os, sys, json, time, base64, sqlite3, shutil, urllib.request, urllib.error

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

# ===== NPC 原版 STYLE（一字不改，与 gen_jiangchen_npc_style.py 完全一致）=====
STYLE = ("高质量动漫风格插画，精致五官，双眼对称自然，细腻光影，电影感构图，竖屏构图，"
         "细节丰富，色彩明快，背景干净")

# 老周角色描述（动漫化，与江辰描述同风格）
LZ = ("一名50岁的中国中年男子，英俊正气，黑色短发夹带灰白，圆脸微胖，温和憨厚，"
      "眼睛略小带鱼尾纹，鼻梁宽，唇厚，脸颊饱满，右耳垂一颗小痣，"
      "穿深灰色Polo衫，内搭白衬衫")

PROMPT = (LZ + "，坐在办公室电脑前，右手握着鼠标（鼠标在右手下方），"
          "左手搭在键盘上，右撇子操作姿势，神情专注平静，"
          "背景是清晨的办公室格子间，电脑屏幕亮着冷光，"
          "中近景，冷色调，都市悬疑氛围" + STYLE)

SIZE = "720x1280"
SEED = 20260701

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
    if not os.path.exists(out_path) or os.path.getsize(out_path) < 10000:
        raise RuntimeError("output not persisted!")
    return time.time() - t0

if __name__ == "__main__":
    out = r"D:\7tan\7tanAI\novel_img\ch01_05.png"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print("生成中... 原版枪参数 size=%s seed=%s 无垫图 STYLE一字不改" % (SIZE, SEED), flush=True)
    try:
        t = gen(PROMPT, SIZE, SEED, out)
        print("OK 用时%.0fs -> %s (%dKB)" % (t, out, os.path.getsize(out) // 1024), flush=True)
        dst = r"D:\7tan\7tanAI\镜像同事_小说\images\ch01_05.png"
        shutil.copy2(out, dst)
        print("已复制 -> %s (%dKB)" % (dst, os.path.getsize(dst) // 1024), flush=True)
    except urllib.error.HTTPError as e:
        print("HTTP %s: %s" % (e.code, e.read().decode("utf-8", "ignore")[:400]), flush=True)
    except Exception as e:
        print("FAIL: %s" % str(e)[:300], flush=True)
