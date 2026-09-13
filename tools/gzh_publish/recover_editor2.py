# -*- coding: utf-8 -*-
"""recover_editor2.py — 点左侧「AI工作台」-> 点「浏览器」标签 -> 确认编辑页 -> 保存草稿"""
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


def click(x, y, wait=1.2):
    pyautogui.moveTo(x, y, duration=0.25)
    time.sleep(0.2)
    pyautogui.click()
    time.sleep(wait)


def main():
    # 1. 点左侧「AI工作台」(x~85, y~159)
    click(85, 159, wait=1.5)
    img = grab()
    words = ocr_words(img)
    hit = find_line(words, "览器", xmin=200, xmax=700)
    if not hit:
        print("AI_WORKBENCH_NO_BROWSER_TAB")
        return
    print(f"BROWSER_TAB at y={hit['y']} line={hit['line']}")
    # 2. 点「浏览器」标签
    click(hit["x"] + 40, hit["y"], wait=2.5)
    img = grab()
    words = ocr_words(img)
    hit2 = find_line(words, "草稿", xmin=380, xmax=960)
    if not hit2:
        print("EDITOR_STILL_NOT_VISIBLE")
        return
    print(f"EDITOR_BACK, save_btn line y={hit2['y']}: {hit2['line']}")
    # 3. 点「保存为草稿」(按钮 x~740)
    click(740, hit2["y"], wait=3.0)
    print("SAVE_CLICKED")
    # 4. 确认保存成功(找「成功」或弹窗)
    img = grab()
    words = ocr_words(img)
    ok = find_line(words, "成功", xmin=0, xmax=2000)
    if ok:
        print(f"SAVE_OK hint: {ok['line']}")
    else:
        print("SAVE_NO_HINT (check screen manually)")
    print("DONE")


if __name__ == "__main__":
    main()
