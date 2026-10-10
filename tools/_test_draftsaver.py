# -*- coding: utf-8 -*-
"""draft_saver 插件静态自测（不依赖重启、不点桌面）"""
import importlib.util
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
SRC = Path(r'D:\7tan\7tanAI\data\plugins\draft_saver\tools.py')
HTML = Path(r'D:\workspace\7tan_zhihu\crazyzoo\index_v3.html')

print('=' * 60)
print('1) 语法编译')
import py_compile
try:
    py_compile.compile(str(SRC), doraise=True)
    print('   ✅ py_compile 通过')
except Exception as e:
    print('   ❌ 编译失败:', e)
    raise SystemExit(1)

print('2) 模块加载 + 注册')
spec = importlib.util.spec_from_file_location('draft_saver_tools', SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('   ✅ 模块加载成功')

print('3) 平台档案（7 个 + URL 记档情况）')
txt = mod.draft_platforms()
print('   档案行数:', len(txt.splitlines()))
for line in txt.splitlines():
    if '编辑器URL' in line or line.startswith('──'):
        print('  ', line.strip())

print('4) CF_HTML 剪贴板往返')
inner = ('<p>测试<strong>加粗</strong></p>'
         '<figure><img src="a.png"><figcaption>图1｜示例</figcaption></figure>'
         '<figure><img src="b.png"><figcaption>图2｜示例</figcaption></figure>')
n, tn = mod._set_cf_html(inner, '测试纯文本')
back, plain = mod._get_cf_html()
print('   写入 %d 字节 / 纯文本 %d 字' % (n, tn))
print('   回读 fragment %d 字节  纯文本=%s' % (len(back), plain[:20]))
print('   ' + mod._fmt_stats(mod._stats_of(back)).replace('\n', '\n   '))

print('5) 静态核验目标文章')
if HTML.exists():
    print('   ' + mod.draft_verify_html(str(HTML)).replace('\n', '\n   '))
else:
    print('   ⚠️ 找不到', HTML)

print('6) prep_html remote / inline')
out_r = Path(r'D:\7tan\7tanAI\tools\_paste_test_remote.html')
out_i = Path(r'D:\7tan\7tanAI\tools\_paste_test_inline.html')
if HTML.exists():
    print('   ' + mod.draft_prep_html(str(HTML), 'remote', str(out_r)).replace('\n', '\n   '))
    print('   ' + mod.draft_prep_html(str(HTML), 'inline', str(out_i)).replace('\n', '\n   '))
    for f in (out_r, out_i):
        print('   %s -> %s 字节' % (f.name, f.stat().st_size if f.exists() else '缺失'))

print('7) 环境自检')
print('   ' + mod.draft_env_check().replace('\n', '\n   '))
