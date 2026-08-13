# -*- coding: utf-8 -*-
"""用正确的 API Key 更新 doubao-seedream-5.0-pro 配置并测试 images API"""
import sys, os, json, sqlite3, urllib.request, base64, time, traceback

sys.path.insert(0, os.getcwd())
from src.database.db import encrypt_password, decrypt_password

DB = os.path.join("data", "games.db")
NEW_KEY = "ark-200c72f8-1b6f-4b16-8fae-9fcddb905182-72f87"  # 用户新建的 Key

conn = sqlite3.connect(DB)
row = conn.execute(
    "SELECT id, api_key, base_url, model FROM ai_configs WHERE config_key='doubao-seedream-5.0-pro'"
).fetchone()
if not row:
    print("ERROR: 未找到配置")
    sys.exit(1)
cid, old_enc, base_url, model = row

print("== 1. 旧 key 解密测试 ==")
old_plain = decrypt_password(old_enc)
print("旧 key 解密:", "成功 len=%d" % len(old_plain) if old_plain else "失败(空)")

print("== 2. 加密新 key 并更新数据库 ==")
new_enc = encrypt_password(NEW_KEY)
conn.execute("UPDATE ai_configs SET api_key=? WHERE id=?", (new_enc, cid))
conn.commit()
print("已更新 id=%d" % cid)

print("== 3. 读回并解密验证 ==")
enc2 = conn.execute("SELECT api_key FROM ai_configs WHERE id=?", (cid,)).fetchone()[0]
plain2 = decrypt_password(enc2)
print("解密成功:", plain2 == NEW_KEY, "| 前缀:", plain2[:10] + "..." if plain2 else "(空)")
print("模型:", model, "| base_url:", base_url)

print("== 4. 调用 images/generations 实测 ==")
url = base_url.rstrip("/") + "/images/generations"
body = {
    "model": model,
    "prompt": "极简扁平漫画风圆形头像LOGO，白色背景，一条黑色波浪曲线起伏，代表人生起落，曲线最高点站着张开双臂的小人剪影，谷底有一颗金色小星星，干净简约，无文字",
    "size": "1024x1024",
    "response_format": "url",
    "watermark": False,
}
req = urllib.request.Request(
    url,
    data=json.dumps(body).encode("utf-8"),
    headers={"Authorization": "Bearer " + plain2, "Content-Type": "application/json"},
)
try:
    resp = urllib.request.urlopen(req, timeout=180)
    data = json.loads(resp.read().decode("utf-8"))
    print("HTTP 200 OK, 响应 keys:", list(data.keys()) if isinstance(data, dict) else type(data))
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
    print("图片URL:", str(img_url)[:200] if img_url else "未提取到")
    # 下载图片
    if img_url and img_url.startswith("http"):
        import urllib.request as ur
        req2 = ur.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
        img_data = ur.urlopen(req2, timeout=60).read()
        out = os.path.join("data", "logo", "seedream_test.png")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(img_data)
        print("已保存:", out, len(img_data), "bytes")
except urllib.error.HTTPError as e:
    print("HTTPError:", e.code, e.read().decode("utf-8", "ignore")[:1500])
except Exception as e:
    print("Error:", repr(e))
    traceback.print_exc()
