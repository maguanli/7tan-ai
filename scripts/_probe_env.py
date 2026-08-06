# -*- coding: utf-8 -*-
"""探测环境：OCR/截图/鼠标库可用性"""
import importlib, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
for m in ['paddleocr','easyocr','pytesseract','PIL','mss','pyautogui','pygetwindow','win32gui','numpy','cv2']:
    try:
        importlib.import_module(m)
        print(m, 'OK')
    except Exception as e:
        print(m, 'NO', type(e).__name__, str(e)[:80])
