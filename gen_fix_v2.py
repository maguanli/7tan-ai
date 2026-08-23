# -*- coding: utf-8 -*-
"""《偏差》v2 修复脚本
1) 老周定妆 main/face/full 全部以 side(右耳垂痣基准) 垫图锁脸 → 统一为同一人
2) 第一章 03/04/05/06 老周插图 用新基准垫图重生成
   (03/04 按剧情突出「左耳垂痣」异常点；05/06 保持同一张脸不强调痣)
3) 第一章 07/10 江辰插图 用 jiangchen_main 垫图重生成，强约束东亚中国面孔
统一 seed=3102，竖屏 720x1280，老周定妆特写 1024x1024。
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

BASE = r"D:\7tan\7tanAI\镜像同事_小说"
DZ = os.path.join(BASE, "定妆图")
IMG = os.path.join(BASE, "images")

STYLE = ("写实向插画，都市悬疑氛围，电影级光影，冷色调（蓝灰、深灰为主），"
         "略带颗粒质感，高细节，非二次元，非Q版，非赛博朋克，"
         "中国都市职场，东亚中国面孔")

def load_ref(path):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return "data:image/png;base64," + b64

REF_LZ = os.path.join(DZ, "character_laozhou_side.png")   # 老周基准：右耳垂痣
REF_JC = os.path.join(DZ, "character_jiangchen_main.png")  # 江辰基准

REF_LZ_URL = load_ref(REF_LZ)
REF_JC_URL = load_ref(REF_JC)

LZ_FACE = ("请严格保持参考图中这个中年男人的同一张脸、同一发型、同一温和气质完全不变，"
           "深灰色polo衫、卡其色长裤、棕色皮带，右耳垂上有一颗深褐色小痣清晰可见"
           "（注意：是人物自己的右耳，不要镜像成左耳）。")

# (输出路径, 尺寸, 垫图URL, 提示词)
tasks = [
    # ---- 老周定妆 3 张：以 side 垫图，统一右耳垂痣 ----
    (os.path.join(DZ, "character_laozhou_main.png"), "1024x1024", REF_LZ_URL,
     LZ_FACE + "改为正面半身像，他坐在办公工位前，双手交叠放在桌上，神情温和、微微带笑，眼袋明显，"
     "背后是模糊的办公室，冷色调光线从窗户方向照入，面部细节清晰。"),
    (os.path.join(DZ, "character_laozhou_face.png"), "1024x1024", REF_LZ_URL,
     LZ_FACE + "改为面部特写，镜头推近到脸部，聚焦在温和却难掩疲惫的笑容上，眼袋沉重，眼角皱纹明显，"
     "眼神里带着隐忍和一丝不易察觉的麻木，深灰色polo衫领口露在画面下方，背景虚化为模糊的办公室，柔和冷调光线。"),
    (os.path.join(DZ, "character_laozhou_full.png"), "720x1280", REF_LZ_URL,
     LZ_FACE + "改为全身竖屏构图，他站在办公室茶水间门口，手里端着一杯咖啡，微微弓着背，体态略显疲惫，"
     "周围是普通的公司办公环境，灯光是冷白色。"),

    # ---- 第一章老周插图 4 张：同一张脸；03/04 突出「左耳垂痣」异常点 ----
    (os.path.join(IMG, "ch01_03.png"), "720x1280", REF_LZ_URL,
     "请严格保持参考图中这个中年男人的同一张脸、同一发型、同一温和气质完全不变。"
     "办公区工位前，他坐在工位上抬起头露出一个温和的微笑，左耳垂正中央偏下有一颗深褐色小痣清晰可见"
     "（注意：剧情异常点，痣在人物自己的左耳，右耳没有痣）。"
     "画面前景是一个穿深灰连帽卫衣的年轻男人的背影，僵立在工位过道上，手里端着咖啡杯。"
     "冷色调办公室，日光灯惨白，氛围平静中透着不对劲。"),
    (os.path.join(IMG, "ch01_04.png"), "720x1280", REF_LZ_URL,
     "请严格保持参考图中这个中年男人的同一张脸、同一发型、同一温和气质完全不变。"
     "特写镜头：他的右手握住黑色办公鼠标，动作自然熟练，画面右侧能看到他左耳垂上的深褐色小痣"
     "（注意：剧情异常点，痣在人物自己的左耳，右耳没有痣）。"
     "桌面上散着包子早餐袋和一杯豆浆，屏幕冷光照亮手背，背景虚化的办公室。"),
    (os.path.join(IMG, "ch01_05.png"), "720x1280", REF_LZ_URL,
     "请严格保持参考图中这个中年男人的同一张脸、同一发型、同一温和气质完全不变。"
     "办公室工位旁，他坐在工位上，手里掰着半个包子，抬头露出憨厚温和的笑容，像在聊家常；"
     "画面一侧一个穿深灰连帽卫衣的年轻男人侧身站着，眼神死死盯着他，表情紧绷。"
     "桌上放着一小盆仙人掌盆栽作为前景点缀，冷灰蓝色调，两人的距离感与违和感透过构图传达。"),
    (os.path.join(IMG, "ch01_06.png"), "720x1280", REF_LZ_URL,
     "请严格保持参考图中这个中年男人的同一张脸、同一发型、同一温和气质完全不变。"
     "办公桌旁，他右手握笔在一沓报销单上签字，笔尖划过纸面，旁边一个年轻男同事探过头来看，表情带笑，像在打趣；"
     "画面远处半张脸藏在阴影里的年轻男人目光投向这边，冷色调，忙碌的办公室日常。"),

    # ---- 第一章江辰插图 2 张：以 main 垫图 + 东亚中国面孔约束 ----
    (os.path.join(IMG, "ch01_07.png"), "720x1280", REF_JC_URL,
     "请严格保持参考图中这个年轻男人的同一张脸、同一发型、同一气质完全不变，东亚中国面孔，深黑色短发，自然黄皮肤。"
     "写字楼厕所最里面的隔间，狭小昏暗，他背靠隔间门板蹲坐在地上，双手举着手机，"
     "手机屏幕的冷白光照亮他紧绷的脸，瞳孔里映着屏幕上的文字。"
     "瓷砖墙面冰凉反光，四周安静，只有头顶日光灯发出细微的嗡嗡声。"),
    (os.path.join(IMG, "ch01_10.png"), "720x1280", REF_JC_URL,
     "请严格保持参考图中这个年轻男人的同一张脸、同一发型、同一气质完全不变，东亚中国面孔，深黑色短发，自然黄皮肤。"
     "黑暗的厕所隔间里，一部手机屏幕已经熄灭，黑色玻璃屏面上倒映出他的脸，他眼神直直地盯着屏幕里的自己，"
     "表情僵硬、瞳孔微缩，冷蓝色微光从侧面勾勒出他的轮廓，四周一片漆黑。"),
]

def gen(out_path, size, ref_url, text):
    payload = {
        "model": MODEL,
        "prompt": text + "。" + STYLE,
        "content": [{"type": "image_url", "image_url": {"url": ref_url}},
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
    return time.time() - t0

if __name__ == "__main__":
    ok = 0
    for i, (out_path, size, ref_url, text) in enumerate(tasks, 1):
        print("[%d/%d] %s ..." % (i, len(tasks), os.path.basename(out_path)), flush=True)
        try:
            t = gen(out_path, size, ref_url, text)
            kb = os.path.getsize(out_path) // 1024
            print("  OK %.0fs %dKB" % (t, kb), flush=True)
            ok += 1
        except urllib.error.HTTPError as e:
            print("  FAIL HTTP %d: %s" % (e.code, e.read().decode("utf-8", "ignore")[:300]), flush=True)
        except Exception as e:
            print("  FAIL %s: %s" % (type(e).__name__, str(e)[:200]), flush=True)
        time.sleep(1)
    print("done %d/%d" % (ok, len(tasks)))
