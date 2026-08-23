# -*- coding: utf-8 -*-
"""《偏差》第一章《左耳上的痣》10张插图生成
策略：涉及老周正脸/江辰正脸的用定妆图垫图锁脸；纯场景/道具不垫图。
统一：720x1280 竖屏（抖音直接可用+公众号HTML自适应），seed=3102。
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
OUT = os.path.join(BASE, "images")
os.makedirs(OUT, exist_ok=True)

DZ = os.path.join(BASE, "定妆图")
STYLE = ("写实向插画，都市悬疑氛围，电影级光影，冷色调（蓝灰、深灰为主），"
         "略带颗粒质感，高细节，非二次元，非Q版，非赛博朋克")

def load_ref(fname):
    if not fname:
        return None
    p = os.path.join(DZ, fname)
    with open(p, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return "data:image/png;base64," + b64

# 垫图基准
JC = "character_jiangchen_main.png"   # 江辰
LZ = "character_laozhou_main.png"     # 老周

# (文件名, 垫图, 提示词)
tasks = [
    ("ch01_01.png", None,
     "清晨六点半的出租屋卧室，单人床，枕头边沿湿了一小块水渍，特写镜头对准那团深色水渍和枕巾的褶皱，"
     "窗外灰蓝色的晨光透过窗帘缝隙照进来，床头柜上放着一只手机和一杯凉透的白开水，"
     "空无一人，安静到诡异，只有闹钟的红色数字冷冷亮着。"),

    ("ch01_02.png", None,
     "写字楼电梯内景，早高峰，金属轿厢，楼层数字灯在跳动。"
     "一个穿深灰连帽卫衣的年轻男人背对镜头站在电梯门边，微微低头，肩膀有些紧绷；"
     "他身后一个穿浅蓝衬衫的男同事正笑着拍他的肩膀打招呼。"
     "冷白顶光，狭小空间，日常中带一丝压抑。"),

    ("ch01_03.png", LZ,
     "办公区工位前，一个穿深灰polo衫的中年男人坐在工位上，正抬起头露出一个温和的微笑，"
     "他的左耳垂正中央偏下有一颗深褐色小痣，清晰可见；"
     "画面前景是一个穿深灰连帽卫衣的年轻男人的背影，僵立在工位过道上，手里端着咖啡杯。"
     "请严格保持参考图中这个中年男人的同一张脸、同一发型、同一气质完全不变。"
     "冷色调办公室，日光灯惨白，氛围平静中透着不对劲。"),

    ("ch01_04.png", LZ,
     "特写镜头：一只中年男人的右手握住黑色办公鼠标，动作自然熟练；"
     "画面右上角能看到他左耳垂上的深褐色小痣。桌面上散着包子早餐袋和一杯豆浆，"
     "屏幕冷光照亮手背，背景虚化的办公室。请严格保持参考图中这个中年男人的同一张脸、同一发型、同一气质完全不变。"
     "平静日常的画面，却让人隐隐觉得哪里不对劲。"),

    ("ch01_05.png", LZ,
     "办公室工位旁，一个穿深灰polo衫的中年男人坐在工位上，手里掰着半个包子，抬头露出憨厚温和的笑容，像在聊家常；"
     "画面一侧一个穿深灰连帽卫衣的年轻男人侧身站着，眼神死死盯着他，表情紧绷。"
     "桌上放着一小盆仙人掌盆栽作为前景点缀。请严格保持参考图中这个中年男人的同一张脸、同一发型、同一气质完全不变。"
     "冷灰蓝色调，两人的距离感与违和感透过构图传达。"),

    ("ch01_06.png", LZ,
     "办公桌旁，一个穿深灰polo衫的中年男人右手握笔在一沓报销单上签字，笔尖划过纸面；"
     "旁边一个年轻男同事探过头来看，表情带笑，像在打趣。"
     "请严格保持参考图中这个中年男人的同一张脸、同一发型、同一气质完全不变。"
     "冷色调，忙碌的办公室日常，画面远处半张脸藏在阴影里的年轻男人目光投向这边。"),

    ("ch01_07.png", JC,
     "写字楼厕所最里面的隔间，狭小昏暗，一个穿深灰连帽卫衣的年轻男人背靠隔间门板蹲坐在地上，"
     "双手举着手机，手机屏幕的冷白光照亮他紧绷的脸，瞳孔里映着屏幕上的文字。"
     "请严格保持参考图中这个年轻男人的同一张脸、同一发型、同一气质完全不变。"
     "瓷砖墙面冰凉反光，四周安静，只有头顶日光灯发出细微的嗡嗡声。"),

    ("ch01_08.png", None,
     "手机屏幕极致特写，备忘录APP界面，分类标签「观察」，列表里密密麻麻的短记录："
     "「3月2日：老周用右手开瓶盖」「3月5日：老周的门禁卡挂在左边口袋」"
     "「3月7日：老周倒水，右手拎壶」「3月9日：老周说数分析，口误」"
     "「3月12日：老周右耳有颗痣，今天看，好像没有了」。"
     "屏幕冷光，四周漆黑，白色小字清晰可辨。"),

    ("ch01_09.png", None,
     "手机屏幕特写，备忘录「观察」分类的最顶端，孤零零一条记录："
     "「1月3日：江辰。开始。」，只有日期和一个名字，没有其他任何解释。"
     "屏幕冷白的光在黑暗中格外刺眼，背景是模糊的厕所隔间门板。"
     "画面极简，信息极少，却让人脊背发凉。"),

    ("ch01_10.png", JC,
     "黑暗的厕所隔间里，一部手机屏幕已经熄灭，黑色玻璃屏面上倒映出一张年轻男人的脸，"
     "他眼神直直地盯着屏幕里的自己，表情僵硬、瞳孔微缩。"
     "请严格保持参考图中这个年轻男人的同一张脸、同一发型、同一气质完全不变。"
     "冷蓝色微光从侧面勾勒出他的轮廓，四周一片漆黑，只有那一张倒影里的脸，和无法言说的恐惧。"),
]

def gen(fname, ref_url, text, size="720x1280"):
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
    with open(os.path.join(OUT, fname), "wb") as f:
        f.write(raw)
    return time.time() - t0

if __name__ == "__main__":
    ok = 0
    for i, (fname, ref, text) in enumerate(tasks, 1):
        ref_url = load_ref(ref) if ref else None
        print("[%d/10] %s ref=%s ..." % (i, fname, ref or "none"), flush=True)
        try:
            t = gen(fname, ref_url, text)
            kb = os.path.getsize(os.path.join(OUT, fname)) // 1024
            print("  OK %.0fs %dKB" % (t, kb), flush=True)
            ok += 1
        except urllib.error.HTTPError as e:
            print("  FAIL HTTP %d: %s" % (e.code, e.read().decode("utf-8", "ignore")[:300]), flush=True)
        except Exception as e:
            print("  FAIL %s: %s" % (type(e).__name__, str(e)[:200]), flush=True)
        time.sleep(1)
    print("done %d/10" % ok)
