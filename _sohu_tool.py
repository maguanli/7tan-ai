# -*- coding: utf-8 -*-
"""临时工具：把《迷你世界》测评灌进搜狐号编辑器（只存草稿）。

用法：
  python _sohu_tool.py build              # 解析 article.md -> _sohu_blocks.json
  python _sohu_tool.py focus              # 把"搜狐号"窗口置前并回报前台窗口
  python _sohu_tool.py title              # 填标题
  python _sohu_tool.py clear              # 点正文区并清空
  python _sohu_tool.py run <from> <to>    # 灌第 from..to-1 块（图文交替）
  python _sohu_tool.py save               # 点存稿（需人工确认后才用）
"""
import ctypes
import json
import os
import re
import sys
import time

ROOT = r"D:\7tan\7tanAI"
ART = r"D:\workspace\7tan_zhihu\miniworld"
BLOCKS = os.path.join(ROOT, "_sohu_blocks.json")
LOG = os.path.join(ROOT, "_sohu_progress.log")

TITLE = "《迷你世界》测评:半小时体验,内容量堆得满"
WIN_KEY = "搜狐号"
TITLE_POS = (555, 324)
BODY_POS = (700, 420)
SAVE_POS = (857, 1004)

TEXT_WAIT = 1.8
IMG_WAIT = 13.0

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


# ---------------- clipboard ----------------
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class DROPFILES(ctypes.Structure):
    _fields_ = [("pFiles", ctypes.c_uint32), ("pt", POINT),
                ("fNC", ctypes.c_int), ("fWide", ctypes.c_int)]


def _alloc(data):
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint32, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    user32.SetClipboardData.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    h = kernel32.GlobalAlloc(0x0042, len(data))
    p = kernel32.GlobalLock(h)
    ctypes.memmove(p, data, len(data))
    kernel32.GlobalUnlock(h)
    return h


def _open_clip():
    for _ in range(30):
        if user32.OpenClipboard(None):
            return True
        time.sleep(0.1)
    raise RuntimeError("无法打开剪贴板")


def set_clip(kind, payload):
    _open_clip()
    try:
        user32.EmptyClipboard()
        if kind == "text":
            user32.SetClipboardData(13, _alloc(payload.encode("utf-16-le") + b"\x00\x00"))
        elif kind == "html":
            fmt = user32.RegisterClipboardFormatW("HTML Format")
            tpl = ("Version:0.9\r\nStartHTML:{sh:010d}\r\nEndHTML:{eh:010d}\r\n"
                   "StartFragment:{sf:010d}\r\nEndFragment:{ef:010d}\r\n")
            sh = len(tpl.format(sh=0, eh=0, sf=0, ef=0).encode("utf-8"))
            pre = b"<html><body>\r\n<!--StartFragment-->"
            post = b"<!--EndFragment-->\r\n</body></html>\r\n"
            frag = payload.encode("utf-8")
            sf = sh + len(pre)
            ef = sf + len(frag)
            eh = ef + len(post)
            data = tpl.format(sh=sh, eh=eh, sf=sf, ef=ef).encode("utf-8") + pre + frag + post + b"\x00"
            user32.SetClipboardData(fmt, _alloc(data))
            plain = re.sub(r"<[^<>]+>", "", payload)
            user32.SetClipboardData(13, _alloc(plain.encode("utf-16-le") + b"\x00\x00"))
        elif kind == "hdrop":
            files = "\0".join(os.path.abspath(p) for p in payload) + "\0\0"
            df = DROPFILES()
            df.pFiles = ctypes.sizeof(DROPFILES)
            df.fWide = 1
            data = bytes(df) + files.encode("utf-16-le")
            user32.SetClipboardData(15, _alloc(data))
            fmt = user32.RegisterClipboardFormatW("Preferred DropEffect")
            user32.SetClipboardData(fmt, _alloc((1).to_bytes(4, "little")))
    finally:
        user32.CloseClipboard()


# ---------------- window ----------------
def find_windows(sub):
    import win32gui
    res = []

    def cb(h, _):
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            if sub in t:
                res.append((h, t))

    win32gui.EnumWindows(cb, None)
    return res


def ensure_tab():
    import win32gui
    import pyautogui
    for _ in range(15):
        if WIN_KEY in win32gui.GetWindowText(win32gui.GetForegroundWindow()):
            return True
        pyautogui.hotkey("ctrl", "tab")
        time.sleep(0.7)
    return False


def focus():
    import win32gui
    import pyautogui
    ws = find_windows("Google Chrome")
    if not ws:
        raise RuntimeError("找不到 Chrome 窗口")
    hwnd, t = ws[0]
    win32gui.ShowWindow(hwnd, 9)
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(0.5)
    fg = win32gui.GetWindowText(win32gui.GetForegroundWindow())
    if WIN_KEY not in fg:
        log("当前标签页是「%s」，正在切回搜狐号标签…" % fg)
        if not ensure_tab():
            raise RuntimeError("切不回搜狐号标签，中止")
        time.sleep(0.6)
        fg = win32gui.GetWindowText(win32gui.GetForegroundWindow())
    if WIN_KEY not in fg:
        raise RuntimeError("前台窗口是「%s」，不含「%s」，中止" % (fg, WIN_KEY))
    return fg


def log(msg):
    line = "%s  %s" % (time.strftime("%H:%M:%S"), msg)
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------------- markdown ----------------
def esc(s):
    parts = re.split(r"(<[^<>]+>)", s)
    out = []
    for p in parts:
        if p.startswith("<") and p.endswith(">"):
            out.append(p)
        else:
            out.append(p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    return "".join(out)


def inline(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return esc(s)


def chunk_html(html, limit=1100):
    """按段落边界切成 <=limit 字的小块"""
    blocks = re.findall(r"<(h2|p|blockquote)>.*?</\1>", html)
    if not blocks:
        return [html]
    parts = re.findall(r"<(?:h2|p|blockquote)>.*?</(?:h2|p|blockquote)>", html)
    out, cur, n = [], "", 0
    for p in parts:
        ln = len(re.sub(r"<[^<>]+>", "", p))
        if n and n + ln > limit:
            out.append(cur)
            cur, n = "", 0
        cur += p
        n += ln
    if cur:
        out.append(cur)
    return out


def build():
    md = open(os.path.join(ART, "article.md"), encoding="utf-8").read()
    lines = md.split("\n")
    blocks = []
    buf = []

    def flush():
        if not buf:
            return
        txt = "\n".join(buf).strip()
        buf.clear()
        if not txt:
            return
        chunks = []
        cur = []

        def flush_cur():
            if cur:
                h = ""
                i = 0
                while i < len(cur):
                    ln = cur[i]
                    if ln.startswith("## "):
                        h += "<h2>%s</h2>" % inline(ln[3:].strip())
                        i += 1
                    elif ln.startswith("> "):
                        q = []
                        while i < len(cur) and cur[i].startswith("> "):
                            q.append(inline(cur[i][2:].strip()))
                            i += 1
                        h += "<blockquote>%s</blockquote>" % "<br>".join(q)
                    else:
                        p = []
                        while i < len(cur) and not cur[i].startswith(("## ", "> ")):
                            if cur[i].strip():
                                p.append(inline(cur[i].strip()))
                            i += 1
                        h += "<p>%s</p>" % "<br>".join(p)
                chunks.append(h)
                cur.clear()

        for ln in txt.split("\n"):
            cur.append(ln)
        flush_cur()
        for c in chunks:
            for piece in chunk_html(c):
                blocks.append({"t": "text", "html": piece})

    i = 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r"^!\[(.*?)\]\((.*?)\)\s*$", ln.strip())
        if ln.startswith("# "):
            i += 1
            continue
        if m:
            flush()
            cap, path = m.group(1), m.group(2)
            blocks.append({"t": "img", "path": os.path.join(ART, path.replace("/", os.sep))})
            if cap:
                blocks.append({"t": "text", "html": "<p>%s</p>" % inline(cap)})
            i += 1
            continue
        if ln.strip() == "---":
            i += 1
            continue
        buf.append(ln)
        i += 1
    flush()

    # 论坛用语 -> 搜狐用语
    for b in blocks:
        if b["t"] == "text":
            b["html"] = (b["html"]
                         .replace("回个帖说说你的看法", "在评论区说说你的看法")
                         .replace("回帖聊聊", "评论区聊聊"))
    json.dump(blocks, open(BLOCKS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ni = sum(1 for b in blocks if b["t"] == "img")
    nt = len(blocks) - ni
    print("blocks=%d  text=%d  img=%d" % (len(blocks), nt, ni))
    for idx, b in enumerate(blocks):
        if b["t"] == "img":
            print("  %2d IMG  %s" % (idx, os.path.basename(b["path"])))
        else:
            plain = re.sub(r"<[^<>]+>", "", b["html"])
            print("  %2d TXT  %s" % (idx, plain[:34]))


# ---------------- actions ----------------
def load_blocks():
    return json.load(open(BLOCKS, encoding="utf-8"))


def paste(kind, payload):
    import pyautogui
    set_clip(kind, payload)
    time.sleep(0.35)
    pyautogui.hotkey("ctrl", "v")


def do_title():
    import pyautogui
    focus()
    pyautogui.click(*TITLE_POS)
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.2)
    pyautogui.press("delete")
    time.sleep(0.3)
    paste("text", TITLE)
    time.sleep(1.2)
    log("填标题完成: %s" % TITLE)


def do_clear():
    import pyautogui
    focus()
    pyautogui.click(*BODY_POS)
    time.sleep(0.6)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.3)
    pyautogui.press("delete")
    time.sleep(0.4)
    log("正文区已点入并清空")


def do_run(a, b):
    blocks = load_blocks()
    focus()
    log(">>> run %d..%d" % (a, b - 1))
    for idx in range(a, b):
        blk = blocks[idx]
        fg = focus() if idx % 6 == 0 else None
        if blk["t"] == "text":
            plain = re.sub(r"<[^<>]+>", "", blk["html"])
            paste("html", blk["html"])
            time.sleep(TEXT_WAIT)
            log("  [%2d] TXT  %d字  %s" % (idx, len(plain), plain[:28]))
        else:
            p = blk["path"]
            if not os.path.exists(p):
                log("  [%2d] IMG  缺失 %s" % (idx, p))
                continue
            paste("hdrop", [p])
            time.sleep(IMG_WAIT)
            log("  [%2d] IMG  %s (%dKB)" % (idx, os.path.basename(p), os.path.getsize(p) // 1024))
    log("<<< done %d..%d" % (a, b - 1))


def do_readback():
    import pyautogui
    import win32clipboard
    focus()
    pyautogui.click(*BODY_POS)
    time.sleep(0.6)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(1.0)
    pyautogui.hotkey("ctrl", "c")
    time.sleep(2.0)
    html, txt = "", ""
    for _ in range(20):
        try:
            win32clipboard.OpenClipboard()
            break
        except Exception:
            time.sleep(0.2)
    try:
        fmt = win32clipboard.RegisterClipboardFormat("HTML Format")
        if win32clipboard.IsClipboardFormatAvailable(fmt):
            html = win32clipboard.GetClipboardData(fmt)
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            txt = win32clipboard.GetClipboardData()
    finally:
        win32clipboard.CloseClipboard()
    if isinstance(html, bytes):
        html = html.decode("utf-8", "ignore")
    if isinstance(txt, bytes):
        txt = txt.decode("utf-16-le", "ignore")
    open(os.path.join(ROOT, "_sohu_readback.html"), "w", encoding="utf-8").write(html)
    open(os.path.join(ROOT, "_sohu_readback.txt"), "w", encoding="utf-8").write(txt)
    import re as _re
    imgs = _re.findall(r"<img[^>]+src=[\"']([^\"']+)[\"']", html)
    print("html_len=%d txt_len=%d img=%d" % (len(html), len(txt), len(imgs)))
    print("img src:")
    for u in imgs:
        print("   ", u[:90])
    print("sohu_res=%d  blob=%d  data=%d  http_other=%d" % (
        sum("res.mp.sohu.com" in u for u in imgs),
        sum(u.startswith("blob:") for u in imgs),
        sum(u.startswith("data:") for u in imgs),
        sum(u.startswith("http") and "res.mp.sohu.com" not in u for u in imgs)))
    pyautogui.press("end")


IMG10 = os.path.join(ART, "images", "img10.jpg")
CAP10 = "<p>图10:星座祈愿,右下角气泡写着「参与召唤 有几率获得5折」</p>"


def do_fix10():
    import pyautogui
    focus()
    pyautogui.hotkey("ctrl", "f")
    time.sleep(1.0)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.3)
    pyautogui.press("delete")
    time.sleep(0.3)
    set_clip("text", "这还没完")
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(1.5)
    pyautogui.press("enter")
    time.sleep(1.2)
    log("已定位到「这还没完」")
    pyautogui.press("escape")
    time.sleep(0.8)
    pyautogui.press("left")
    time.sleep(0.5)
    log("光标已收到匹配起点")
    paste("hdrop", [IMG10])
    time.sleep(16)
    log("img10 已粘")


def do_fix10cap():
    import pyautogui
    focus()
    paste("html", CAP10)
    time.sleep(3)
    log("图10 图注已粘")


def do_save():
    import pyautogui
    focus()
    pyautogui.click(*SAVE_POS)
    time.sleep(3)
    log("已点存稿 %s" % (SAVE_POS,))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "focus"
    if cmd == "build":
        build()
    elif cmd == "focus":
        print("前台窗口:", focus())
    elif cmd == "title":
        do_title()
    elif cmd == "clear":
        do_clear()
    elif cmd == "run":
        do_run(int(sys.argv[2]), int(sys.argv[3]))
    elif cmd == "find":
        import pyautogui
        focus()
        pyautogui.hotkey("ctrl", "f")
        time.sleep(1.0)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.3)
        pyautogui.press("delete")
        time.sleep(0.3)
        set_clip("text", sys.argv[2])
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(1.5)
        pyautogui.press("enter")
        time.sleep(1.2)
        log("find: %s" % sys.argv[2])
    elif cmd == "fix10":
        do_fix10()
    elif cmd == "fix10cap":
        do_fix10cap()
    elif cmd == "readback":
        do_readback()
    elif cmd == "save":
        do_save()
    elif cmd == "show":
        b = load_blocks()
        for i in range(int(sys.argv[2]), int(sys.argv[3])):
            print(i, b[i]["t"], re.sub(r"<[^<>]+>", "", b[i].get("html", b[i].get("path", "")))[:60])
