# -*- coding: utf-8 -*-
"""
ocr_locate_click.py — 全屏 OCR 定位 + 虚拟鼠标点击
1. mss 全屏截图
2. winsdk Windows OCR 识别，输出每个词的中心坐标
3. 按关键词定位目标（如草稿标题），pyautogui 真实鼠标点击
用法:
  python ocr_locate_click.py --keys "40岁,大起大落"          # 只定位输出坐标
  python ocr_locate_click.py --keys "40岁,大起大落" --click  # 定位并点击第一个命中
  python ocr_locate_click.py --keys "xxx" --click --double  # 双击
"""
import argparse
import asyncio
import io
import json
import sys
import time
from pathlib import Path

import mss
from PIL import Image

OUT = Path(r"D:\7tan\7tanAI\data\screenshots")
OUT.mkdir(parents=True, exist_ok=True)


def grab_screen():
    cls = getattr(mss, "MSS", None)
    with (cls() if cls else mss.mss()) as sct:
        mon = sct.monitors[1]  # 主屏
        shot = sct.grab(mon)
    img = Image.frombytes("RGB", shot.size, shot.rgb)
    path = OUT / "screen_now.png"
    img.save(path)
    return img, path


def ocr_words(img):
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

    async def _run():
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()

        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream)
        writer.write_bytes(data)
        await writer.store_async()
        stream.seek(0)

        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()

        engine = OcrEngine.try_create_from_language(Language("zh-CN"))
        if engine is None:
            engine = OcrEngine.try_create_from_user_profile_languages()
        if engine is None:
            raise RuntimeError("Windows OCR 引擎创建失败")

        result = await engine.recognize_async(bitmap)
        words = []
        for line in result.lines:
            for w in line.words:
                r = w.bounding_rect
                words.append({
                    "text": w.text,
                    "x": round(r.x + r.width / 2),
                    "y": round(r.y + r.height / 2),
                    "w": round(r.width),
                    "h": round(r.height),
                })
        return words

    return asyncio.run(_run())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", default="", help="关键词，逗号分隔")
    ap.add_argument("--click", action="store_true", help="定位后点击第一个命中")
    ap.add_argument("--double", action="store_true", help="双击")
    ap.add_argument("--offset-x", type=int, default=0)
    ap.add_argument("--offset-y", type=int, default=0)
    args = ap.parse_args()

    img, path = grab_screen()
    print(f"SHOT {path} {img.size}")
    t0 = time.time()
    words = ocr_words(img)
    print(f"OCR {len(words)} words in {time.time()-t0:.1f}s")

    (OUT / "ocr_words.json").write_text(
        json.dumps(words, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WORDS_SAVED", OUT / "ocr_words.json")

    keys = [k.strip() for k in args.keys.split(",") if k.strip()]
    if keys:
        for k in keys:
            hits = [w for w in words if k in w["text"]]
            print(f"KEY[{k}] hits={len(hits)}")
            for h in hits[:8]:
                print(f"   {h['text']} @ ({h['x']},{h['y']})")

    if args.click and keys:
        for k in keys:
            for h in words:
                if k in h["text"]:
                    x, y = h["x"] + args.offset_x, h["y"] + args.offset_y
                    import pyautogui
                    pyautogui.moveTo(x, y, duration=0.3)
                    time.sleep(0.2)
                    pyautogui.click()
                    if args.double:
                        time.sleep(0.15)
                        pyautogui.click()
                    print(f"CLICKED ({x},{y}) text={h['text']}")
                    return 0
        print("NO_HIT")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
