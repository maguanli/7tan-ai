# -*- coding: utf-8 -*-
"""下载 Anything V5 模型（ModelScope 国内源）"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from modelscope import snapshot_download

path = snapshot_download(
    'stablediffusionapi/anything-v5',
    local_dir=r'D:\7tan\7tanAI\models\anything-v5'
)
print('DOWNLOAD_OK:', path)
