# -*- coding: utf-8 -*-
"""使用 Anything V5 动漫模型生成公众号 LOGO 候选（CPU 推理版）"""
import os, sys, time, gc
import torch
from PIL import Image

MODEL_PATH = r"D:\7tan\7tanAI\models\AnythingV5_PrtRE.safetensors"
OUT_DIR = r"D:\7tan\7tanAI\data\logo_anime"
os.makedirs(OUT_DIR, exist_ok=True)

PROMPTS = [
    {
        "name": "A_star_curve",
        "prompt": "minimalist flat vector logo icon, white background, a single elegant golden winding path curve from bottom-left valley rising to a peak on the right, tiny white chibi person standing on the peak raising both arms in joy, one small golden star at the valley, subtle sparkle dots, clean smooth lines, modern flat design, high quality, centered composition, no text, no letters, no watermark",
        "negative": "text, letters, words, watermark, signature, frame, border, complex background, photorealistic, 3d render, low quality, blurry, deformed, extra limbs",
    },
    {
        "name": "B_sunrise_peak",
        "prompt": "minimalist flat vector logo icon, warm sunrise gradient sky orange to soft yellow, two stylized mountain silhouettes left low right high, tiny white chibi person standing on the high peak waving, small red flag on the peak, flying birds, clean geometric flat design, cozy warm atmosphere, centered, no text, no letters, no watermark",
        "negative": "text, letters, words, watermark, signature, frame, border, photorealistic, 3d render, low quality, blurry, deformed, extra limbs",
    },
    {
        "name": "C_wave_rider",
        "prompt": "minimalist flat vector logo icon, white background, a smooth blue ocean wave curving upward, tiny chibi person surfing on the wave crest raising arm happily, golden star above, simple rounded shapes, clean modern flat design, fresh blue and orange color palette, centered composition, no text, no letters, no watermark",
        "negative": "text, letters, words, watermark, signature, frame, border, complex background, photorealistic, 3d render, low quality, blurry, deformed, extra limbs",
    },
]

def main():
    from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
    print("Loading model...", flush=True)
    t0 = time.time()
    pipe = StableDiffusionPipeline.from_single_file(
        MODEL_PATH,
        torch_dtype=torch.float32,
        safety_checker=None,
    )
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    # CPU 低内存：逐模块加载卸载，峰值内存可控
    try:
        pipe.enable_sequential_cpu_offload()
        print("sequential cpu offload enabled", flush=True)
    except Exception as e:
        print("offload skip:", e, flush=True)
    print(f"Model loaded in {time.time()-t0:.0f}s", flush=True)

    for i, cfg in enumerate(PROMPTS, 1):
        print(f"[{i}/{len(PROMPTS)}] generating {cfg['name']} ...", flush=True)
        t1 = time.time()
        img = pipe(
            prompt=cfg["prompt"],
            negative_prompt=cfg["negative"],
            height=512, width=512,
            num_inference_steps=24,
            guidance_scale=7.5,
            generator=torch.Generator().manual_seed(20260813 + i * 7),
        ).images[0]
        out = os.path.join(OUT_DIR, f"{cfg['name']}_512.png")
        img.save(out)
        # 360x360 头像版
        img.resize((360, 360), Image.LANCZOS).save(os.path.join(OUT_DIR, f"{cfg['name']}_360.png"))
        print(f"  saved {out} in {time.time()-t1:.0f}s", flush=True)
        del img
        gc.collect()

    # 生成预览页
    html = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>Anything V5 LOGO 候选</title>
<style>body{font-family:Microsoft YaHei;background:#f5f5f5;text-align:center;padding:30px}
h2{color:#333}.cards{display:flex;flex-wrap:wrap;justify-content:center;gap:30px}
.card{background:#fff;border-radius:16px;padding:20px;box-shadow:0 4px 16px rgba(0,0,0,.08)}
.circle{width:160px;height:160px;border-radius:50%;overflow:hidden;margin:0 auto;border:4px solid #eee;box-shadow:0 2px 8px rgba(0,0,0,.15)}
.circle img{width:100%;height:100%;object-fit:cover}
p{font-size:14px;color:#666}</style></head><body>
<h2>🎨 Anything V5 动漫 LOGO 候选（圆形头像预览）</h2>
<div class="cards">"""
    for cfg in PROMPTS:
        html += f"""<div class="card"><div class="circle"><img src="{cfg['name']}_360.png"></div><p>{cfg['name']}</p></div>"""
    html += "</div></body></html>"
    with open(os.path.join(OUT_DIR, "preview.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
