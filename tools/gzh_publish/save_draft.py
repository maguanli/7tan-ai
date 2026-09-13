# -*- coding: utf-8 -*-
"""save_draft.py — 切回浏览器标签, 定位并点击「保存为草稿」"""
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


def find_key_pos(words, key, min_ratio=0.5, xmin=0, xmax=2000):
    """行级匹配 -> 返回行中与 key 最相似的那个词的坐标"""
    rows = defaultdict(list)
    for w in words:
        if xmin <= w["x"] <= xmax:
            rows[w["y"] // 12].append(w)
    for yk in sorted(rows):
        ws = sorted(rows[yk], key=lambda w: w["x"])
        line_text = "".join(w["text"] for w in ws)
        if key in line_text:
            # 找行中含 key 子串的词
            for w in ws:
                if key in w["text"]:
                    return w
            # 否则返回行中间词
            return ws[len(ws) // 2]
    # 模糊
    best_w = None
    best_r = 0.0
    for w in words:
        if xmin <= w["x"] <= xmax:
            r = difflib.SequenceMatcher(None, key, w["text"]).ratio()
            if r > best_r:
                best_r = r
                best_w = w
    if best_w and best_r >= min_ratio:
        return best_w
    return None


def main():
    # 切回浏览器标签(标签栏「浏览器」x~350, y~49; 或 y~111 如果标签栏在下方)
    for y in (49, 111):
        pyautogui.moveTo(345, y, duration=0.2)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(1.5)
        img = grab()
        words = ocr_words(img)
        # 检查是否看到「保存为草稿」或「发表」按钮
        hit = find_key_pos(words, "草稿", xmin=380, xmax=960)
        if hit:
            print(f"EDITOR_VISIBLE save-btn at ({hit['x']},{hit['y']})")
            break
    else:
        print("EDITOR_NOT_VISIBLE")
        return

    # 点击「保存为草稿」按钮
    click_btn = find_key_pos(words, "草稿", xmin=380, xmax=960)
    if click_btn:
        pyautogui.moveTo(click_btn["x"], click_btn["y"], duration=0.3)
        time.sleep(0.3)
        pyautogui.click()
        print(f"CLICK_SAVE ({click_btn['x']},{click_btn['y']})")
        time.sleep(3.0)

    # 确认: 截图看是否有「保存成功」提示或弹窗变化
    img = grab()
    words = ocr_words(img)
    ok = find_key_pos(words, "成功", xmin=0, xmax=2000)
    if ok:
        print(f"SAVE_CONFIRM hint at ({ok['x']},{ok['y']}) line={ok['text']}")
    else:
        print("SAVE_NO_HINT (check screen)")
    print("DONE")


if __name__ == "__main__":
    main()
