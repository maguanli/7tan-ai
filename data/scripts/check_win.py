import psutil, ctypes, time

def get_window_title(pid):
    titles = []
    try:
        import win32gui
        def cb(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                tid = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)
                # 用 win32process 拿 pid
                try:
                    import win32process
                    _, wpid = win32process.GetWindowThreadProcessId(hwnd)
                except Exception:
                    wpid = None
                if wpid == pid:
                    t = win32gui.GetWindowText(hwnd)
                    if t:
                        titles.append((hwnd, t))
        win32gui.EnumWindows(cb, None)
    except Exception as e:
        return [f"win32gui err: {e}"]
    return titles

for pid in [4252, 10964]:
    try:
        p = psutil.Process(pid)
        print(f"=== PID {pid} ===")
        print(f"  name={p.name()} create={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(p.create_time()))}")
        print(f"  cmd={' '.join(p.cmdline())[:200]}")
        print(f"  status={p.status()} cwd={p.cwd()}")
        wins = get_window_title(pid)
        print(f"  windows: {wins if wins else '(none)'}")
    except Exception as e:
        print(f"PID {pid}: {e}")
    print()
