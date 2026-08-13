import win32gui, win32con, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

hwnd = 395876
print('activate', hwnd, repr(win32gui.GetWindowText(hwnd)))
try:
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    win32gui.SetForegroundWindow(hwnd)
    print('ACTIVATED')
except Exception as e:
    print('ACTIVATE_ERR:', e)
time.sleep(1.2)
print('done')
