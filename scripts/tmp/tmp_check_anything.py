# -*- coding: utf-8 -*-
"""检查本地 Anything V5 模型版本：读取 safetensors 元数据 + 目录信息"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')

def read_safetensors_meta(path):
    """读取 safetensors 文件头部 metadata"""
    try:
        with open(path, 'rb') as f:
            h = f.read(8)
            n = int.from_bytes(h[4:8], 'little')
            meta = json.loads(f.read(n).decode('utf-8'))
        md = meta.get('__metadata__', {})
        keys = [k for k in meta.keys() if k != '__metadata__']
        return {'tensor_count': len(keys), 'metadata': md}
    except Exception as e:
        return {'error': str(e)}

targets = [
    (r'D:\7tan\7tanAI\models\anything-v5\unet\diffusion_pytorch_model.safetensors', 'anything-v5 unet'),
    (r'D:\7tan\7tanAI\models\anything-v5-ms\unet\diffusion_pytorch_model.safetensors', 'anything-v5-ms unet'),
]

for path, label in targets:
    print('='*60)
    print(f'[{label}]')
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f'  文件: {path}')
        print(f'  大小: {size/1024/1024:.1f} MB')
        print(f'  MD5 : {__import__("hashlib").md5(open(path,"rb").read(1024*1024*8)).hexdigest()} (前8MB)')
        info = read_safetensors_meta(path)
        print(f'  tensor数: {info.get("tensor_count")}')
        print(f'  metadata: {json.dumps(info.get("metadata", {}), ensure_ascii=False)}')
    else:
        print('  文件不存在')

# 检查 G 盘单文件版
print('='*60)
print('[G盘单文件版检查]')
for root, dirs, files in os.walk(r'G:\AI_Video\stable-diffusion-webui\models'):
    for fn in files:
        low = fn.lower()
        if 'anything' in low or 'v5' in low or 'v3' in low:
            full = os.path.join(root, fn)
            print(f'  {full}  ({os.path.getsize(full)/1024/1024:.0f} MB)')
