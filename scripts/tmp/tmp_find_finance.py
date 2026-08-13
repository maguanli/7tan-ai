import os, sys, winreg
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

out = []
roots = [
    Path(os.environ.get('ProgramData', 'C:/ProgramData')) / 'Microsoft/Windows/Start Menu/Programs',
    Path('C:/Users/Public/Desktop'),
]
try:
    for u in Path('C:/Users').iterdir():
        if u.is_dir():
            roots.append(u / 'Desktop')
except Exception:
    pass

kw = ['广发', 'gf', '证券', 'guangfa', 'gft', '金融终端', '易淘金']
for r in roots:
    if not r.exists():
        continue
    try:
        for f in r.rglob('*.lnk'):
            low = f.name.lower()
            if any(k.lower() in low for k in kw):
                out.append('LNK: ' + str(f))
    except Exception:
        pass

print('=== LNK MATCH ===')
for x in out:
    print(x)
print('total:', len(out))

print()
print('=== GF DIRS ===')
for root in ['C:/Program Files', 'C:/Program Files (x86)', 'D:/', 'C:/']:
    p = Path(root)
    if not p.exists():
        continue
    try:
        for d in p.iterdir():
            n = d.name.lower()
            if any(k in n for k in ['gf', 'guangfa', '广发', 'gft', 'trade', 'secur', 'easytrader']):
                print(d)
    except Exception:
        pass

print()
print('=== REGISTRY 广发/GF ===')
def scan(key):
    try:
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key)
        for i in range(winreg.QueryInfoKey(k)[0]):
            try:
                sub = winreg.EnumKey(k, i)
                try:
                    sk = winreg.OpenKey(k, sub)
                    try:
                        dn, _ = winreg.QueryValueEx(sk, 'DisplayName')
                        if dn and ('广发' in dn or 'gf' in dn.lower()):
                            print('NAME:', dn)
                            try:
                                ul, _ = winreg.QueryValueEx(sk, 'UninstallString')
                                print('  UNINSTALL:', ul)
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    pass
            except Exception:
                pass
    except Exception:
        pass

scan(r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall')
scan(r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall')
print('=== DONE ===')
