# -*- coding: utf-8 -*-
"""批量用 Anything V5 生成第一章分镜图（后台运行，断点续跑）"""
import urllib.request, json, io, sys, time, base64, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

API = "http://127.0.0.1:7861/sdapi/v1/txt2img"
OUT_DIR = r"downloads\fanqie\video\frames_v2"
os.makedirs(OUT_DIR, exist_ok=True)
PROGRESS = os.path.join(OUT_DIR, "progress.txt")

NEG = ("lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, "
       "cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry")

SCENES = [
    ("01_coin_title", "close-up of an ancient bronze coin with glowing engravings, lying on dark night city street, bokeh city lights, mysterious atmosphere, anime style, masterpiece, best quality"),
    ("02_global_announcement", "night city street full of people, everyone looking at floating blue system panels above their heads, game UI elements, holographic screens, anime style, cinematic, masterpiece, best quality"),
    ("03_chenmo_panel", "lonely young chinese man in casual jacket standing on empty night street, no name tag above his head unlike others, dark moody atmosphere, anime style, detailed, masterpiece"),
    ("04_street_panic", "city street chaos, excited crowd with glowing magic effects, people running with superpowers, fireball and lightning sparks, night scene, anime style, dynamic, masterpiece"),
    ("05_tutorial_rules", "holographic game tutorial panel floating in night air, translucent blue interface with chinese text style symbols, dark street background, anime style, masterpiece"),
    ("06_huangmao_probe", "young man with dyed yellow spiky hair confronting another man on night street, suspicious expression, street lights, anime style, two shot, masterpiece, best quality"),
    ("07_hidden_npc_quest", "young man in dark coat showing game quest interface to a yellow-haired punk, glowing quest window, night street, mysterious, anime style, masterpiece"),
    ("08_life_deduct", "close-up of translucent game panel showing countdown numbers, glowing red warning interface on night street background, dramatic lighting, anime style, masterpiece"),
    ("09_landlady_knock", "angry middle-aged chinese woman banging on metal door at night, neighborhood corridor, dramatic shadows, anime style, dynamic, masterpiece"),
    ("10_guard_quest", "young man standing guard at building entrance at night, holding a flashlight, game quest notification floating beside him, residential corridor, anime style, masterpiece"),
    ("11_coin_announcement", "giant holographic bronze coin projection over night city skyline, people looking up in awe, game event announcement, anime style, epic, masterpiece"),
    ("12_huangmao_expose", "dramatic confrontation on night street, yellow-haired man pointing accusingly at stunned young man, tension, streetlights, anime style, cinematic, masterpiece"),
]

def log(msg):
    with open(PROGRESS, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    print(msg, flush=True)

def gen_one(name, prompt):
    payload = {
        "prompt": prompt,
        "negative_prompt": NEG,
        "steps": 15,
        "width": 512,
        "height": 768,
        "cfg_scale": 7,
        "sampler_name": "Euler a",
        "batch_size": 1,
    }
    t0 = time.time()
    req = urllib.request.Request(API, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=1800)
    data = json.loads(r.read())
    imgs = data.get("images", [])
    if not imgs:
        raise RuntimeError("no image returned")
    out = os.path.join(OUT_DIR, f"{name}.png")
    with open(out, "wb") as f:
        f.write(base64.b64decode(imgs[0]))
    log(f"OK {name} in {time.time()-t0:.0f}s -> {out}")

def main():
    done = 0
    for name, prompt in SCENES:
        out = os.path.join(OUT_DIR, f"{name}.png")
        if os.path.exists(out) and os.path.getsize(out) > 10000:
            log(f"SKIP {name} (exists)")
            done += 1
            continue
        for attempt in range(3):
            try:
                gen_one(name, prompt)
                done += 1
                break
            except Exception as e:
                log(f"FAIL {name} attempt{attempt+1}: {e}")
                time.sleep(5)
    log(f"ALL DONE {done}/{len(SCENES)}")

if __name__ == "__main__":
    main()
