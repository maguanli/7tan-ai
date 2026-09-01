# -*- coding: utf-8 -*-
"""《游资是怎样炼成的》写实封面底图生成 v3（修正：画面干净清爽，人物不脏）"""
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

OUT_DIR = r"D:\7tan\7tanAI\陈小群\cover"
os.makedirs(OUT_DIR, exist_ok=True)
SIZE = "720x1280"

PROMPT = (
    "写实电影剧照风格，超写实摄影质感，绝不要动漫、不要二次元、不要插画、不要卡通。"
    "一个20岁出头的中国年轻男生，干净清爽的短发，皮肤白皙细腻、干净透亮，"
    "五官清秀，眼神专注又带点倔强，"
    "穿着一件干净整洁的白色T恤，独自坐在整洁温馨的小房间里，"
    "面前是一台普通的笔记本电脑，屏幕上是红红绿绿的股票K线图和跳动的行情数字，"
    "电脑旁边一部手机屏幕也亮着行情软件，"
    "一张干净整洁的书桌，一盏柔和的台灯，桌上整齐放着翻开的笔记本和一支笔、一杯水，"
    "背景是干净整洁的卧室墙面和深夜窗外的柔和城市灯光，"
    "明亮通透的光线，画面干净清爽、通透、无噪点、无脏乱，"
    "冷蓝色调为主，红绿K线光和台灯柔光映在他年轻清秀的脸上，"
    "电影级布光，浅景深，超高细节，8K画质，皮肤质感细腻，竖屏构图，"
    "人物位于画面上半部分，下半部分是书桌、笔记本电脑和手机，底部留出干净暗部空间"
)

def gen(prompt, size, seed, out_path):
    payload = {"model": MODEL, "prompt": prompt, "size": size,
               "seed": seed, "watermark": False}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE_URL.rstrip("/") + "/images/generations", data=body,
        headers={"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}, method="POST")
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
    return len(raw)

if __name__ == "__main__":
    seeds = [20260821, 20260822, 20260823]
    for i, seed in enumerate(seeds, 1):
        out = os.path.join(OUT_DIR, "cover_base_v3_%d.png" % i)
        print("[%d] 生成中 seed=%s ..." % (i, seed), flush=True)
        try:
            t0 = time.time()
            n = gen(PROMPT, SIZE, seed, out)
            print("[%d] OK 用时%.0fs (%dKB)" % (i, time.time() - t0, n // 1024), flush=True)
        except urllib.error.HTTPError as e:
            print("[%d] HTTP %s: %s" % (i, e.code, e.read().decode("utf-8", "ignore")[:300]), flush=True)
        except Exception as e:
            print("[%d] FAIL: %s" % (i, str(e)[:300]), flush=True)
        time.sleep(1)
    print("完成", flush=True)
