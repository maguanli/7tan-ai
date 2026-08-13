# -*- coding: utf-8 -*-
"""读取 G 盘 Anything V5 单文件版的 safetensors 元数据"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')

path = r'G:\AI_Video\stable-diffusion-webui\models\Stable-diffusion\AnythingV5V3_v5PrtRE.safetensors'

def read_safetensors_meta(path):
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

if os.path.exists(path):
    print(f'文件: {path}')
    print(f'大小: {os.path.getsize(path)/1024/1024:.0f} MB')
    info = read_safetensors_meta(path)
    print(f'tensor数: {info.get("tensor_count")}')
    print('metadata:')
    print(json.dumps(info.get('metadata', {}), ensure_ascii=False, indent=2))
else:
    print('文件不存在')
