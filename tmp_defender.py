import subprocess, sys, ctypes
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 是否管理员
is_admin = ctypes.windll.shell32.IsUserAnAdmin()
print('IS_ADMIN:', bool(is_admin))

# 尝试添加 Defender 排除
if is_admin:
    ps = r"Add-MpPreference -ExclusionPath 'D:\7tan\7tanAI' -ErrorAction Stop"
    r = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True)
    print('ADD_EXCL_STDOUT:', r.stdout[:500])
    print('ADD_EXCL_STDERR:', r.stderr[:500])
    r2 = subprocess.run(['powershell', '-NoProfile', '-Command', "Get-MpPreference | Select-Object -ExpandProperty ExclusionPath"], capture_output=True, text=True)
    print('EXCLUSIONS:', r2.stdout[:1000])
else:
    print('NOT_ADMIN - cannot add exclusion')
