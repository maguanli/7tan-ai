# -*- coding: utf-8 -*-
"""
region_ocr.py — 区域裁剪 OCR 工具（优化版）
============================================
解决旧方案「全屏截图 + 全屏 OCR」导致 CPU 100% 的问题。

优化点（对应之前的 5 个问题）：
  1. 只识别目标区域（鼠标框选 / 坐标参数），不再整屏 OCR
  2. 截图用 mss（C 扩展，毫秒级），替代 pyautogui.screenshot()
  3. 可选缩放 scale=0.3~0.5，OCR 计算量降到 1/10 以下
  4. OCR 引擎只初始化一次并复用（Windows OCR / Tesseract 自动选择）
  5. 自动保存区域小图，方便调试定位
  6. 支持 --loop 连续监测，带间隔冷却，不会连续轰炸 CPU

用法示例：
  python region_ocr.py --select                       # 鼠标框选后识别一次
  python region_ocr.py --region 100,200,800,300       # 指定坐标区域识别
  python region_ocr.py --region 100,200,800,300 --scale 0.5   # 缩放识别(更快)
  python region_ocr.py --select --loop 0 --interval 3 --save-text result.txt  # 连续监测
  python region_ocr.py --region 0,0,400,200 --engine tesseract --lang chi_sim
"""

import argparse
import io
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("缺少 Pillow，请先安装: pip install pillow")

try:
    import mss
except ImportError:
    sys.exit("缺少 mss，请先安装: pip install mss")


# ============================================================
# 1. 截图：只截目标区域（mss，快）
# ============================================================
def _create_mss():
    """兼容新旧版 mss：新版用 MSS 类，旧版用 mss()。"""
    cls = getattr(mss, "MSS", None)
    return cls() if cls else mss.mss()


def grab_region(x, y, w, h, scale=1.0):
    """截取屏幕区域 (x,y,w,h)，可选缩放。返回 PIL Image。"""
    with _create_mss() as sct:
        monitor = {"left": int(x), "top": int(y), "width": int(w), "height": int(h)}
        shot = sct.grab(monitor)
    img = Image.frombytes("RGB", shot.size, shot.rgb)
    if scale and scale != 1.0:
        new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
        img = img.resize(new_size, Image.LANCZOS)
    return img


# ============================================================
# 2. OCR 引擎封装（只初始化一次，循环复用）
# ============================================================
class WindowsOcrEngine:
    """Windows 原生 OCR（WinRT），中文识别好，纯 CPU 但区域小图很快。"""
    name = "windows-ocr"

    def __init__(self, lang="zh-CN", debug=False):
        # 兼容 winrt / winsdk 两种包
        try:
            from winrt.windows.media.ocr import OcrEngine as _OE
            from winrt.windows.globalization import Language as _Lang
            from winrt.windows.graphics.imaging import BitmapDecoder as _BD
            from winrt.windows.storage.streams import (
                InMemoryRandomAccessStream as _Stream,
                DataWriter as _Writer,
            )
        except ImportError:
            from winsdk.windows.media.ocr import OcrEngine as _OE
            from winsdk.windows.globalization import Language as _Lang
            from winsdk.windows.graphics.imaging import BitmapDecoder as _BD
            from winsdk.windows.storage.streams import (
                InMemoryRandomAccessStream as _Stream,
                DataWriter as _Writer,
            )
        self._OE = _OE
        self._Lang = _Lang
        self._BD = _BD
        self._Stream = _Stream
        self._Writer = _Writer

        engine = None
        if lang:
            try:
                engine = _OE.try_create_from_language(_Lang(lang))
            except Exception:
                engine = None
        if engine is None:  # 回退：使用用户配置文件语言
            engine = _OE.try_create_from_user_profile_languages()
        if engine is None:
            raise RuntimeError("Windows OCR 引擎创建失败（系统缺少 OCR 语言包？）")
        self.engine = engine
        if debug:
            print(f"[debug] Windows OCR 语言: {engine.recognizer_language.language_tag}")

    @staticmethod
    def _wait(op):
        """等待 WinRT 异步操作完成，兼容 winrt/winsdk 新旧版本。

        - 旧版 winsdk/winrt: op.get()
        - winsdk 1.x 部分操作: op.get_results() 可用
        - winsdk 1.x 部分操作（如 BitmapDecoder.create_async）必须真正 await
        """
        if hasattr(op, "get"):  # 旧版 winrt/winsdk
            return op.get()
        try:
            return op.get_results()
        except Exception:
            pass
        # winsdk 1.x：必须在事件循环中 await（当前线程可能无事件循环，用新线程）
        import asyncio
        import threading

        box = {}

        async def _await_op(o):
            return await o

        def _run():
            box["v"] = asyncio.run(_await_op(op))

        t = threading.Thread(target=_run)
        t.start()
        t.join()
        return box["v"]

    def recognize(self, pil_img):
        """识别 PIL 图片，返回文本。"""
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        data = buf.getvalue()

        stream = self._Stream()
        writer = self._Writer(stream)
        writer.write_bytes(data)
        # 兼容新旧版 winrt/winsdk：新版用 store_async()，旧版用 store()
        if hasattr(writer, "store"):
            writer.store()
        else:
            self._wait(writer.store_async())
        stream.seek(0)

        decoder = self._wait(self._BD.create_async(stream))
        bitmap = self._wait(decoder.get_software_bitmap_async())
        result = self._wait(self.engine.recognize_async(bitmap))
        return result.text


class TesseractOcrEngine:
    """Tesseract OCR（需安装 tesseract.exe），作为备选引擎。"""
    name = "tesseract"

    def __init__(self, lang="chi_sim", debug=False):
        try:
            import pytesseract
        except ImportError:
            raise RuntimeError("未安装 pytesseract，请先: pip install pytesseract")
        self._pt = pytesseract
        self.lang = lang or "chi_sim"
        try:
            self._pt.get_tesseract_version()
        except Exception as e:
            raise RuntimeError(
                f"找不到 tesseract.exe（{e}）。请安装 Tesseract-OCR 并加入 PATH，"
                "或改用 Windows 引擎（--engine windows）"
            )
        if debug:
            print(f"[debug] Tesseract 版本: {self._pt.get_tesseract_version()}")

    def recognize(self, pil_img):
        return self._pt.image_to_string(pil_img, lang=self.lang)


def create_engine(name, lang="", debug=False):
    """创建 OCR 引擎（auto 时自动挑选可用者）。"""
    candidates = ["windows", "tesseract"] if name == "auto" else [name]
    errors = []
    for eng in candidates:
        try:
            if eng == "windows":
                e = WindowsOcrEngine(lang or "zh-CN", debug)
            else:
                e = TesseractOcrEngine(lang or "chi_sim", debug)
            if debug:
                print(f"[debug] 使用引擎: {e.name}")
            return e
        except Exception as ex:
            errors.append(f"{eng}: {ex}")
            if debug:
                print(f"[debug] 引擎 {eng} 不可用: {ex}")
    sys.exit("没有可用的 OCR 引擎:\n  " + "\n  ".join(errors))


# ============================================================
# 3. 鼠标框选区域（tkinter 全屏半透明画布）
# ============================================================
def select_region():
    """让用户用鼠标拖拽框选区域，返回 [x, y, w, h]。"""
    try:
        import tkinter as tk
    except ImportError:
        sys.exit("tkinter 不可用，请改用 --region 指定坐标")

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.3)
    root.configure(bg="gray")
    canvas = tk.Canvas(root, cursor="cross", bg="gray", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    state = {"start": None, "rect": None, "result": None}

    def on_press(e):
        state["start"] = (e.x_root, e.y_root)
        if state["rect"]:
            canvas.delete(state["rect"])
        state["rect"] = canvas.create_rectangle(
            e.x_root, e.y_root, e.x_root, e.y_root, outline="red", width=2
        )

    def on_drag(e):
        if state["start"] and state["rect"]:
            canvas.coords(state["rect"], state["start"][0], state["start"][1], e.x_root, e.y_root)

    def on_release(e):
        x1, y1 = state["start"]
        x2, y2 = e.x_root, e.y_root
        x, y = min(x1, x2), min(y1, y2)
        w, h = abs(x2 - x1), abs(y2 - y1)
        if w < 5 or h < 5:
            print("选区太小，已取消")
            root.destroy()
            return
        state["result"] = [x, y, w, h]
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", lambda e: root.destroy())
    root.mainloop()
    return state["result"]


# ============================================================
# 4. 主流程
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="区域裁剪 OCR 工具（优化版）")
    parser.add_argument("--region", help="识别区域 x,y,w,h，如 100,200,800,300")
    parser.add_argument("--select", action="store_true", help="用鼠标框选区域（推荐）")
    parser.add_argument("--scale", type=float, default=1.0, help="截图缩放比例 0.1~1.0，越小越快（默认1.0）")
    parser.add_argument("--engine", choices=["auto", "windows", "tesseract"], default="auto", help="OCR 引擎（默认自动选择）")
    parser.add_argument("--lang", default="", help="识别语言：windows 用 zh-CN，tesseract 用 chi_sim")
    parser.add_argument("--loop", type=int, default=1, help="识别次数，0=无限循环（默认1次）")
    parser.add_argument("--interval", type=float, default=2.0, help="循环间隔秒数（默认2）")
    parser.add_argument("--save-dir", default="", help="保存区域截图目录（默认 data/screenshots）")
    parser.add_argument("--save-text", default="", help="识别文本追加保存到文件")
    parser.add_argument("--debug", action="store_true", help="打印调试信息")
    args = parser.parse_args()

    # ---- 确定识别区域 ----
    region = None
    if args.region:
        parts = [p.strip() for p in args.region.split(",")]
        if len(parts) != 4:
            parser.error("--region 格式应为 x,y,w,h，如 100,200,800,300")
        region = [int(p) for p in parts]
    elif args.select:
        print("请用鼠标拖拽框选要识别的区域（Esc 取消）...")
        region = select_region()
        if not region:
            sys.exit("未选择区域")
    else:
        with _create_mss() as sct:
            m = sct.monitors[0]  # 所有屏幕总区域
        region = [m["left"], m["top"], m["width"], m["height"]]
        print("⚠ 未指定区域，使用全屏（较慢）。建议用 --select 或 --region 裁剪区域")

    if args.scale <= 0 or args.scale > 1:
        parser.error("--scale 应在 0.1~1.0 之间")
    if args.loop < 0:
        parser.error("--loop 不能为负数")

    # ---- 初始化引擎（只一次，复用）----
    if not args.save_dir:
        args.save_dir = str(Path(__file__).resolve().parent.parent.parent / "data" / "screenshots")
    engine = create_engine(args.engine, args.lang, args.debug)
    if args.save_dir:
        Path(args.save_dir).mkdir(parents=True, exist_ok=True)

    print(f"区域: {region} | 缩放: {args.scale}x | 引擎: {engine.name} | 循环: {'∞' if args.loop==0 else args.loop} 次")

    # ---- 识别循环（带冷却，不烧 CPU）----
    count = 0
    try:
        while args.loop == 0 or count < args.loop:
            count += 1
            t0 = time.time()
            img = grab_region(*region, scale=args.scale)
            text = engine.recognize(img)
            elapsed = time.time() - t0
            now = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{now}] 第{count}次 | 耗时 {elapsed:.2f}s | 区域 {region} | 缩放 {args.scale}")
            print(text.strip() if text.strip() else "(未识别到文字)")

            if args.save_text:
                with open(args.save_text, "a", encoding="utf-8") as f:
                    f.write(f"\n===== {datetime.now().isoformat()} region={region} scale={args.scale} =====\n{text}\n")

            if args.save_dir:
                fname = f"region_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                img.save(Path(args.save_dir) / fname)
                if args.debug:
                    print(f"[debug] 截图已保存: {fname}")

            if args.loop != 0 and count >= args.loop:
                break
            if args.loop == 0 or count < args.loop:
                time.sleep(args.interval)  # 冷却，避免连续轰炸
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
