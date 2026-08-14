# -*- coding: utf-8 -*-
import os, subprocess, base64, time

p = r"D:\用户目录\下载\新建文件夹 123\recording_20260814_030943.mkv"

def try_del():
    try:
        os.remove(p)
        return True, None
    except Exception as e:
        return False, e

# 1) 直接尝试删除
ok, err = try_del()
if ok:
    print("DELETED_OK")
else:
    print("DIRECT_DELETE_FAIL:", err)
    # 2) 通过 PowerShell -EncodedCommand 关闭目标文件夹窗口（避免中文乱码）
    ps = r'''
$shell = New-Object -ComObject Shell.Application
$n = 0
$shell.Windows() | ForEach-Object {
  $u = $_.LocationURL
  if ($u -like '*123*') { $_.Quit(); $n++ }
}
Write-Output ("closed=" + $n)
'''
    enc = base64.b64encode(ps.encode('utf-16-le')).decode('ascii')
    r = subprocess.run(['powershell', '-NoProfile', '-EncodedCommand', enc],
                       capture_output=True, text=True, timeout=30)
    print("CLOSE_WIN_RC:", r.returncode)
    print("CLOSE_WIN_OUT:", (r.stdout or '').strip()[-200:])
    print("CLOSE_WIN_ERR:", (r.stderr or '').strip()[-200:])
    time.sleep(1)
    # 3) 再尝试删除
    ok2, err2 = try_del()
    if ok2:
        print("DELETED_AFTER_CLOSE")
    else:
        print("STILL_FAIL:", err2)
