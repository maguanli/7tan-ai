import sys, os, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

candidates = [
    r'C:\Program Files\Tencent\QQNT\QQ.exe',
    r'C:\Program Files (x86)\Tencent\QQNT\QQ.exe',
    r'C:\Program Files\Tencent\QQ\Bin\QQ.exe',
    r'C:\Program Files (x86)\Tencent\QQ\Bin\QQ.exe',
    r'C:\Program Files\Tencent\QQNT\resources\app\qq.exe',
]
# 也搜索桌面快捷方式
for pat in [r'C:\Users\*\Desktop\*.lnk', r'C:\Users\Public\Desktop\*.lnk']:
    for lnk in glob.glob(pat):
        if 'QQ' in os.path.basename(lnk):
            print('LNK:', lnk)

for c in candidates:
    if os.path.exists(c):
        print('FOUND:', c)
print('search done')
