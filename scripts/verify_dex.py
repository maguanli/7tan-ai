# -*- coding: utf-8 -*-
"""从 classes.dex 验证新 TtsManager 代码（新字符串标记）"""
import zipfile, re

apk = r'D:\7tan\iching-android\app\build\outputs\apk\debug\app-debug.apk'
z = zipfile.ZipFile(apk)
dex = z.read('classes.dex')
z.close()

# 新代码标记：copyAssetVerified 新错误消息 + 注释提到的修复
marks = {
    '新错误消息(复制内容为空)': '复制内容为空'.encode('utf-8'),
    '旧openFd消息(大小不一致)': '大小不一致'.encode('utf-8'),
    'TtsManager类名': b'TtsManager',
}
text = dex
for name, b in marks.items():
    print(name, ':', b in text)
