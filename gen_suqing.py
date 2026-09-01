# -*- coding: utf-8 -*-
"""《偏差》苏晴定妆图 —— 美女版，保留剧情锚点（26岁/自由插画师/两个酒窝/铅笔别发/碎发）"""
import os, sys, json, time, base64, sqlite3, urllib.request, urllib.error

sys.path.insert(0, os.getcwd())
from src.database.db import decrypt_password

DB = os.path.join("data", "games.db")
conn = sqlite3.connect(DB)
row = conn.execute(
    "SELECT api_key, base_url, model FROM ai_configs WHERE config_key='doubao-seedream-5.0-pro'"
).fetchone()
if not row:
    print("ERROR: no doubao-seedream config"); sys.exit(1)
enc_key, BASE_URL, MODEL = row
API_KEY = decrypt_password(enc_key)
if not API_KEY:
    print("ERROR: api_key decrypt failed"); sys.exit(1)
print("api_key decrypted len=%d model=%s" % (len(API_KEY), MODEL), flush=True)

OUT_DIR = r"D:\7tan\7tanAI\镜像同事_小说\定妆图"
os.makedirs(OUT_DIR, exist_ok=True)

STYLE = ("写实向插画，都市悬疑氛围，电影级光影，高细节，"
         "整体冷色调（蓝灰、深灰为主），但工作室暖黄台灯做局部对比，"
         "略带颗粒质感，非二次元，非Q版，非赛博朋克")

# 苏晴 · 美女版 —— 保留剧情锚点：26岁、两个酒窝(一左一右)、长发用铅笔别着、几缕碎发、插画师气质
SQ_FACE = ("26岁中国女性，长相清纯漂亮、明艳动人，五官精致立体，"
           "鹅蛋脸小巧精致、下颌线条柔和，皮肤白皙细腻有光泽，"
           "一双大眼睛明亮有神、眼尾微微上挑，笑起来眼睛弯成月牙，"
           "鼻梁小巧挺秀，唇形饱满自然、唇色红润，"
           "两个甜甜的酒窝，一左一右（笑起来很明显，是她最大的标志），"
           "乌黑柔顺的长发及肩偏长，用一支木铅笔随性地别在脑后，几缕碎发散在耳边，"
           "身材纤细窈窕、比例匀称，气质清新文艺、带着插画师的随性与灵气，"
           "是那种干净好看、让人一眼心动的文艺系美女")

SQ_CLOTH = "米白色宽松针织开衫，内搭浅色棉麻衬衫，下穿卡其色直筒休闲裤，脚踩帆布鞋，衣袖和指节上沾着零星的颜料痕迹"

def gen(prompt, size, seed, out_path):
    payload = {"model": MODEL, "prompt": prompt, "size": size,
               "seed": seed, "response_format": "url", "watermark": False}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE_URL.rstrip("/") + "/images/generations", data=body,
                                 headers={"Authorization": "Bearer " + API_KEY,
                                          "Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    item = data.get("data", [{}])[0]
    img_url = item.get("url"); b64 = item.get("b64_json")
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

def gen_with_fallback(prompt, size, seed, out_path):
    for try_size in [size, "1024x1024", "720x1280"]:
        try:
            t = gen(prompt, try_size, seed, out_path)
            return True, try_size, t
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            print("  [fallback] %s -> HTTP %s: %s" % (try_size, e.code, body[:200]), flush=True)
        except Exception as e:
            print("  [error] %s -> %s" % (try_size, str(e)[:200]), flush=True)
    return False, None, 0

tasks = [
    ("character_suqing_main.png",
     SQ_FACE + "。她站在自己的插画工作室里，正面面对镜头，微笑着、露出两个酒窝，"
     "身后是软木板钉满画稿的墙、桌上摊开着颜料、马克笔和手账。"
     "穿" + SQ_CLOTH + "。表情温柔明朗，眼神清澈带笑。"
     "半身构图，人物居中。暖黄台灯从侧面打亮她的脸，窗外是冷蓝的都市夜色，冷暖对比，突出她干净好看的容貌。" + STYLE,
     "768x1024", 3201),

    ("character_suqing_side.png",
     SQ_FACE + "。她坐在工作室的窗边，镜头拍她45度侧脸，突出柔和的下颌线和小巧挺秀的鼻梁，几缕碎发垂在耳侧。"
     "手里握着一支铅笔，微微低头在看摊开的手账，神情专注、安静。"
     "穿" + SQ_CLOTH + "。窗外是灰暗的城市夜景，玻璃反射模糊冷光。"
     "侧身半身构图。冷色侧逆光勾勒她脸部和发丝的轮廓，暖黄台灯补光。氛围文艺、恬静。" + STYLE,
     "768x1024", 3202),

    ("character_suqing_face.png",
     SQ_FACE + "。面部特写，镜头推近到她的脸，聚焦在明亮弯弯的眼睛和两个酒窝，突出精致好看的五官。"
     "她笑起来，眼睛弯成月牙，两个酒窝一左一右很明显，嘴角上扬，神情俏皮温柔。"
     "一支木铅笔别在脑后的头发边缘露出一点。背景虚化为工作室的画稿和暖黄灯光。"
     "冷色调打底、暖光映脸，明暗对比让五官更立体。" + STYLE,
     "1024x1024", 3203),

    ("character_suqing_full.png",
     SQ_FACE + "。全身构图，她站在插画工作室中央，四周是画架、堆叠的画稿、颜料罐和一排排马克笔，"
     "软木板上钉满零散的画稿，桌角摊着翻开的手账。"
     "穿" + SQ_CLOTH + "，双手随意交叠在身前，身姿轻盈自然，站姿带着插画师的随性。"
     "头顶暖黄吊灯发出柔光，窗外透进冷蓝夜色，地面微微反光，营造出文艺又带一丝悬疑的氛围。" + STYLE,
     "720x1280", 3204),
]

if __name__ == "__main__":
    ok = 0
    for idx, (fname, prompt, size, seed) in enumerate(tasks, 1):
        out_path = os.path.join(OUT_DIR, fname)
        print("[%d/4] gen %s (size=%s seed=%d)..." % (idx, fname, size, seed), flush=True)
        okk, used, t = gen_with_fallback(prompt, size, seed, out_path)
        if okk:
            ok += 1
            kb = os.path.getsize(out_path) // 1024
            print("  OK %s %.0fs %dKB" % (used, t, kb), flush=True)
        else:
            print("  FAIL %s" % fname, flush=True)
        time.sleep(1)
    print("=" * 40)
    print("done %d/4" % ok)
