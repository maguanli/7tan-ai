import zipfile, os, sys
p = r'D:\7tan\7tanAI\dist\release\7tan-editor-v1.0.6.zip'
print('zip存在:', os.path.exists(p))
print('zip大小:', os.path.getsize(p) if os.path.exists(p) else '-')
z = zipfile.ZipFile(p)
n = z.namelist()
print('总文件数:', len(n))
tops = sorted(set(x.split('/')[0] for x in n))
print('顶层目录:', tops)
# 找构建相关文件
keys = ['build.spec','.bat','package_release','requirements','setup','readme_build','rebuild','.py']
build = [x for x in n if any(k.lower() in x.lower() for k in keys)]
print('=== 构建/脚本相关文件数:', len(build), '===')
for x in build[:60]:
    print(' ', x)
# 统计各顶层目录文件数
from collections import Counter
c = Counter(x.split('/')[0] for x in n)
print('=== 各顶层目录文件数 ===')
for k, v in sorted(c.items()):
    print(f'  {k}: {v}')
