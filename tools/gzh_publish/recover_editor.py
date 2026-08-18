# -*- coding: utf-8 -*-
"""recover_editor.py — 关闭弹窗, 找回浏览器标签, 回到微信编辑页"""
import asyncio
import difflib
import io
import time
from collections import defaultdict

import mss
import pyautogui


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


def find_line(words, key, xmin=0, xmax=2000):
    rows = defaultdict(list)
    for w in words:
        if xmin <= w["x"] <= xmax:
            rows[w["y"] // 12].append(w)
    for yk in sorted(rows):
        ws = sorted(rows[yk], key=lambda w: w["x"])
        line = "".join(w["text"] for w in ws)
        if key in line:
            return {"y": ws[0]["y"], "x": ws[0]["x"], "line": line[:60]}
    return None


def main():
    # 1. 关弹窗
    pyautogui.press("esc")
    time.sleep(1.2)

    # 2. 找标签栏「浏览器」文字(可能 y49 或 y111 两行)
    img = grab()
    words = ocr_words(img)
    hit = find_line(words, "览器", xmin=200, xmax=600)
    if hit:
        print(f"TAB_FOUND 览器 @ y={hit['y']} line={hit['line']}")
        pyautogui.moveTo(hit["x"] + 40, hit["y"], duration=0.25)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(2.0)
        # 3. 确认编辑页出现「保存为草稿」按钮
        img = grab()
        words = ocr_words(img)
        hit2 = find_line(words, "草稿", xmin=380, xmax=960)
        if hit2:
            print(f"EDITOR_BACK save at y={hit2['y']} line={hit2['line']}")
            # 点击保存
            pyautogui.moveTo(740, hit2["y"], duration=0.3)
            time.sleep(0.3)
            pyautogui.click()
            print("CLICK_SAVE_BTN")
            time.sleep(3.0)
        else:
            print("EDITOR_NOT_BACK, dump:")
            for yk in sorted(set(w["y"] // 30 for w in words)):
                print(f"  y~{yk*30}")
    else:
        print("NO_TAB_FOUND, dump lines:")
        rows = defaultdict(list)
        for w in words:
            rows[w["y"] // 12].append(w)
        for yk in sorted(rows):
            ws = sorted(rows[yk], key=lambda w: w["x"])
            line = "".join(w["text"] for w in ws)
            if 30 <= yk * 12 <= 200:
                print(f"  y~{yk*12}: {line[:80]}")
    print("DONE")


if __name__ == "__main__":
    main()
