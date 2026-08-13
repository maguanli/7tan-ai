# -*- coding: utf-8 -*-
"""调用豆包 doubao-seedream-5.0-pro 批量生成公众号 LOGO 候选（漫画风+简约）"""
import sys, os, json, sqlite3, urllib.request, base64, time

sys.path.insert(0, os.getcwd())
from src.database.db import decrypt_password

DB = os.path.join("data", "games.db")
conn = sqlite3.connect(DB)
row = conn.execute(
    "SELECT api_key, base_url, model FROM ai_configs WHERE config_key='doubao-seedream-5.0-pro'"
).fetchone()
if not row:
    print("ERROR: 未找到 doubao-seedream-5.0-pro 配置")
    sys.exit(1)

enc_key, base_url, model = row
api_key = decrypt_password(enc_key)
if not api_key:
    print("ERROR: api_key 解密失败")
    sys.exit(1)
print("api_key 解密成功, 长度:", len(api_key))
print("model:", model, "| base_url:", base_url)

PROMPTS = {
    "candidate_1": (
        "公众号头像LOGO，极简漫画风格，主题：人生大起大落。"
        "画面主体：一条流畅的黑色波浪曲线从画面左下角向右上角起伏延伸，"
        "曲线形状像心电图也像人生轨迹，曲线最高点站着一个小小的人物剪影张开双臂，"
        "曲线最低点有一颗小小的金色星星。"
        "纯白色背景，黑色细线条为主，少量金色点缀，扁平矢量插画风格，"
        "干净留白，圆形构图，适合小尺寸头像显示，无任何文字，简约高级有设计感"
    ),
    "candidate_2": (
        "公众号头像LOGO，可爱卡通漫画风格，主题：人生起伏。"
        "画面：一个小小卡通人物站在陡峭山峰顶端举起双手欢呼，"
        "山脚下是低谷洼地，低谷里有一颗明亮的小星星，"
        "旁边有蜿蜒的登山小路。"
        "扁平漫画色块风格，白色背景，蓝色、橙色为主色调，"
        "圆形构图适合头像，无任何文字，简约明快，小尺寸清晰"
    ),
    "candidate_3": (
        "公众号头像LOGO，极简线条漫画风格，主题：人生如过山车。"
        "画面：一条黑色过山车轨道线条从低处冲上高处再落回低处，"
        "轨道最高点有一辆小小的过山车车厢，最低点有一颗小星星点缀。"
        "纯白背景，黑色细线条加一点红色点缀，"
        "扁平插画风，圆形构图，无文字，极简有设计感，适合头像"
    ),
}

out_dir = os.path.join("data", "logo")
os.makedirs(out_dir, exist_ok=True)

url = base_url.rstrip("/") + "/images/generations"

for name, prompt in PROMPTS.items():
    print("\n===== 生成", name, "=====")
    body = {
        "model": model,
        "prompt": prompt,
        "size": "2048x2048",
        "response_format": "url",
        "watermark": False,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=180)
        data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("HTTPError:", e.code, e.read().decode("utf-8", "ignore")[:1500])
        continue
    except Exception as e:
        print("Error:", repr(e))
        continue

    img_url = None
    if isinstance(data, dict):
        for k in ("data", "images", "output", "result"):
            v = data.get(k)
            if isinstance(v, list) and v:
                first = v[0]
                if isinstance(first, dict):
                    img_url = first.get("url") or first.get("image_url") or first.get("b64_json")
                elif isinstance(first, str):
                    img_url = first
                if img_url:
                    break
            elif isinstance(v, dict):
                img_url = v.get("url") or v.get("image_url") or v.get("b64_json")
                if img_url:
                    break

    if not img_url:
        print("ERROR: 未提取到图片, 响应:", json.dumps(data, ensure_ascii=False)[:500])
        continue

    out_path = os.path.join(out_dir, name + ".png")
    if img_url.startswith("http"):
        req2 = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
        img_data = urllib.request.urlopen(req2, timeout=120).read()
        with open(out_path, "wb") as f:
            f.write(img_data)
        print("已保存:", out_path, "| 大小:", len(img_data))
    else:
        img_data = base64.b64decode(img_url)
        with open(out_path, "wb") as f:
            f.write(img_data)
        print("已保存(b64):", out_path, "| 大小:", len(img_data))
    time.sleep(2)

print("\n全部完成")
