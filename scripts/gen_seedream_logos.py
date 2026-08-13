# -*- coding: utf-8 -*-
"""用 Seedream 5.0 Pro 生成 3 张公众号 LOGO 候选（从数据库读 Key）"""
import sys, os, json, sqlite3, urllib.request, time, traceback

sys.path.insert(0, os.getcwd())
from src.database.db import decrypt_password

DB = os.path.join("data", "games.db")
OUT_DIR = os.path.join("data", "logo")
os.makedirs(OUT_DIR, exist_ok=True)

conn = sqlite3.connect(DB)
row = conn.execute(
    "SELECT api_key, base_url, model FROM ai_configs WHERE config_key='doubao-seedream-5.0-pro'"
).fetchone()
if not row:
    print("ERROR: 未找到 doubao 配置")
    sys.exit(1)
api_key = decrypt_password(row[0])
base_url, model = row[1], row[2]
print("模型:", model, "| Key 前缀:", api_key[:12] + "...")

PROMPTS = [
    {
        "name": "candidate_1_golden_curve",
        "prompt": (
            "Minimalist premium app icon logo, square with rounded corners, deep navy blue gradient background. "
            "A single smooth flowing golden curve rises from the bottom-left valley to the top-right peak, "
            "like a life journey of ups and downs. Small elegant white minimalist human silhouette stands "
            "at the peak with arms wide open triumphantly. A small warm glowing golden star sits at the valley "
            "bottom symbolizing hope. A few tiny soft stars in the dark sky. Clean flat vector style, soft glow, "
            "professional logo design, no text, no letters, balanced composition, beautiful and simple."
        ),
    },
    {
        "name": "candidate_2_sunrise_peak",
        "prompt": (
            "Minimalist flat design app icon logo, square with rounded corners, warm orange to soft cream gradient "
            "background like sunrise. A low hill on the left and a tall mountain peak on the right, connected by "
            "an elegant winding path. A small cute cartoon person stands on the tall peak waving a tiny red flag, "
            "celebrating success. A small orange circle (sun) rising behind the peak. Two small birds in the sky. "
            "Clean simple comic style, rounded shapes, no text, no letters, cheerful and inspiring, professional logo."
        ),
    },
    {
        "name": "candidate_3_wave_rise",
        "prompt": (
            "Minimalist modern app icon logo, square with rounded corners, clean white background with soft blue "
            "gradient ocean wave at the bottom. A single bold smooth blue wave curve rises high like a roller "
            "coaster, a small happy cartoon character riding on top of the wave peak with arms raised. "
            "A tiny golden star above. Flat comic style, thick clean lines, generous white space, "
            "no text, no letters, fresh and simple, professional logo design."
        ),
    },
]

def gen_one(name, prompt):
    url = base_url.rstrip("/") + "/images/generations"
    body = {
        "model": model,
        "prompt": prompt,
        "size": "1024x1024",
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
        img_url = None
        if isinstance(data, dict) and data.get("data"):
            first = data["data"][0]
            img_url = first.get("url") if isinstance(first, dict) else first
        if not img_url:
            print(f"[{name}] 未提取到图片URL: {str(data)[:300]}")
            return False
        req2 = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
        img_data = urllib.request.urlopen(req2, timeout=60).read()
        out = os.path.join(OUT_DIR, name + ".png")
        with open(out, "wb") as f:
            f.write(img_data)
        print(f"[{name}] OK -> {out} ({len(img_data)} bytes)")
        return True
    except urllib.error.HTTPError as e:
        print(f"[{name}] HTTPError:", e.code, e.read().decode("utf-8", "ignore")[:800])
        return False
    except Exception as e:
        print(f"[{name}] Error:", repr(e))
        return False

ok = 0
for p in PROMPTS:
    if gen_one(p["name"], p["prompt"]):
        ok += 1
    time.sleep(2)

print(f"\n完成: {ok}/{len(PROMPTS)} 张生成成功")
