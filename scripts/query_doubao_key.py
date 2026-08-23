# -*- coding: utf-8 -*-
"""查询数据库中 doubao-seedream 的 API Key 并测试是否有效"""
import sys, os, json, sqlite3, urllib.request, urllib.error

sys.path.insert(0, os.getcwd())
from src.database.db import decrypt_password

DB = os.path.join("data", "games.db")
conn = sqlite3.connect(DB)
rows = conn.execute(
    "SELECT config_key, api_key, base_url, model FROM ai_configs "
    "WHERE config_key LIKE '%doubao%' OR config_key LIKE '%seedream%' OR config_key LIKE '%ark%'"
).fetchall()
print("找到配置数:", len(rows))
for config_key, enc, base_url, model in rows:
    try:
        plain = decrypt_password(enc)
    except Exception as e:
        plain = None
    print("config:", config_key, "| base_url:", base_url, "| model:", model,
          "| key前缀:", (plain[:12] + "...") if plain else "解密失败")

# 取 seedream 配置测试
row = conn.execute(
    "SELECT api_key, base_url, model FROM ai_configs WHERE config_key='doubao-seedream-5.0-pro'"
).fetchone()
if not row:
    print("ERROR: 未找到 doubao-seedream-5.0-pro 配置")
    sys.exit(1)
enc, base_url, model = row
api_key = decrypt_password(enc)
if not api_key:
    print("ERROR: key 解密为空")
    sys.exit(1)

url = base_url.rstrip("/") + "/images/generations"
body = {
    "model": model,
    "prompt": "极简扁平漫画风圆形头像LOGO，白色背景，一条黑色波浪曲线起伏，无文字",
    "size": "1024x1024",
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
    print("HTTP 200 OK, 响应keys:", list(data.keys()) if isinstance(data, dict) else type(data))
    print("key有效:", api_key[:12] + "...")
except urllib.error.HTTPError as e:
    print("HTTPError:", e.code, e.read().decode("utf-8", "ignore")[:800])
except Exception as e:
    print("Error:", repr(e))
