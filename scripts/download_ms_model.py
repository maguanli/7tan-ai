# -*- coding: utf-8 -*-
"""从魔搭下载 Anything V5 diffusers 格式模型"""
import sys, time
from modelscope import snapshot_download

t0 = time.time()
print("Start downloading stablediffusionapi/anything-v5 ...", flush=True)
path = snapshot_download(
    'stablediffusionapi/anything-v5',
    local_dir=r'D:\7tan\7tanAI\models\anything-v5-ms',
)
print("DONE in", round(time.time()-t0), "s ->", path, flush=True)
