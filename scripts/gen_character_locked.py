# -*- coding: utf-8 -*-
"""
《镜像同事》人物定妆图 · 垫图锁脸生成脚本
以一张用户认可的基准脸（character_jiangchen_side.png）为参考图（image字段），
图生图生成同一个人物的 正面/表情特写/全身 定妆图，保证五官、发型、气质完全一致。
用法:
    ONLY=main python gen_character_locked.py   # 只生成正面(测试)
    python gen_character_locked.py             # 全部
"""
import os, sys, json, time, base64, urllib.request, urllib.error, io

# API_KEY 从数据库读取（见下方 _load_key）
API_KEY = None
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL = "doubao-seedream-5-0-pro-260628"

def _load_key():
    """从 data/games.db 读取 doubao-seedream-5.0-pro 的 API Key"""
    import sqlite3
    sys.path.insert(0, os.getcwd())
    from src.database.db import decrypt_password
    conn = sqlite3.connect(os.path.join("data", "games.db"))
    row = conn.execute(
        "SELECT api_key, base_url, model FROM ai_configs WHERE config_key='doubao-seedream-5.0-pro'"
    ).fetchone()
    if not row:
        raise RuntimeError("未找到 doubao-seedream-5.0-pro 配置")
    enc, base_url, model = row
    key = decrypt_password(enc)
    if not key:
        raise RuntimeError("API Key 解密失败")
    return key, base_url, model

CHAR_DIR = r"D:/7tan/7tanAI/镜像同事_小说/定妆图"
REF = os.path.join(CHAR_DIR, "character_jiangchen_side.png")

FACE_ANCHOR = (
    "参考图中这名中国青年男性（约27岁，黑色短发清爽利落，双眼皮，眼型修长，"
    "鼻梁高挺，脸型清瘦有棱角，气质清冷干净带正气，左眼角下方有一颗小痣）。"
    "【必须严格保持参考图中人物的脸型、五官、发型、眼神气质完全一致，绝对不要改变人物长相。】"
)

STYLE = "高质量动漫风格插画，精致五官，细腻光影，电影感构图，细节丰富，色彩明快，背景干净"

JOBS = [
    # (name, size, seed, 场景描述)
    ("character_jiangchen_main", "1024x1024", 8001,
     FACE_ANCHOR + "正面半身像，人物正对镜头，神情端正正气、温和可信赖，"
     "深灰色连帽卫衣，背景为简洁冷色调办公室走廊虚化，画面主体为人像，"
     + STYLE),
    ("character_jiangchen_face", "1024x1024", 8002,
     FACE_ANCHOR + "脸部特写，微侧角度，表情警觉专注、略带审视，"
     "深灰色连帽卫衣，背景虚化冷色，突出面部细节，"
     + STYLE),
    ("character_jiangchen_full", "720x1280", 8003,
     FACE_ANCHOR + "全身像，站立姿态，身姿挺拔，穿深灰色连帽卫衣、深色长裤、运动鞋，"
     "背景为简洁写字楼走廊冷色调，全身构图，"
     + STYLE),
]


def load_ref_b64(target_size):
    from PIL import Image, ImageOps
    img = Image.open(REF).convert("RGB")
    w, h = target_size.split("x")
    tw, th = int(w), int(h)
    img = ImageOps.fit(img, (tw, th), Image.LANCZOS)  # 居中裁剪保持比例
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    print("ref jpeg KB:", len(buf.getvalue()) // 1024, "size:", target_size, flush=True)
    return base64.b64encode(buf.getvalue()).decode()


def gen(name, size, seed, prompt):
    global API_KEY, BASE_URL, MODEL
    if not API_KEY:
        API_KEY, BASE_URL, MODEL = _load_key()
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "size": size,
        "seed": seed,
        "watermark": False,
        "image": "data:image/jpeg;base64," + load_ref_b64(size),
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + "/images/generations",
        data=body,
        headers={"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as resp:
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
        raise RuntimeError("no image data: %s" % str(data)[:300])
    out = os.path.join(CHAR_DIR, name + ".png")
    with open(out, "wb") as f:
        f.write(raw)
    print("OK ->", out, "bytes:", len(raw), "%.0fs" % (time.time() - t0), flush=True)
    return out


if __name__ == "__main__":
    only = os.environ.get("ONLY", "")
    jobs = [j for j in JOBS if not only or j[0].endswith(only)]
    for name, size, seed, prompt in jobs:
        try:
            gen(name, size, seed, prompt)
        except urllib.error.HTTPError as e:
            print("HTTP", e.code, e.read().decode("utf-8", "ignore")[:800], flush=True)
        except Exception as e:
            print("FAIL", name, repr(e), flush=True)
    print("DONE", flush=True)
