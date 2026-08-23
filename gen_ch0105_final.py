# -*- coding: utf-8 -*-
"""《偏差》ch01_05 重做 v2 —— 输出到英文目录 novel_img，落盘自检"""
import os, sys, json, time, base64, sqlite3, urllib.request, urllib.error

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

STYLE = ("日式动漫漫画风格，二次元画法，粗黑描边，赛璐璐上色，扁平色块，线条清晰，"
         "精致五官，细腻光影，电影感构图，竖屏构图，细节丰富，色彩明快，背景干净，"
         "画面中所有人物统一为日式动漫漫画风，绝不要出现任何写实风格，绝不要照片质感")

LZ = ("一名50岁的中国中年男子，二次元动漫角色画法，圆脸微胖，温和憨厚，"
      "黑色短发夹带灰白，眼睛略小带鱼尾纹，鼻梁宽，唇厚，脸颊饱满，"
      "右耳垂一颗小痣，穿深灰色Polo衫，内搭白衬衫")

PROMPT = (LZ + "，坐在办公室电脑前，画面中他的右手握着鼠标（右手在鼠标上，鼠标在他的右手下方），"
          "左手离开鼠标放在键盘上，这是右撇子操作姿势（他其实是左撇子，这是异常），神情专注平静，"
          "背景是办公室格子间和亮着冷光的电脑屏幕，"
          "中近景，冷色调办公光，都市悬疑氛围，"
          "整体保持二次元日式动漫漫画画风，粗黑描边，赛璐璐上色，不要写实" + STYLE)

SIZE = "720x1280"
SEED = 20260701
REF = r"D:\7tan\7tanAI\novel_img\ref_jc_comic_face.png"
OUT = r"D:\7tan\7tanAI\novel_img\ch01_05.png"

# 确保英文目录存在 + 垫图在
os.makedirs(os.path.dirname(OUT), exist_ok=True)
if not os.path.exists(REF):
    # 从中文定妆目录复制垫图到英文目录
    import shutil
    src = r"D:\7tan\7tanAI\镜像同事_小说\定妆图\ref_jc_comic_face.png"
    shutil.copy2(src, REF)
    print("copied ref -> %s" % REF, flush=True)

def gen(prompt, size, seed, ref_path, out_path):
    with open(ref_path, "rb") as f:
        ref_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")
    payload = {"model": MODEL, "prompt": prompt, "size": size,
               "seed": seed, "watermark": False,
               "image": [ref_b64]}
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
    # 落盘自检
    if not os.path.exists(out_path) or os.path.getsize(out_path) < 10000:
        raise RuntimeError("output not persisted!")
    return time.time() - t0

if __name__ == "__main__":
    print("生成中... 垫图=%s seed=%s" % (os.path.basename(REF), SEED), flush=True)
    try:
        t = gen(PROMPT, SIZE, SEED, REF, OUT)
        print("OK 用时%.0fs -> %s (%dKB)" % (t, OUT, os.path.getsize(OUT) // 1024), flush=True)
    except urllib.error.HTTPError as e:
        print("HTTP %s: %s" % (e.code, e.read().decode("utf-8", "ignore")[:400]), flush=True)
    except Exception as e:
        print("FAIL: %s" % str(e)[:300], flush=True)
