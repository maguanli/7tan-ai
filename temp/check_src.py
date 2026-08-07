import zipfile, os
p = r'D:\7tan\7tanAI\dist\release\7tan-editor-v1.0.6.zip'
z = zipfile.ZipFile(p)
n = z.namelist()
# 只看 7tan-src 下所有文件
src = [x for x in n if x.startswith('7tan-src/')]
print('=== 7tan-src 全部', len(src), '个文件 ===')
for x in src:
    print(' ', x)
