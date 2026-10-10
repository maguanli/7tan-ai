import ctypes
u = ctypes.windll.user32
k = ctypes.windll.kernel32
u.OpenClipboard(0)
fmts = []
f = 0
while True:
    f = u.EnumClipboardFormats(f)
    if f == 0:
        break
    buf = ctypes.create_unicode_buffer(256)
    u.GetClipboardFormatNameW(f, buf, 256)
    fmts.append((f, buf.value))
print('FORMATS:', fmts)
for f, name in fmts:
    if name in ('HTML Format', 'text/html'):
        h = u.GetClipboardData(f)
        print(name, 'bytes:', k.GlobalSize(h))
CF_UNICODETEXT = 13
h = u.GetClipboardData(CF_UNICODETEXT)
if h:
    p = k.GlobalLock(h)
    s = ctypes.c_wchar_p(p).value
    print('TEXT_LEN:', len(s) if s else 0)
    print('TEXT_HEAD:', (s or '')[:80])
    k.GlobalUnlock(h)
u.CloseClipboard()
