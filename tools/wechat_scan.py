# -*- coding: utf-8 -*-
"""
wechat_scan.py — 微信界面侦察 v2：找窗口 → 截图 → OCR(带坐标) → 输出 UTF-8 文件
用于定位微信窗口、识别当前界面文字与位置，为自动化点击做准备。
低CPU：只截微信窗口区域 + 50%缩放 OCR。
用法: python wechat_scan.py [--out xxx.png] [--txt out.txt] [--scale 0.5]
"""
import sys, ctypes, io, argparse
from pathlib import Path

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import win32gui
import mss
from PIL import Image

# ---------- OCR 引擎（winrt，兼容新旧版） ----------
try:
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
except ImportError:
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

_engine = None
def get_engine():
    global _engine
    if _engine is None:
        _engine = (OcrEngine.try_create_from_language(Language('zh-CN'))
                   or OcrEngine.try_create_from_user_profile_languages())
    return _engine

def ocr_words(pil_img, scale=1.0):
    """识别图片，返回 ([(x,y,w,h,text)...], full_text)。坐标为原始图片坐标。
    注意：不做 PIL 缩放（Windows OCR 对缩放图识别会返回空），
    scale 参数仅用于坐标换算（若外部已缩放，则按 scale 还原坐标）。"""
    buf = io.BytesIO(); pil_img.save(buf, format='PNG'); data = buf.getvalue()
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(data)
    if hasattr(writer, 'store'):
        writer.store()
    else:
        writer.store_async().get()
    stream.seek(0)
    # 用已验证可用的 create_async 方式（兼容 winrt 新旧版）
    if hasattr(BitmapDecoder, 'create_async'):
        dec = BitmapDecoder.create_async(stream).get()
    else:
        dec = BitmapDecoder.create(stream)
        if hasattr(dec, 'get'):
            dec = dec.get()
    if hasattr(dec, 'get_software_bitmap_async'):
        bmp = dec.get_software_bitmap_async().get()
    else:
        bmp = dec.get_software_bitmap()
    engine = get_engine()
    if hasattr(engine, 'recognize_async'):
        res = engine.recognize_async(bmp).get()
    else:
        res = engine.recognize(bmp)
    words = []
    for line in res.lines:
        # 新版 OcrLine 无 bounding_rect，用 words 合并
        if not line.words:
            continue
        xs = [w.bounding_rect.x for w in line.words]
        ys = [w.bounding_rect.y for w in line.words]
        x2s = [w.bounding_rect.x + w.bounding_rect.width for w in line.words]
        y2s = [w.bounding_rect.y + w.bounding_rect.height for w in line.words]
        x, y = min(xs), min(ys)
        w2, h2 = max(x2s) - x, max(y2s) - y
        # 坐标还原到原始图片（除以 scale）
        if scale and scale != 1.0:
            x, y, w2, h2 = int(x/scale), int(y/scale), int(w2/scale), int(h2/scale)
        words.append((x, y, w2, h2, line.text))
    return words, res.text

# ---------- 窗口查找 ----------
def find_wechat_windows():
    hits = []
    def cb(hwnd, _):
        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        if ('微信' in title) or ('weixin' in cls.lower()) or ('wechat' in cls.lower()):
            try:
                rect = win32gui.GetWindowRect(hwnd)
            except Exception:
                return
            w, h = rect[2]-rect[0], rect[3]-rect[1]
            if w > 100 and h > 100:
                hits.append({'hwnd': hwnd, 'title': title, 'cls': cls, 'rect': rect, 'w': w, 'h': h,
                             'visible': win32gui.IsWindowVisible(hwnd), 'iconic': win32gui.IsIconic(hwnd)})
    win32gui.EnumWindows(cb, None)
    return hits

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='wechat_scan.png')
    ap.add_argument('--txt', default='')
    ap.add_argument('--scale', type=float, default=1.0)
    ap.add_argument('--hwnd', type=int, default=0, help='指定窗口句柄（0=自动找最大）')
    args = ap.parse_args()

    if args.hwnd:
        rect = win32gui.GetWindowRect(args.hwnd)
        wins = [{'hwnd': args.hwnd, 'title': win32gui.GetWindowText(args.hwnd),
                 'rect': rect, 'w': rect[2]-rect[0], 'h': rect[3]-rect[1]}]
    else:
        wins = find_wechat_windows()
        if not wins:
            print('NO_WECHAT_WINDOW')
            return 1
        # 优先可见主窗口
        vis = [w for w in wins if w['visible'] and not w['iconic']]
        pool = vis or wins
        pool.sort(key=lambda x: x['w']*x['h'], reverse=True)
        wins = pool[:1]

    top = wins[0]
    print(f"WINDOW hwnd={top['hwnd']} title={top['title']!r} cls={top.get('cls','')} rect={top['rect']} size={top['w']}x{top['h']}")

    x0, y0, x1, y1 = top['rect']
    w, h = x1-x0, y1-y0
    with mss.MSS() if hasattr(mss, 'MSS') else mss.mss() as sct:
        shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
    img = Image.frombytes('RGB', shot.size, shot.rgb)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"SCREENSHOT saved={out} size={w}x{h}")

    words, full = ocr_words(img, scale=args.scale)
    txt_path = Path(args.txt) if args.txt else out.with_suffix('.txt')
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"# window rect={top['rect']} hwnd={top['hwnd']}\n")
        f.write("=== OCR WORDS (x,y,w,h,text) ===\n")
        for wx, wy, ww, wh, wt in words:
            f.write(f"{wx},{wy},{ww},{wh} | {wt}\n")
        f.write("\n=== FULL TEXT ===\n")
        f.write(full)
    print(f"OCR_LINES={len(words)} CHARS={len(full)} saved={txt_path}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
