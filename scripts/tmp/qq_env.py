import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
mods = ['pytesseract', 'easyocr', 'rapidocr_onnxruntime', 'paddleocr', 'cnocr', 'mss', 'PIL']
for m in mods:
    try:
        __import__(m)
        print(m, 'OK')
    except Exception as e:
        print(m, 'NO', type(e).__name__)
