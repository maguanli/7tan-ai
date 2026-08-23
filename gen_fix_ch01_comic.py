# -*- coding: utf-8 -*-
"""
《偏差》第一章 4张写实图 -> 改回漫画风
★机制与 gen_laozhou_comic.py 100% 同源：垫《NPC》原图 ch4_check_01.png + 日式动漫STYLE
★这是能稳定出「动漫」的那把枪（content 数组 image_url 参考图），不是纯文本随机漂
★只重做：ch01_02 / ch01_04 / ch01_05 / ch01_07（用户指认偏写实的4张）
"""
import os, sys, json, time, base64, sqlite3, urllib.request, urllib.error

DB = r"D:\7tan\7tanAI\data\games.db"
sys.path.insert(0, r"D:\7tan\7tanAI")
from src.database.db import decrypt_password

conn = sqlite3.connect(DB)
row = conn.execute(
    "SELECT api_key, base_url, model FROM ai_configs WHERE config_key='doubao-seedream-5.0-pro'"
).fetchone()
enc_key, BASE_URL, MODEL = row
API_KEY = decrypt_password(enc_key)
print("model=%s" % MODEL, flush=True)

OUT_DIR = r"D:\7tan\7tanAI\镜像同事_小说\images"
REF = r"D:\7tan\7tanAI\downloads\fanqie\video\ch4_check_01.png"  # 《NPC》原图
with open(REF, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
REF_URL = "data:image/png;base64," + b64

# ===== 日式动漫 STYLE（与 gen_laozhou_comic.py 一字不差，能锁动漫）=====
STYLE = ("日式动漫插画风格（anime style），清晰中等粗细描边线条，轮廓线分明，"
         "赛璐璐上色，高饱和度，色彩明快鲜艳，动漫化精致五官，大眼睛明亮有神，"
         "细腻光影，电影感构图，竖屏构图，细节丰富，背景干净，画面精致有质感。"
         "禁止写实照片、禁止真人3D、禁止厚涂写实、禁止欧美漫画")

# ===== 人物锚点（与定妆一致）=====
JC = ("一名27岁的中国年轻男子，英俊帅气，正气阳光，黑色清爽短发，双眼皮，剑眉星目，"
      "高挺鼻梁，薄唇，清瘦有棱角的脸型，皮肤干净清透，左眼角下方一颗小痣，"
      "穿深灰色连帽卫衣，内搭白色T恤")
LZ = ("一名50岁的中国中年男子，圆脸微胖，温和憨厚，黑色短发夹带灰白，"
      "眼睛略小带鱼尾纹，鼻梁宽，唇厚，脸颊饱满，"
      "穿深灰色Polo衫")

# ===== 4张待重做（保留原场景，只换 STYLE + 垫图）=====
tasks = [
    ("ch01_02.png",
     JC + "，站在写字楼电梯里，身旁一个年轻男同事（市场部小刘）凑近搭话，"
          "江辰脸色疲惫、眼神躲闪，电梯金属门内壁反射冷光，显示屏数字跳动，"
          "都市冷色调，中景构图"),
    ("ch01_04.png",
     LZ + "，坐在办公室工位抬头冲镜头温和一笑，重点特写：他的右耳垂上有一颗明显的深褐色小痣"
          "（这是偏差，本该在左耳...实际剧情痣在右耳），眼神含笑却透着一点说不出的违和，"
          "冷光从侧面打来，半张脸隐在阴影，面部特写"),
    ("ch01_05.png",
     LZ + "，坐在电脑前，右手握着鼠标、左手搭在键盘边，姿势是标准右撇子坐姿，"
          "神情专注平静，背景是办公室格子间和屏幕，"
          "中近景，冷色调办公光，都市悬疑氛围"),
    ("ch01_07.png",
     JC + "，躲在写字楼卫生间最里面的隔间，后背靠在冰凉的隔间门板上，反锁门，"
          "低头掏出手机，昏暗的隔间里只有手机屏幕的冷光映在脸上，"
          "神情紧绷、呼吸急促，窄小空间特写"),
]

def gen(ref_url, text, size, seed, out_path):
    payload = {
        "model": MODEL,
        "prompt": text + "。" + STYLE,
        "content": [
            {"type": "image_url", "image_url": {"url": ref_url}},
            {"type": "text", "text": text}
        ],
        "size": size, "seed": seed, "watermark": False,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE_URL.rstrip("/") + "/images/generations", data=body,
        headers={"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}, method="POST")
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
    return time.time() - t0, os.path.getsize(out_path) // 1024

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    SEED = 3102  # 与 gen_laozhou_comic.py 一致，能锁脸锁动漫
    print("重做 %d 张写实图 -> 动漫... seed=%s" % (len(tasks), SEED), flush=True)
    for fname, text in tasks:
        out = os.path.join(OUT_DIR, fname)
        print("生成 [%s] ..." % fname, flush=True)
        try:
            t, kb = gen(REF_URL, text, "720x1280", SEED, out)
            print("  OK %.0fs -> %s (%dKB)" % (t, out, kb), flush=True)
        except urllib.error.HTTPError as e:
            print("  HTTP %s: %s" % (e.code, e.read().decode("utf-8", "ignore")[:400]), flush=True)
        except Exception as e:
            print("  FAIL: %s" % str(e)[:300], flush=True)
        time.sleep(1)
    print("完成", flush=True)
