# -*- coding: utf-8 -*-
"""验证 APK：图标更新 + onnx 未压缩 + 新 TtsManager 类"""
import zipfile, struct, os

apk = r'D:\7tan\iching-android\app\build\outputs\apk\debug\app-debug.apk'
print('APK:', apk, os.path.getsize(apk) / 1024 / 1024, 'MB')

z = zipfile.ZipFile(apk)
names = z.namelist()

# 1. onnx 是否被压缩（compress_type 0 = stored 未压缩）
for n in ['assets/tts/model.onnx', 'assets/tts/tokens.txt', 'assets/tts/lexicon.txt']:
    info = z.getinfo(n)
    print(f'{n}: size={info.file_size} stored={info.compress_type == 0}')

# 2. 图标是否更新（解出 xxxhdpi 图标，检查颜色构成）
icon = z.read('res/mipmap-xxxhdpi-v4/ic_launcher.png') if 'res/mipmap-xxxhdpi-v4/ic_launcher.png' in names else z.read('res/mipmap-xxxhdpi/ic_launcher.png')
from PIL import Image
import io
im = Image.open(io.BytesIO(icon)).convert('RGB')
colors = im.getcolors(maxcolors=1000000)
colors.sort(reverse=True)
print('图标尺寸:', im.size, '主色:', colors[:4])

# 3. 是否包含新 TtsManager（大小变化即可判断 class 已重编）
tts_class = [n for n in names if 'TtsManager' in n]
print('TtsManager 相关:', tts_class)
z.close()
