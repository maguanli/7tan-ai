# -*- coding: utf-8 -*-
"""只输出 deploy.json 的字段结构，不打印任何凭据值。"""
import json, os, sys

p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'deploy.json')
d = json.load(open(p, encoding='utf-8'))

def walk(o, prefix=''):
    if isinstance(o, dict):
        for k, v in o.items():
            walk(v, f'{prefix}.{k}' if prefix else k)
    elif isinstance(o, list):
        print(f'{prefix}  [list, len={len(o)}]')
    else:
        if o in ('', None):
            print(f'{prefix}  = <empty>')
        elif isinstance(o, str) and len(o) > 40:
            print(f'{prefix}  = <str len={len(o)}>')
        else:
            # 短字符串才可能是域名/用户名/端口，仍需掩码中间
            s = str(o)
            masked = s[:2] + '*' * max(1, len(s) - 4) + s[-2:] if len(s) > 4 else '*' * len(s)
            print(f'{prefix}  = {masked}')

walk(d)
print('--- top keys:', list(d.keys()))
