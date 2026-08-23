# -*- coding: utf-8 -*-
"""
《偏差》人物定妆图生成 - Doubao Seedream 5.0 Pro
从数据库 ai_configs 解密 API Key 后生成 8 张定妆图
"""
import os, sys, json, time, base64, sqlite3, urllib.request, urllib.error

sys.path.insert(0, os.getcwd())
from src.database.db import decrypt_password

DB = os.path.join("data", "games.db")
conn = sqlite3.connect(DB)
row = conn.execute(
    "SELECT api_key, base_url, model FROM ai_configs WHERE config_key='doubao-seedream-5.0-pro'"
).fetchone()
if not row:
    print("ERROR: no doubao-seedream config")
    sys.exit(1)
enc_key, BASE_URL, MODEL = row
API_KEY = decrypt_password(enc_key)
if not API_KEY:
    print("ERROR: api_key decrypt failed")
    sys.exit(1)
print("api_key decrypted len=%d model=%s" % (len(API_KEY), MODEL), flush=True)

OUT_DIR = r"D:\7tan\7tanAI\镜像同事_小说\定妆图"
os.makedirs(OUT_DIR, exist_ok=True)

STYLE = ("写实向插画，都市悬疑氛围，电影级光影，冷色调（蓝灰、深灰为主），"
         "略带颗粒质感，高细节，非二次元，非Q版，非赛博朋克")

JC_FACE = ("27岁中国男性，偏瘦长脸，下颌线清晰但不硬朗，黑色短发微乱、刘海略遮眉，"
           "单眼皮，眼神警惕多疑，眉头习惯性微皱，左眼角下方一颗小痣，"
           "皮肤略苍白带熬夜疲惫感，178cm，偏瘦，久坐办公室略驼背")
JC_CLOTH = "深灰色连帽卫衣，内搭藏青色纯色T恤，深色牛仔裤，简单帆布鞋"

LZ_FACE = ("45岁中国男性，圆脸，眼袋重，头发稀疏、鬓角发白，"
           "温和的老好人式笑容，眼角有皱纹，微胖，略驼背，右耳垂一颗痣")
LZ_CLOTH = "深灰色polo衫，卡其色长裤，旧皮带，手腕一只旧手表"

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
    ("character_jiangchen_main.png",
     JC_FACE + "。他站在深夜办公室的工位前，正面面对镜头，身后是虚化的写字楼格子间和发着冷光的电脑屏幕，环境昏暗。"
     "穿" + JC_CLOTH + "。表情克制、疲惫、压抑着焦虑，眼神带着一丝警惕地看向镜头。"
     "半身构图，人物居中。冷色调主光从侧面打在脸上，面部细节清晰。" + STYLE,
     "768x1024", 1001),

    ("character_jiangchen_side.png",
     JC_FACE + "。他站在窗前，镜头拍他的左侧脸（展示左眼角下方那颗小痣），45度侧面。"
     "窗外是灰暗的城市夜景，玻璃上反射出模糊的冷光。穿" + JC_CLOTH + "。"
     "眼神望向窗外，眉头微皱，若有所思，表情凝重。侧身半身构图。冷色调侧逆光勾勒面部轮廓。" + STYLE,
     "768x1024", 1002),

    ("character_jiangchen_face.png",
     JC_FACE + "。面部特写，镜头推近到他的脸，聚焦在警惕的眼神和微皱的眉头。"
     "他像是发现了什么不对劲的事，瞳孔微微收缩，嘴角紧抿，神情紧张、狐疑。"
     "穿" + JC_CLOTH + "的深灰色连帽卫衣领口露在画面下方。背景虚化为模糊的办公室环境。冷色调，光影在脸上形成明暗对比。" + STYLE,
     "1024x1024", 1003),

    ("character_jiangchen_full.png",
     JC_FACE + "。全身构图，他站在空无一人的深夜办公室过道中央，两边是整齐的工位和亮着的显示器，头顶的日光灯发出冷白微暗的光。"
     "穿" + JC_CLOTH + "，双手插在卫衣口袋里，微微弓着背，站姿略紧张。地面有轻微反光，营造出压抑、孤独的都市悬疑氛围。" + STYLE,
     "720x1280", 1004),

    ("character_laozhou_main.png",
     LZ_FACE + "。他坐在办公工位前，正面面对镜头，身后是虚化的办公室格子间和电脑屏幕，环境是普通的白天办公室。"
     "穿" + LZ_CLOTH + "。脸上带着温和、疲惫、隐忍的笑容，像是个从不诉苦的老好人。"
     "半身构图，人物居中。自然柔和的冷调光线，面部细节清晰。" + STYLE,
     "768x1024", 2001),

    ("character_laozhou_side.png",
     LZ_FACE + "。镜头拍他的右侧脸，45度侧面，清晰露出右耳垂上那颗痣。"
     "他坐在工位，转头看向旁边的同事，脸上带着温和的笑容，眼袋明显。穿" + LZ_CLOTH + "。"
     "身后是模糊的办公环境。侧身半身构图，冷色调光线从窗户方向照入。" + STYLE,
     "768x1024", 2002),

    ("character_laozhou_face.png",
     LZ_FACE + "。面部特写，镜头推近到他的脸，聚焦在他温和却难掩疲惫的笑容上，眼袋沉重，眼角皱纹明显，眼神里带着隐忍和一丝不易察觉的麻木。"
     "穿" + LZ_CLOTH + "的深色polo衫领口露在画面下方。背景虚化为模糊的办公室环境。柔和冷调光线。" + STYLE,
     "1024x1024", 2003),

    ("character_laozhou_full.png",
     LZ_FACE + "。全身构图，他站在办公室茶水间门口，手里端着一杯咖啡，微微弓着背，体态略显疲惫。"
     "穿" + LZ_CLOTH + "。周围是普通的公司办公环境，灯光是冷白色。" + STYLE,
     "720x1280", 2004),
]

if __name__ == "__main__":
    ok_count = 0
    for idx, (fname, prompt, size, seed) in enumerate(tasks, 1):
        out_path = os.path.join(OUT_DIR, fname)
        if os.path.exists(out_path):
            print("[%d/8] SKIP(exists) %s" % (idx, fname), flush=True)
            ok_count += 1
            continue
        print("[%d/8] gen %s (size=%s seed=%d)..." % (idx, fname, size, seed), flush=True)
        ok, used_size, t = gen_with_fallback(prompt, size, seed, out_path)
        if ok:
            ok_count += 1
            kb = os.path.getsize(out_path) // 1024
            print("  OK %s %.0fs %dKB" % (used_size, t, kb), flush=True)
        else:
            print("  FAIL %s" % fname, flush=True)
        time.sleep(1)
    print("=" * 40)
    print("done %d/8" % ok_count)
