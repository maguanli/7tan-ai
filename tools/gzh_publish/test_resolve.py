# -*- coding: utf-8 -*-
"""gzh_do.py resolve() 三级定位逻辑单元测试"""
import importlib.util
import io
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

spec = importlib.util.spec_from_file_location('gzh_do', r'tools\gzh_publish\gzh_do.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Args:
    def __init__(self, dynamic='on', **kw):
        self.dynamic = dynamic
        self.title_pos = kw.get('title_pos', m.DEFAULTS['title_pos'])
        self.draft_pos = kw.get('draft_pos', m.DEFAULTS['draft_pos'])
        self.publish_confirm_pos = kw.get('publish_confirm_pos', m.DEFAULTS['publish_confirm_pos'])
        self.upload_pos = kw.get('upload_pos', m.DEFAULTS['upload_pos'])
        self.cover_pos = kw.get('cover_pos', m.DEFAULTS['cover_pos'])


results = []

# 1. 默认参数 + 动态on，OCR未命中 → default 兜底
a = Args()
pos, src = m.resolve(a, 'title')
ok = src == 'default' and pos == (460, 420)
results.append(('1.默认+OCR未命中→default兜底', ok, pos, src))

# 2. 显式坐标≠默认 → explicit 优先
a2 = Args(title_pos='500,500')
pos, src = m.resolve(a2, 'title')
results.append(('2.显式坐标→explicit', src == 'explicit' and pos == (500, 500), pos, src))

# 3. dynamic off + 默认 → 纯坐标 default
a3 = Args(dynamic='off')
pos, src = m.resolve(a3, 'title')
results.append(('3.off模式→default', src == 'default' and pos == (460, 420), pos, src))

# 4. dynamic off + 显式 → explicit
a4 = Args(dynamic='off', title_pos='300,300')
pos, src = m.resolve(a4, 'title')
results.append(('4.off+显式→explicit', src == 'explicit' and pos == (300, 300), pos, src))

# 5. mock OCR 命中 → ocr[文字]
orig = m._find_text
m._find_text = lambda kw, lines=None: (888, 666, kw[0]) if kw else None
a5 = Args()
pos, src = m.resolve(a5, 'title')
results.append(('5.OCR命中→ocr[文本]', src == 'ocr[请在这里输入标题]' and pos == (888, 666), pos, src))

# 6. mock OCR命中 + 显式坐标 → 显式优先
a6 = Args(title_pos='500,500')
pos, src = m.resolve(a6, 'title')
results.append(('6.OCR+显式→显式优先', src == 'explicit' and pos == (500, 500), pos, src))

# 7. publish_confirm 映射 confirm 关键词（OCR未命中→default）
m._find_text = orig
a7 = Args()
pos, src = m.resolve(a7, 'publish_confirm', kw='confirm')
results.append(('7.confirm键映射', src == 'default' and pos == (458, 456), pos, src))

# 8. parse_pos 容错
p1 = m.parse_pos('1,2', '3,4')
p2 = m.parse_pos('', '3,4')
results.append(('8.parse_pos容错', p1 == (1, 2) and p2 == (3, 4), (p1, p2), ''))

# 9. KEYWORDS 覆盖所有动作
need = ['title', 'author', 'body', 'digest', 'cover', 'upload', 'original', 'draft', 'publish', 'confirm']
missing = [k for k in need if k not in m.KEYWORDS]
results.append(('9.KEYWORDS完整性', not missing, missing, ''))

print('=' * 60)
all_ok = True
for name, ok, detail, src in results:
    all_ok = all_ok and ok
    print(f'{"✅ PASS" if ok else "❌ FAIL"}  {name}  {detail} [{src}]')
print('=' * 60)
print('总体:', 'ALL PASS ✅' if all_ok else '有失败 ❌')
sys.exit(0 if all_ok else 1)
