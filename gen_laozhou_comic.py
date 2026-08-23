# -*- coding: utf-8 -*-
"""《偏差》老周动漫基准图 —— 与江辰动漫基准 100% 同源
参考图: downloads/fanqie/video/ch4_check_01.png（和江辰 npc_style 同一张）
STYLE: 一字不差复制 gen_style_npc_test.py 的动漫风格
输出: 定妆图/character_laozhou_comic_base.png
"""
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
REF = r"downloads\fanqie\video\ch4_check_01.png"  # 和江辰动漫基准同一张《NPC》原图
with open(REF, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
REF_URL = "data:image/png;base64," + b64

# 与江辰 npc_style 一字不差的动漫 STYLE
STYLE = ("日式动漫插画风格（anime style），清晰中等粗细描边线条，轮廓线分明，"
         "赛璐璐上色，高饱和度，色彩明快鲜艳，动漫化精致五官，大眼睛明亮有神，"
         "细腻光影，电影感构图，竖屏构图，细节丰富，背景干净，画面精致有质感。"
         "禁止写实照片、禁止真人3D、禁止厚涂写实、禁止欧美漫画")

# 老周人物描述（动漫化 50 岁大叔，右耳垂小痣）
LZ = ("50岁中国中年男性，动漫化圆润脸型，黑色利落短发，浓眉，温和的眼睛，"
      "眼袋和法令纹以卡通化方式表现（不写实），下巴圆润，气质温和憨厚，"
      "微微发福，身穿深灰色polo衫。"
      "请严格模仿参考图片的动漫画风与上色质感（描边、赛璐璐、高饱和），"
      "但人物是一个全新的50岁中国中年男性，不是参考图中的人物。")

PROMPT = (LZ + "他坐在办公工位前，转头看向镜头，脸上带着温和憨厚的笑容，"
          "右耳垂上有一颗明显的小痣。背景是虚化的现代办公室，冷色调光线，"
          "都市悬疑氛围。")

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
    print("[OK] %s  %.1fs  %d bytes" % (out_path, time.time() - t0, len(raw)), flush=True)

if __name__ == "__main__":
    gen(os.path.join(OUT, "character_laozhou_comic_base.png"), "720x1280", PROMPT)
