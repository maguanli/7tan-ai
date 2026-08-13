# -*- coding: utf-8 -*-
"""用 ctypes 写 Windows 剪贴板（带错误检查）"""
import ctypes
import sys

text = r"D:\7tan\7tanAI\dist\release\7tan-editor-v1.0.6.zip"

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 重试打开剪贴板
ok = False
for _ in range(5):
    if user32.OpenClipboard(0):
        ok = True
        break
    ctypes.windll.kernel32.Sleep(200)
if not ok:
    print('FAIL OpenClipboard, err=', ctypes.get_last_error())
    sys.exit(1)
print('OpenClipboard OK')

user32.EmptyClipboard()
data = (text + '\x00').encode('utf-16-le')
h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
if not h:
    print('FAIL GlobalAlloc, err=', ctypes.get_last_error())
    user32.CloseClipboard()
    sys.exit(1)
p = kernel32.GlobalLock(h)
if not p:
    print('FAIL GlobalLock, err=', ctypes.get_last_error())
    user32.CloseClipboard()
    sys.exit(1)
ctypes.memmove(p, data, len(data))
kernel32.GlobalUnlock(h)
res = user32.SetClipboardData(CF_UNICODETEXT, h)
if not res:
    print('FAIL SetClipboardData, err=', ctypes.get_last_error())
    user32.CloseClipboard()
    sys.exit(1)
user32.CloseClipboard()
print('OK clipboard set:', text)
