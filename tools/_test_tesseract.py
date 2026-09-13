# -*- coding: utf-8 -*-
"""检查 tesseract 可用性并用它识别截图，对比 OCR 质量"""
import subprocess, sys

# 1. 检查 tesseract.exe
try:
    r = subprocess.run(["tesseract", "--version"], capture_output=True, text=True, timeout=15)
    print("=== tesseract 版本 ===")
    print(r.stdout.splitlines()[0] if r.stdout else r.stderr.splitlines()[0])
except FileNotFoundError:
    print("tesseract.exe 未安装或不在 PATH")
    sys.exit(0)
except Exception as e:
    print("检查 tesseract 异常:", e)
    sys.exit(0)

# 2. 检查语言包
try:
    r = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=15)
    print("=== 语言包 ===")
    print(r.stdout or r.stderr)
except Exception as e:
    print("语言列表失败:", e)

# 3. 用 pytesseract 识别刚才的截图
try:
    import pytesseract
    from PIL import Image
    img = Image.open(r"D:\7tan\7tanAI\data\screenshots\wechat_status_1.png")
    # 放大 2 倍提高小字识别率
    img2 = img.resize((img.width*2, img.height*2), Image.LANCZOS)
    print("=== pytesseract 中文识别（放大2倍）===")
    txt = pytesseract.image_to_string(img2, lang="chi_sim")
    print(txt[:1500])
except Exception as e:
    print("pytesseract 识别失败:", e)
