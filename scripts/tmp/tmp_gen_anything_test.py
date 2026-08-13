# -*- coding: utf-8 -*-
"""用 diffusers 直接加载 Anything V5 (SD1.5 单文件) 生成测试图，CPU 模式"""
import os, time, torch

MODEL_PATH = r"G:\AI_Video\stable-diffusion-webui\models\Stable-diffusion\AnythingV5V3_v5PrtRE.safetensors"
OUT_DIR = r"D:\7tan\7tanAI\data\logo\anything"
os.makedirs(OUT_DIR, exist_ok=True)

# 复用本机已有的 HF 缓存（CLIP text encoder 等）
os.environ["HF_HOME"] = r"G:\AI_Video\stable-diffusion-webui\models\hf_cache"
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

t0 = time.time()
print("Loading model...", flush=True)
from diffusers import StableDiffusionPipeline

pipe = StableDiffusionPipeline.from_single_file(
    MODEL_PATH,
    torch_dtype=torch.float32,
    safety_checker=None,
    requires_safety_checker=False,
    local_files_only=False,
)
pipe.to("cpu")
pipe.enable_attention_slicing()
print(f"Model loaded in {time.time()-t0:.1f}s", flush=True)

prompt = ("masterpiece, best quality, anime style logo icon, minimalist flat design, "
          "a small cute chibi character standing on top of a mountain peak, "
          "waving a flag, orange sunset sky, low mountain and high mountain, "
          "winding path from bottom to top, birds flying, warm colors, "
          "simple clean white background, circular composition, vector logo, no text")

neg = ("lowres, bad anatomy, bad hands, missing fingers, extra digits, fewer digits, "
       "worst quality, low quality, normal quality, jpeg artifacts, signature, "
       "watermark, username, blurry, text, letters, words, logo text")

t1 = time.time()
gen = pipe(
    prompt=prompt,
    negative_prompt=neg,
    num_inference_steps=20,
    height=512, width=512,
    guidance_scale=7.5,
    generator=torch.Generator("cpu").manual_seed(42),
)
img = gen.images[0]
print(f"Generated in {time.time()-t1:.1f}s", flush=True)
out = os.path.join(OUT_DIR, "test_anything.png")
img.save(out)
print("SAVED:", out, flush=True)
