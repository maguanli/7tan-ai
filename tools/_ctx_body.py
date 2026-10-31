# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = json.load(open(r'D:\7tan\7tanAI\data\_995_export.json', encoding='utf-8'))
b = d['ll_baike_body']

for a, z, label in [
    (100, 400, '开头'),
    (560, 700, 'meta 里的发行日'),
    (880, 1000, '基础信息表'),
    (1150, 1300, '安装包/包体'),
    (1650, 1750, '资料边界'),
    (3050, 3180, '已知限制·更新滞后'),
    (5680, 5800, '词条尾'),
]:
    print('=' * 18, label, f'[{a}:{z}]')
    print(b[a:z])
    print()
