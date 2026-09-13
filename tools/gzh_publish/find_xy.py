# -*- coding: utf-8 -*-
"""find_xy.py — OCR 找屏幕上的关键词(写死在脚本, 避免命令行中文乱码)"""
import asyncio
import io
import sys
import time
from collections import defaultdict
from pathlib import Path

import mss
import pyautogui
from PIL import Image

KEYWORDS = ["拖拽", "封面", "选择", "摘要", "原创", "保存"]


def grab():
    cls = getattr(mss, "MSS", None)
    with (cls() if cls else mss.mss()) as sct:
        shot = sct.grab(sct.monitors[1])
    return Image.frombytes("RGB", shot.size, shot.rgb)


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
        result = await engine.recognize_async(bitmap)
        words = []
        for line in result.lines:
            for w in line.words:
                r = w.bounding_rect
                words.append({"text": w.text, "x": round(r.x + r.width / 2),
                              "y": round(r.y + r.height / 2), "h": round(r.height)})
        return words
    return asyncio.run(_run())


def main():
    img = grab()
    words = ocr_words(img)
    rows = defaultdict(list)
    for w in words:
        rows[w["y"] // 12].append(w)
    lines = []
    for yk in sorted(rows):
        ws = sorted(rows[yk], key=lambda w: w["x"])
        lines.append((yk * 12, "".join(w["text"] for w in ws)))
    for y, text in lines:
        for kw in KEYWORDS:
            if kw in text:
                print(f"FOUND {kw} @ y={y}: {text[:80]}")
    print("---ALL---")
    for y, text in lines:
        print(f"y={y}: {text[:90]}")


if __name__ == "__main__":
    main()
