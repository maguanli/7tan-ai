# -*- coding: utf-8 -*-
"""
verify_cards.py — 滚动全文, 检测编辑器中的图片卡片(大字词 h>=28px)
用于验证 6 张配图是否插入成功, 并检查是否有重复/误插。
"""
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
OUT.mkdir(parents=True, exist_ok=True)


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


def scroll_top():
    pyautogui.moveTo(650, 620, duration=0.1)
    time.sleep(0.2)
    for _ in range(8):
        pyautogui.scroll(1500)
        time.sleep(0.15)
    time.sleep(1.2)


def scroll_down():
    pyautogui.moveTo(650, 620, duration=0.1)
    time.sleep(0.2)
    pyautogui.scroll(-600)
    time.sleep(0.9)


def main():
    pyautogui.moveTo(350, 49, duration=0.2)
    time.sleep(0.2)
    pyautogui.click()
    time.sleep(2.0)
    scroll_top()
    time.sleep(0.5)

    big_seen = []      # 大字词(卡片文字)
    all_lines = []     # 全部行文本(粗略)
    prev_sig = ""
    for step in range(14):
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
            if maxh >= 28:
                big_seen.append((yk, line[:60], maxh))
        # 签名去重: 只记录内容变化较大的步骤
        sig = "|".join(l[1][:20] for l in step_lines[:5])
        if sig != prev_sig:
            all_lines.append(f"--- step{step} ---")
            for yk, line, maxh in step_lines:
                all_lines.append(f"  y~{yk*14} hmax={maxh}: {line[:90]}")
            prev_sig = sig
        scroll_down()

    report = "\n".join(all_lines)
    (OUT / "verify_report.txt").write_text(report, encoding="utf-8")
    big_report = "\n".join(f"y~{y*14} h={h}: {t}" for y, t, h in big_seen)
    (OUT / "verify_big.txt").write_text(big_report, encoding="utf-8")
    print("REPORT_SAVED", len(all_lines), "lines, BIG_WORDS", len(big_seen))


if __name__ == "__main__":
    main()
