# -*- coding: utf-8 -*-
"""
wechat_helper.py — 微信桌面自动化助手（OCR 定位 + 点击 + 输入）
================================================================
解决微信 4.0 自绘界面无法用 UIA 读控件的问题：
  1. 全屏/区域 OCR → 输出「文字 + 屏幕坐标」(JSON)，让 AI 知道界面上有什么
  2. --click "文字" → 根据 OCR 坐标自动点击（模拟鼠标）
  3. --type "文字"  → 剪贴板粘贴输入（保证中文真正输入，绝不漏输）
  4. --key 按键     → 模拟键盘（enter/tab/esc/f5...）

用法示例：
  python wechat_helper.py --status                 # 全屏 OCR，列出所有文字+坐标
  python wechat_helper.py --region 0,0,500,300     # 只识别左上区域
  python wechat_helper.py --click "文章"            # 点击识别到的"文章"
  python wechat_helper.py --click "最热" --index 0  # 点击第1个"最热"
  python wechat_helper.py --type "游戏推荐"         # 粘贴输入中文（防漏输）
  python wechat_helper.py --key enter              # 按回车
  python wechat_helper.py --status --save shot.png # 截图+OCR

注意：所有坐标均为屏幕物理坐标（已做 DPI 感知），与 pyautogui 点击一致。
"""
import argparse
import ctypes
import io
import json
import sys
import time

# ---- DPI 感知：保证 mss 截图坐标 == pyautogui 点击坐标 ----
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

from PIL import Image


# ============================================================
# 截图（mss）
# ============================================================
def grab(x=0, y=0, w=None, h=None):
    import mss
    with mss.mss() as sct:
        mon = sct.monitors[1]  # 主屏
        if w is None:
            w = mon["width"] - x
        if h is None:
            h = mon["height"] - y
        shot = sct.grab({"left": int(x), "top": int(y),
                         "width": int(w), "height": int(h)})
    return Image.frombytes("RGB", shot.size, shot.rgb)


# ============================================================
# Windows OCR：返回词列表 [{text,x,y,w,h}]
# ============================================================
class WinOcrWords:
    def __init__(self, lang="zh-CN"):
        try:
            from winrt.windows.media.ocr import OcrEngine
            from winrt.windows.globalization import Language
            from winrt.windows.graphics.imaging import BitmapDecoder
            from winrt.windows.storage.streams import (
                InMemoryRandomAccessStream, DataWriter)
        except ImportError:
            from winsdk.windows.media.ocr import OcrEngine
            from winsdk.windows.globalization import Language
            from winsdk.windows.graphics.imaging import BitmapDecoder
            from winsdk.windows.storage.streams import (
                InMemoryRandomAccessStream, DataWriter)
        self.OcrEngine, self.Language = OcrEngine, Language
        self.BitmapDecoder, self.Stream, self.Writer = BitmapDecoder, InMemoryRandomAccessStream, DataWriter
        self.engine = None
        try:
            self.engine = OcrEngine.try_create_from_language(Language(lang))
        except Exception:
            self.engine = None
        if self.engine is None:
            self.engine = OcrEngine.try_create_from_user_profile_languages()
        if self.engine is None:
            raise RuntimeError("Windows OCR 引擎创建失败")

    def words(self, pil_img):
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        data = buf.getvalue()
        stream = self.Stream()
        writer = self.Writer(stream)
        writer.write_bytes(data)
        if hasattr(writer, "store"):
            writer.store()
        else:
            writer.store_async().get()
        stream.seek(0)
        decoder = self.BitmapDecoder.create_async(stream).get()
        bitmap = decoder.get_software_bitmap_async().get()
        result = self.engine.recognize_async(bitmap).get()
        out = []
        for line in result.lines:
            for w in line.words:
                r = w.bounding_rect
                out.append({
                    "text": w.text,
                    "x": int(r.x), "y": int(r.y),
                    "w": int(r.width), "h": int(r.height),
                })
        return out


# ============================================================
# 点击 / 输入
# ============================================================
def click_at(x, y, desc=""):
    import pyautogui
    pyautogui.click(int(x), int(y))
    print(f"[CLICK] ({int(x)},{int(y)}) {desc}")


def find_word(words, keyword, index=0, fuzzy=True):
    """在 OCR 词列表中找包含关键词的词（可模糊，如 文章/最热/阅读）。"""
    kw = keyword.strip()
    hits = []
    for it in words:
        t = it["text"].strip()
        if fuzzy:
            if kw in t or t in kw:
                hits.append(it)
        else:
            if t == kw:
                hits.append(it)
    if not hits:
        return None
    if index >= len(hits):
        index = len(hits) - 1
    return hits[index]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true", help="全屏 OCR 列出文字+坐标")
    ap.add_argument("--region", default="", help="x,y,w,h 只识别该区域")
    ap.add_argument("--click", default="", help="点击包含该文字的词")
    ap.add_argument("--index", type=int, default=0, help="命中多个时选第几个(0起)")
    ap.add_argument("--type", dest="type_text", default="", help="剪贴板粘贴输入中文")
    ap.add_argument("--key", default="", help="按键: enter/tab/esc/f5/ctrl+a...")
    ap.add_argument("--save", default="", help="保存截图路径")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    # 区域
    x, y, w, h = 0, 0, None, None
    if args.region:
        parts = [int(p) for p in args.region.replace(" ", "").split(",")]
        x, y = parts[0], parts[1]
        if len(parts) >= 4:
            w, h = parts[2], parts[3]

    img = grab(x, y, w, h)
    if args.save:
        img.save(args.save)
        print(f"[SAVED] {args.save}")

    # 按键
    if args.key:
        import pyautogui
        k = args.key.strip().lower()
        mapping = {"enter": "enter", "esc": "esc", "tab": "tab",
                   "f5": "f5", "back": "backspace", "del": "delete",
                   "up": "up", "down": "down", "left": "left", "right": "right",
                   "ctrl+a": ["ctrl", "a"], "ctrl+v": ["ctrl", "v"],
                   "ctrl+c": ["ctrl", "c"], "ctrl+f": ["ctrl", "f"],
                   "ctrl+s": ["ctrl", "s"], "ctrl+z": ["ctrl", "z"],
                   "ctrl+w": ["ctrl", "w"], "alt+f4": ["alt", "f4"]}
        if k in mapping:
            key = mapping[k]
            if isinstance(key, list):
                pyautogui.hotkey(*key)
            else:
                pyautogui.press(key)
            print(f"[KEY] {args.key}")
        else:
            pyautogui.press(k)
            print(f"[KEY] {args.key}")
        time.sleep(0.3)

    # 输入（剪贴板粘贴，保证中文）
    if args.type_text:
        import pyautogui
        import pyperclip
        pyperclip.copy(args.type_text)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "v")
        print(f"[TYPE] 已粘贴输入: {args.type_text}")
        time.sleep(0.3)

    # OCR 识别
    ocr = WinOcrWords()
    words = ocr.words(img)
    # 坐标补偿（区域偏移）
    for it in words:
        it["x"] += x
        it["y"] += y

    # 点击
    if args.click:
        hit = find_word(words, args.click, args.index)
        if hit:
            cx = hit["x"] + hit["w"] // 2
            cy = hit["y"] + hit["h"] // 2
            click_at(cx, cy, f'"{args.click}" -> "{hit["text"]}"')
        else:
            print(f"[MISS] 未找到可点击的文字: {args.click}")
            # 输出相近词便于排查
            close = [it["text"] for it in words if any(ch in it["text"] for ch in args.click)]
            if close:
                print(f"[HINT] 相似词: {close[:10]}")
            sys.exit(2)

    # 输出
    if args.json:
        print(json.dumps(words, ensure_ascii=False))
    else:
        for i, it in enumerate(words):
            print(f'{i:3d} [{it["x"]:5d},{it["y"]:5d} {it["w"]:4d}x{it["h"]:3d}] {it["text"]}')


if __name__ == "__main__":
    main()
