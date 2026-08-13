import re, sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

lnk = r'C:\Users\Administrator\Desktop\金融终端.lnk'
data = open(lnk, 'rb').read()
print('LNK size:', len(data))

# LNK 里通常包含目标路径字符串（ANSI/UTF-16）
# 找所有可打印 ASCII 路径
strs = re.findall(rb'[ -~]{6,}', data)
print('--- ASCII strings ---')
for s in strs:
    print(s.decode('ascii', 'ignore'))

# UTF-16LE 字符串（含中文的路径）
try:
    text16 = data.decode('utf-16-le', 'ignore')
    paths = re.findall(r'[A-Za-z]:\\\\[^\x00]{3,}', text16)
    if not paths:
        paths = re.findall(r'[A-Za-z]:\\[^\x00]{3,}', text16)
    print('--- UTF-16 paths ---')
    for p in set(paths):
        print(p)
except Exception as e:
    print('utf16 err', e)
