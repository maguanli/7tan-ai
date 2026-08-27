# -*- coding: utf-8 -*-
"""v3 HTML: base64内嵌图片 + 校验三处修订点"""
import re, io, base64, os, sys
sys.stdout.reconfigure(encoding='utf-8')

SRC = r'D:\7tan\7tanAI\data\gzh_render\体检查出这5种病_v3.html'
html = io.open(SRC, encoding='utf-8').read()

# 1) 图片内嵌
def embed(m):
    path = m.group(1).replace('/', '\\')
    if not os.path.exists(path):
        print('!! 图片不存在:', path); return m.group(0)
    ext = os.path.splitext(path)[1].lower().lstrip('.')
    mime = 'jpeg' if ext in ('jpg','jpeg') else ext
    b64 = base64.b64encode(open(path,'rb').read()).decode()
    return 'src="data:image/%s;base64,%s"' % (mime, b64)

html2 = re.sub(r'src="(D:/[^"]+)"', embed, html)
n_embed = html2.count('data:image/')
n_ext   = len(re.findall(r'src="(?!data:image)', html2))
print('img总数:', html2.count('<img'), '| 内嵌:', n_embed, '| 外部引用:', n_ext)

# 2) 校验三处修订点
checks = {
    '①幽门螺杆菌例外': '不必执着"阳性就必须吃药"',
    '②范围声明(第二节)': '请不要把本文的经验直接套用到别的检查结果上',
    '②范围声明(文末)': '本文仅讨论上述5种常见体检异常',
    '③情绪句已收敛(图注)': '是否用药，以正规医院的诊断为准',
    '③"一片都嫌多"已删除': '一片都嫌多',
    '③CTA已收敛': '少一个人花冤枉钱',
}
for k, v in checks.items():
    found = v in html2
    if k == '③"一片都嫌多"已删除':
        print(('✅' if not found else '❌仍存在'), k)
    else:
        print(('✅' if found else '❌'), k)

# 3) 检查 ### 是否残留（上版瑕疵）
print('###残留:', html2.count('###'))

io.open(SRC, 'w', encoding='utf-8').write(html2)
print('大小:', len(html2.encode('utf-8')), 'bytes')
