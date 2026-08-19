# -*- coding: utf-8 -*-
"""鐢ㄦ纭殑 API Key 鏇存柊 doubao-seedream-5.0-pro 閰嶇疆骞舵祴璇?images API"""
import sys, os, json, sqlite3, urllib.request, base64, time, traceback

sys.path.insert(0, os.getcwd())
from src.database.db import encrypt_password, decrypt_password

DB = os.path.join("data", "games.db")
NEW_KEY = "YOUR_API_KEY_HERE"  # 鐢ㄦ埛鏂板缓鐨?Key

conn = sqlite3.connect(DB)
row = conn.execute(
    "SELECT id, api_key, base_url, model FROM ai_configs WHERE config_key='doubao-seedream-5.0-pro'"
).fetchone()
if not row:
    print("ERROR: 鏈壘鍒伴厤缃?)
    sys.exit(1)
cid, old_enc, base_url, model = row

print("== 1. 鏃?key 瑙ｅ瘑娴嬭瘯 ==")
old_plain = decrypt_password(old_enc)
print("鏃?key 瑙ｅ瘑:", "鎴愬姛 len=%d" % len(old_plain) if old_plain else "澶辫触(绌?")

print("== 2. 鍔犲瘑鏂?key 骞舵洿鏂版暟鎹簱 ==")
new_enc = encrypt_password(NEW_KEY)
conn.execute("UPDATE ai_configs SET api_key=? WHERE id=?", (new_enc, cid))
conn.commit()
print("宸叉洿鏂?id=%d" % cid)

print("== 3. 璇诲洖骞惰В瀵嗛獙璇?==")
enc2 = conn.execute("SELECT api_key FROM ai_configs WHERE id=?", (cid,)).fetchone()[0]
plain2 = decrypt_password(enc2)
print("瑙ｅ瘑鎴愬姛:", plain2 == NEW_KEY, "| 鍓嶇紑:", plain2[:10] + "..." if plain2 else "(绌?")
print("妯″瀷:", model, "| base_url:", base_url)

print("== 4. 璋冪敤 images/generations 瀹炴祴 ==")
url = base_url.rstrip("/") + "/images/generations"
body = {
    "model": model,
    "prompt": "鏋佺畝鎵佸钩婕敾椋庡渾褰㈠ご鍍廘OGO锛岀櫧鑹茶儗鏅紝涓€鏉￠粦鑹叉尝娴洸绾胯捣浼忥紝浠ｈ〃浜虹敓璧疯惤锛屾洸绾挎渶楂樼偣绔欑潃寮犲紑鍙岃噦鐨勫皬浜哄壀褰憋紝璋峰簳鏈変竴棰楅噾鑹插皬鏄熸槦锛屽共鍑€绠€绾︼紝鏃犳枃瀛?,
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
    print("HTTP 200 OK, 鍝嶅簲 keys:", list(data.keys()) if isinstance(data, dict) else type(data))
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
    print("鍥剧墖URL:", str(img_url)[:200] if img_url else "鏈彁鍙栧埌")
    # 涓嬭浇鍥剧墖
    if img_url and img_url.startswith("http"):
        import urllib.request as ur
        req2 = ur.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
        img_data = ur.urlopen(req2, timeout=60).read()
        out = os.path.join("data", "logo", "seedream_test.png")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(img_data)
        print("宸蹭繚瀛?", out, len(img_data), "bytes")
except urllib.error.HTTPError as e:
    print("HTTPError:", e.code, e.read().decode("utf-8", "ignore")[:1500])
except Exception as e:
    print("Error:", repr(e))
    traceback.print_exc()

