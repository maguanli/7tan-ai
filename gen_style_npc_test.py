# -*- coding: utf-8 -*-
"""《偏差》风格复刻测试：垫《NPC》正文分镜原图，复刻其动漫画风
参考图: downloads/fanqie/video/ch4_check_01.png (确认: 动漫+清晰描边+赛璐璐高饱和+冷色调)
输出: 定妆图/character_jiangchen_npc_style3.png
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
REF = r"downloads\fanqie\video\ch4_check_01.png"  # 《NPC》正文分镜，风格参照
with open(REF, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
REF_URL = "data:image/png;base64," + b64

# 完全抛弃"写实向"！复刻《NPC》动漫风
STYLE = ("日式动漫插画风格（anime style），清晰中等粗细描边线条，轮廓线分明，"
         "赛璐璐上色，高饱和度，色彩明快鲜艳，动漫化精致五官，大眼睛明亮有神，"
         "细腻光影，电影感构图，竖屏构图，细节丰富，背景干净，画面精致有质感。"
         "禁止写实照片、禁止真人3D、禁止厚涂写实、禁止欧美漫画")

FACE = ("27岁中国年轻男性，帅气温和，黑色清爽短发，剑眉星目，明亮有神的眼睛，"
        "脸型清瘦有棱角，身姿挺拔，深灰色连帽卫衣。"
        "请严格模仿参考图片的动漫画风与上色质感（描边、赛璐璐、高饱和），"
        "但人物是一个全新的中国年轻男性，不是参考图中的人物。")

PROMPT = (FACE + "他坐在深夜办公室工位前，神情专注、眼神坚定，带着一丝警觉，"
          "左眼角下方有一颗小痣。背景是虚化的写字楼格子间和冷光电脑屏幕，"
          "冷色调主光从侧面打在脸上，都市悬疑氛围。")

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
    gen(os.path.join(OUT, "character_jiangchen_npc_style3.png"), "720x1280", PROMPT)
