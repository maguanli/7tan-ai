import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import traceback

try:
    import ctypes
    import ctypes.wintypes as wt

    u = ctypes.windll.user32

    def title(h):
        b = ctypes.create_unicode_buffer(512)
        u.GetWindowTextW(h, b, 512)
        return b.value

    def rect(h):
        r = wt.RECT()
        ok = u.GetWindowRect(h, ctypes.byref(r))
        return (r.left, r.top, r.right, r.bottom) if ok else None

    ids = [9175868, 984354, 7603556, 66960, 329388, 1901928, 722174]
    out = []
    for h in ids:
        out.append("{} | {} | {}".format(h, repr(title(h)), rect(h)))
    print("\n".join(out))
    print("screen:", u.GetSystemMetrics(0), "x", u.GetSystemMetrics(1))
except Exception:
    traceback.print_exc()
    sys.exit(1)
