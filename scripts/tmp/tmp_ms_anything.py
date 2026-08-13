# -*- coding: utf-8 -*-
"""拉取 ModelScope anything-v5 完整信息 + 解析文件列表"""
import sys, json, urllib.request
sys.stdout.reconfigure(encoding='utf-8')

url = 'https://modelscope.cn/api/v1/models/stablediffusionapi/anything-v5'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    data = json.loads(urllib.request.urlopen(req, timeout=30).read().decode('utf-8'))
    d = data.get('Data', {})
    print('模型名:', d.get('Name') or d.get('ChineseName'))
    print('路径:', d.get('Path') or d.get('ModelId') or d.get('Id'))
    print('下载量:', d.get('Downloads'))
    print('更新时间:', d.get('LastUpdatedTime'))
    print('License:', d.get('License'))
    print('标签:', d.get('Tags'))
    print('简介:', (d.get('Description') or '')[:500])
    print('='*60)
    # 文件列表
    infos = d.get('ModelInfos', {})
    files = []
    for k, v in infos.items():
        if isinstance(v, dict) and 'files' in v:
            for f in v['files']:
                files.append((k, f.get('name'), f.get('Size') or f.get('size')))
    for typ, name, size in files:
        print(f'  [{typ}] {name}  ({size})')
    if not files:
        print('  (ModelInfos 结构:', json.dumps(infos, ensure_ascii=False)[:800], ')')
except Exception as e:
    print('ERROR:', e)
