# -*- coding: utf-8 -*-
"""recover_editor3.py — 点击浏览器标签(345,49), dump 屏幕确认状态"""
import asyncio
import io
import time
from collections import defaultdict
from pathlib import Path

import mss
import pyautogui

OUT = Path(r"D:\7tan\7tanAI\data\screenshots")


def grab():
    cls = getattr(mss, "MSS", None)
    with (cls() if cls else mss.mss()) as sct:
        shot = sct.grab(sct.monitors[1])
    return shot


def ocr_words(img):
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
    from PIL import Image
    import io as _io

    pil = Image.frombytes("RGB", img.size, img.rgb)
    buf = _io.BytesIO()
    pil.save(buf, format="PNG")
    data = buf.getvalue()

    async def _run():
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


def dump_screen(words, fname):
    rows = defaultdict(list)
    for w in words:
        rows[w["y"] // 12].append(w)
    lines = []
    for yk in sorted(rows):
        ws = sorted(rows[yk], key=lambda w: w["x"])
        line = "".join(w["text"] for w in ws)
        lines.append(f"y~{yk*12}: {line[:100]}")
    (OUT / fname).write_text("\n".join(lines), encoding="utf-8")
    print("DUMP", fname, len(lines))


def main():
    pyautogui.press("esc")
    time.sleep(1.0)
    pyautogui.moveTo(345, 49, duration=0.25)
    time.sleep(0.2)
    pyautogui.click()
    time.sleep(2.5)
    img = grab()
    words = ocr_words(img)
    dump_screen(words, "state_after_browsertab.txt")
    # 找关键标志
    for key in ["草稿", "发表", "预览", "正文"]:
        rows = defaultdict(list)
        for w in words:
            rows[w["y"] // 12].append(w)
        for yk in sorted(rows):
            ws = sorted(rows[yk], key=lambda w: w["x"])
            line = "".join(w["text"] for w in ws)
            if key in line and 100 <= yk * 12 <= 1000:
                print(f"KEY {key} y~{yk*12}: {line[:70]}")
    print("DONE")


if __name__ == "__main__":
    main()
