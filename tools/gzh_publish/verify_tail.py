# -*- coding: utf-8 -*-
"""verify_tail.py — 滚动到文章末尾, 检测 card_05(写在最后)是否插入"""
import asyncio
import io
import time
from collections import defaultdict
from pathlib import Path

import mss
import pyautogui
from PIL import Image

BODY_X_MIN, BODY_X_MAX = 380, 960
OUT = Path(r"D:\7tan\7tanAI\data\screenshots")


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
                words.append({
                    "text": w.text,
                    "x": round(r.x + r.width / 2),
                    "y": round(r.y + r.height / 2),
                    "w": round(r.width),
                    "h": round(r.height),
                })
        return words
    return asyncio.run(_run())


def scroll_down():
    pyautogui.moveTo(650, 620, duration=0.1)
    time.sleep(0.2)
    pyautogui.scroll(-700)
    time.sleep(1.0)


def main():
    pyautogui.moveTo(350, 49, duration=0.2)
    time.sleep(0.2)
    pyautogui.click()
    time.sleep(2.0)

    lines_out = []
    big_out = []
    prev_sig = ""
    for step in range(6):
        img = grab()
        words = ocr_words(img)
        rows = defaultdict(list)
        for w in words:
            if BODY_X_MIN <= w["x"] <= BODY_X_MAX and 130 <= w["y"] <= 1040:
                rows[w["y"] // 14].append(w)
        step_lines = []
        for yk in sorted(rows):
            ws = sorted(rows[yk], key=lambda w: w["x"])
            line = "".join(w["text"] for w in ws)
            maxh = max(w["h"] for w in ws)
            step_lines.append((yk, line, maxh))
            if maxh >= 25:
                big_out.append(f"y~{yk*14} h={maxh}: {line[:70]}")
        sig = "|".join(l[1][:20] for l in step_lines[:5])
        if sig != prev_sig:
            lines_out.append(f"--- step{step} ---")
            for yk, line, maxh in step_lines:
                lines_out.append(f"  y~{yk*14} hmax={maxh}: {line[:90]}")
            prev_sig = sig
        scroll_down()

    (OUT / "verify_tail_report.txt").write_text("\n".join(lines_out), encoding="utf-8")
    (OUT / "verify_tail_big.txt").write_text("\n".join(big_out), encoding="utf-8")
    print("TAIL_SAVED", len(lines_out), "lines, BIG", len(big_out))


if __name__ == "__main__":
    main()
