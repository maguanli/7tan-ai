# -*- coding: utf-8 -*-
"""调用豆包 doubao-seedream-5.0-pro 生成公众号 LOGO（漫画风+简约）"""
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

PROMPT = (
    "极简漫画风格公众号头像LOGO，主题'大起大落的一生'："
    "一条黑色流畅的波浪线从左下角向右上角起伏延伸，象征人生的起伏跌宕；"
    "波浪最高处站着一个小小的人物剪影，张开双臂，象征人生巅峰；"
    "波浪最低处有一颗小小的星星点缀，象征低谷中的希望；"
    "纯白背景，只使用黑色线条配少量红色或金色点缀，"
    "扁平化矢量插画风格，留白充足，干净简约，无任何文字，"
    "圆形构图适合社交头像小尺寸显示，设计感强，高级感"
)

url = base_url.rstrip("/") + "/images/generations"
body = {
    "model": model,
    "prompt": PROMPT,
    "size": "2048x2048",
    "response_format": "url",
    "watermark": False,
}

req = urllib.request.Request(
    url,
    data=json.dumps(body).encode("utf-8"),
    headers={
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    },
)

try:
    resp = urllib.request.urlopen(req, timeout=180)
    data = json.loads(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print("HTTPError:", e.code, e.read().decode("utf-8", "ignore")[:1500])
    sys.exit(1)
except Exception as e:
    print("Error:", repr(e))
    sys.exit(1)

print("响应 keys:", list(data.keys()) if isinstance(data, dict) else type(data))
print(json.dumps(data, ensure_ascii=False)[:3000])

# 提取图片
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
    print("ERROR: 未从响应中提取到图片")
    sys.exit(1)

out_dir = os.path.join("data", "logo")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "logo_dqdyl_seedream.png")

if img_url.startswith("http"):
    req2 = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
    img_data = urllib.request.urlopen(req2, timeout=120).read()
    with open(out_path, "wb") as f:
        f.write(img_data)
    print("已保存:", out_path, "| 大小:", len(img_data))
else:
    # b64_json
    img_data = base64.b64decode(img_url)
    with open(out_path, "wb") as f:
        f.write(img_data)
    print("已保存(b64):", out_path, "| 大小:", len(img_data))
