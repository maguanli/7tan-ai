# -*- coding: utf-8 -*-
import os
print('ffmpeg E:', os.path.exists(r'E:\7tan_voice\ffmpeg\ffmpeg.exe'))
print('ffmpeg G:', os.path.exists(r'G:\ffmpeg\bin\ffmpeg.exe'))
print('piper onnx:', os.path.exists(r'E:\7tan_voice\piper\voices\zh_CN-huayan-medium.onnx'))
print('piper json:', os.path.exists(r'E:\7tan_voice\piper\voices\zh_CN-huayan-medium.onnx.json'))
print('OUTPUT_DIR E:', os.path.isdir(r'E:\7tan_voice\piper\output'))
