# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import winsdk.windows.media.ocr as o
print('OcrLine:', [a for a in dir(o.OcrLine) if not a.startswith('_')])
print('OcrWord:', [a for a in dir(o.OcrWord) if not a.startswith('_')])
print('OcrResult:', [a for a in dir(o.OcrResult) if not a.startswith('_')])
