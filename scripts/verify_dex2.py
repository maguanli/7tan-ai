# -*- coding: utf-8 -*-
import zipfile

apk = r'D:\7tan\iching-android\app\build\outputs\apk\debug\app-debug.apk'
z = zipfile.ZipFile(apk)
dex_names = [n for n in z.namelist() if n.endswith('.dex')]
print('dex 文件:', dex_names)

marks = [('TtsManager', b'TtsManager'),
         ('复制内容为空', '复制内容为空'.encode('utf-8'))]
for dn in dex_names:
    data = z.read(dn)
    for name, b in marks:
        if b in data:
            print(f'[{dn}] 找到标记: {name}')
print('done')
