# -*- coding: utf-8 -*-
"""
set_cover.py — 设置公众号文章封面
流程: 点击封面占位区 -> 弹窗找「上传」-> 文件对话框输入路径 -> 选择图片 -> 确定
"""
import asyncio
import difflib
import io
import subprocess
import time
from collections import defaultdict
from pathlib import Path

import mss
import pyautogui

COVER = r"D:\7tan\7tanAI\data\screenshots\gzh_cards\cover_900x383.png"


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


def find_key(words, key, min_ratio=0.55):
    rows = defaultdict(list)
    for w in words:
        rows[w["y"] // 12].append(w)
    best = None
    best_ratio = 0.0
    for yk in sorted(rows):
        ws = sorted(rows[yk], key=lambda w: w["x"])
        line_text = "".join(w["text"] for w in ws)
        if key in line_text:
            return {"x": ws[0]["x"], "y": ws[0]["y"], "line": line_text[:70], "ratio": 1.0}
        for i in range(max(1, len(line_text) - len(key) + 1)):
            seg = line_text[i:i + len(key)]
            r = difflib.SequenceMatcher(None, key, seg).ratio()
            if r > best_ratio:
                best_ratio = r
                best = {"x": ws[0]["x"], "y": ws[0]["y"], "line": line_text[:70], "ratio": r}
    if best and best_ratio >= min_ratio:
        return best
    return None


def click(x, y):
    pyautogui.moveTo(x, y, duration=0.25)
    time.sleep(0.3)
    pyautogui.click()
    time.sleep(1.0)


def type_path(path):
    import pyperclip
    pyperclip.copy(path)
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(2.5)


def main():
    # 1. 点击封面占位区(摘要框上方 y~290)
    img = grab()
    words = ocr_words(img)
    # 找「52/120」摘要计数, 封面在其上方 ~80px
    hit = find_key(words, "120")
    if hit:
        fy = hit["y"] - 80
        print(f"COVER_AREA y={fy} (based on 52/120 at {hit['y']})")
        click(700, fy)
    else:
        print("NO 52/120 FOUND, click default (700, 290)")
        click(700, 290)
    time.sleep(2.5)

    # 2. 弹窗中找「上传」按钮
    img = grab()
    words = ocr_words(img)
    up = find_key(words, "上传")
    if not up:
        up = find_key(words, "本地上传")
    if not up:
        up = find_key(words, "图片和视频")
    if up:
        print(f"CLICK_UPLOAD at ({up['x']},{up['y']}) line={up['line']}")
        click(up["x"], up["y"])
        time.sleep(2.5)
        # 3. 文件对话框输入路径
        type_path(COVER)
    else:
        print("NO_UPLOAD_BUTTON, dump screen:")
        for yk in sorted(set(w["y"] // 30 for w in words)):
            print(f"  y~{yk*30}")
        return

    # 4. 上传后找「下一步」/「确定」/「完成」
    for key in ["下一步", "确定", "完成", "选择"]:
        for _ in range(3):
            img = grab()
            words = ocr_words(img)
            hit = find_key(words, key)
            if hit:
                print(f"CLICK {key} at ({hit['x']},{hit['y']})")
                click(hit["x"], hit["y"])
                time.sleep(2.0)
                break
            time.sleep(1.5)
    print("COVER_DONE")


if __name__ == "__main__":
    main()
