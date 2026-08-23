# -*- coding: utf-8 -*-
"""验证: Seedream 图片接口用 image 数组参考图(而非content) 是否真正锁脸+统一风格"""
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
print("model=%s key_len=%d" % (MODEL, len(API_KEY)), flush=True)

OUT = r"D:\7tan\7tanAI\镜像同事_小说\定妆图"
# 基准: 用户认可的江辰漫画风正面图
REF = os.path.join(OUT, "character_jiangchen_main_comic.png")
if not os.path.exists(REF):
    # 找候选
    for c in ["character_jiangchen_main.png", "character_jiangchen_npc_style.png", "character_jiangchen_npc_style3.png", "character_jiangchen_side.png"]:
        p = os.path.join(OUT, c)
        if os.path.exists(p):
            REF = p
            break
print("REF=%s" % REF, flush=True)
with open(REF, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

# 统一 STYLE = 《NPC》原版动漫风
STYLE = ("高质量动漫风格插画，精致五官，双眼对称自然，细腻光影，电影感构图，竖屏构图，"
         "细节丰富，色彩明快，背景干净，日式动漫角色造型，严禁写实照片，严禁真人3D")

# 用 image 数组字段传参考图
prompt = ("请严格保持参考图这个年轻中国男人的同一张脸、同一发型、同一清冷帅气气质完全不变，"
          "只把镜头改为正面半身照，人物居中。深灰色连帽卫衣内搭黑色T恤，站在深夜办公室工位前，"
          "身后是虚化的写字楼格子间和发冷光的电脑屏幕，环境昏暗。表情克制冷静、眼神坚定，"
          "左眼角下方一颗小痣清晰可见。冷色调主光从侧面打在脸上，突出帅气的五官。" + STYLE)

payload = {
    "model": MODEL,
    "prompt": prompt,
    "image": ["data:image/png;base64," + b64],   # 关键: image 数组，不是 content
    "size": "720x1280",
    "seed": 3102,
    "watermark": False,
}
body = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(BASE_URL.rstrip("/") + "/images/generations", data=body,
                             headers={"Authorization": "Bearer " + API_KEY,
                                      "Content-Type": "application/json"}, method="POST")
t0 = time.time()
try:
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
    out_path = os.path.join(OUT, "_verify_image_array.png")
    with open(out_path, "wb") as f:
        f.write(raw)
    print("OK %.0fs %dKB -> %s" % (time.time()-t0, len(raw)//1024, out_path), flush=True)
except urllib.error.HTTPError as e:
    # 若 image 数组不被接受，打印错误信息，明确响应体
    print("HTTP %d: %s" % (e.code, e.read().decode("utf-8", "ignore")[:500]), flush=True)
except Exception as e:
    print("ERR %s: %s" % (type(e).__name__, str(e)[:300]), flush=True)
