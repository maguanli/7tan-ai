# -*- coding: utf-8 -*-
import zipfile, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
zpath = r'D:\7tan\7tanAI\dist\release\7tan-web-v1.0.12.zip'
z = zipfile.ZipFile(zpath)
items = z.infolist()
print('总文件数:', len(items))
for i in items[:80]:
    print(i.filename, i.file_size)
