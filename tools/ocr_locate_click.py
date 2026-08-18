# -*- coding: utf-8 -*-
"""
ocr_locate_click.py — 屏幕 OCR 定位 + 虚拟鼠标真实点击
用途：微信公众平台草稿卡片用 JS 合成点击无效（isTrusted=false），
      必须用系统级真实鼠标点击。本脚本在全屏截图上用 Windows OCR
      找到目标文字位置，再调用 pyautogui 移动鼠标真实点击。
用法：
  python ocr_locate_click.py "目标文字"            # 定位并打印，不点击
  python ocr_locate_click.py "目标文字" --click    # 定位并真实点击
  python ocr_locate_click.py "目标文字" --click --offset 0,20   # 点击位置微调
"""
import argparse
import io
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, r"D:\7tan\7tanAI\tools")

try:
    from PIL import Image
    import mss
    import pyautogui
except ImportError as e:
    sys.exit(f"缺少依赖: {e}")

from region_ocr import WindowsOcrEngine


def full_screen_image():
    cls = getattr(mss, "MSS", None)
    with (cls() if cls else mss.mss()) as sct:
        shot = sct.grab(sct.monitors[1])
    return Image.frombytes("RGB", shot.size, shot.rgb)


def recognize_lines(img):
    """用 WinRT OCR 识别，返回 [(text, left, top, width, height), ...]（屏幕像素坐标）"""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()

    from winrt.windows.media.ocr import OcrEngine as _OE
    from winrt.windows.globalization import Language as _Lang
    from winrt.windows.graphics.imaging import BitmapDecoder as _BD
    from winrt.windows.storage.streams import (
        InMemoryRandomAccessStream as _Stream,
        DataWriter as _Writer,
    )

    engine = None
    try:
        engine = _OE.try_create_from_language(_Lang("zh-CN"))
    except Exception:
        engine = None
    if engine is None:
        engine = _OE.try_create_from_user_profile_languages()
    if engine is None:
        sys.exit("Windows OCR 引擎创建失败")

    stream = _Stream()
    writer = _Writer(stream)
    writer.write_bytes(data)
    if hasattr(writer, "store"):
        writer.store()
    else:
        writer.store_async().get()
    stream.seek(0)

    decoder = _BD.create_async(stream).get()
    bitmap = decoder.get_software_bitmap_async().get()
    result = engine.recognize_async(bitmap).get()

    lines = []
    for line in result.lines:
        text = line.text.strip()
        if not text:
            continue
        # 新版 winrt: OcrLine 无 recognized_text_rect，用 words 的 bounding_rect 合成
        if hasattr(line, "recognized_text_rect"):
            r = line.recognized_text_rect
            lines.append((text, int(r.x), int(r.y), int(r.width), int(r.height)))
        elif hasattr(line, "words") and line.words:
            xs, ys, x2s, y2s = [], [], [], []
            for w in line.words:
                br = w.bounding_rect
                xs.append(br.x)
                ys.append(br.y)
                x2s.append(br.x + br.width)
                y2s.append(br.y + br.height)
            lx, ty = min(xs), min(ys)
            rx, by = max(x2s), max(y2s)
            lines.append((text, int(lx), int(ty), int(rx - lx), int(by - ty)))
        else:
            continue
    return lines


def _norm(s):
    """去掉 OCR 会在中文字符间插入的空格"""
    return s.replace(" ", "").replace("\u3000", "")


def find_target(lines, target):
    """在识别结果中找包含目标文字的 line（去空格后包含匹配），返回其中心坐标 (x, y) 与命中文本"""
    nt = _norm(target)
    if not nt:
        return None
    hits = []
    for text, x, y, w, h in lines:
        ntext = _norm(text)
        if ntext and nt in ntext:
            hits.append((text, x, y, w, h))
    # 优先选择最长（最完整）的匹配行
    hits.sort(key=lambda t: -len(t[0]))
    if not hits:
        return None
    text, x, y, w, h = hits[0]
    return text, (x + w // 2, y + h // 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="要定位的目标文字（支持子串）")
    ap.add_argument("--click", action="store_true", help="定位后真实点击")
    ap.add_argument("--offset", default="0,0", help="点击偏移 dx,dy")
    ap.add_argument("--save", default=r"D:\7tan\7tanAI\data\screenshots\ocr_full.png", help="全屏截图保存路径")
    args = ap.parse_args()

    print("[1] 全屏截图...")
    img = full_screen_image()
    img.save(args.save)
    print(f"    截图: {args.save} ({img.width}x{img.height})")

    print("[2] OCR 识别全屏...")
    t0 = time.time()
    lines = recognize_lines(img)
    print(f"    识别到 {len(lines)} 行文字, 耗时 {time.time()-t0:.1f}s")

    # 打印包含目标关键词附近的行，方便调试
    for text, x, y, w, h in lines:
        if any(k in text for k in ["大起大落", "40岁", "才明白", "人生最好", "四个字", "草稿", "近期"]):
            print(f"    > {text!r} @ ({x},{y},{w}x{h})")

    # 兼容命令行传递时引号被原样传入的情况
    args.target = args.target.strip(' \"\'\u201c\u201d')
    hit = find_target(lines, args.target)
    if not hit:
        print("[X] 未找到目标文字")
        sys.exit(2)
    text, (cx, cy) = hit
    dx, dy = map(int, args.offset.split(","))
    cx, cy = cx + dx, cy + dy
    print(f"[3] 命中: {text!r} → 中心 ({cx},{cy})")

    if args.click:
        print(f"[4] 虚拟鼠标移动到 ({cx},{cy}) 并点击...")
        pyautogui.moveTo(cx, cy, duration=0.3)
        time.sleep(0.3)
        pyautogui.click(cx, cy)
        print("    已点击！")
    else:
        print("[4] 仅定位（未点击）。加 --click 执行真实点击")


if __name__ == "__main__":
    main()
