# -*- coding: utf-8 -*-
import importlib.util
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
for m in ['rapidocr_onnxruntime', 'rapidocr', 'onnxruntime', 'winsdk']:
    print(f'{m}: {"OK" if importlib.util.find_spec(m) else "MISSING"}')
