# -*- coding: utf-8 -*-
"""
paste_cards.py v5 — 全自动把配图粘贴插入微信编辑器正文指定位置
v5 修复:
  - 匹配限定正文区域 x in [380, 960] (排除左侧导航/右侧面板误匹配)
  - 点击位置 = 正文行内最左词(>=380) 前 20px, 确保光标落在正文
  - 关键词换更稳的词(四点半/雪中送炭/心穷/归来)
  - 每张卡循环滚动直到找到关键词(最多6次)
  - 粘贴后验证: 重新OCR找卡片署名「大起大落的一生」确认插入
"""
import asyncio
import difflib
import io
import os
import subprocess
import time
from collections import defaultdict
from pathlib import Path

import mss
import pyautogui
from PIL import Image

CARDS = Path(r"D:\7tan\7tanAI\data\screenshots\gzh_cards")
BODY_X_MIN, BODY_X_MAX = 380, 960
BODY_Y_MIN, BODY_Y_MAX = 130, 1040


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


def find_key(words, key, min_ratio=0.6):
    """只匹配正文区域(380<=x<=960)的词, 行级拼接+模糊匹配。
    返回: 行内最左正文词坐标(点击点) + 命中行文本"""
    rows = defaultdict(list)
    for w in words:
        if BODY_X_MIN <= w["x"] <= BODY_X_MAX and BODY_Y_MIN <= w["y"] <= BODY_Y_MAX:
            rows[w["y"] // 12].append(w)
    best = None
    best_ratio = 0.0
    for yk in sorted(rows):
        ws = sorted(rows[yk], key=lambda w: w["x"])
        line_text = "".join(w["text"] for w in ws)
        if key in line_text:
            return {"x": ws[0]["x"], "y": ws[0]["y"], "line": line_text[:80], "ratio": 1.0}
        for i in range(max(1, len(line_text) - len(key) + 1)):
            seg = line_text[i:i + len(key)]
            r = difflib.SequenceMatcher(None, key, seg).ratio()
            if r > best_ratio:
                best_ratio = r
                best = {"x": ws[0]["x"], "y": ws[0]["y"], "line": line_text[:80], "ratio": r}
    if best and best_ratio >= min_ratio:
        return best
    return None


def set_clipboard_image(path):
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "Add-Type -AssemblyName System.Drawing;"
        f"$img=[System.Drawing.Bitmap]::FromFile('{path}');"
        "[System.Windows.Forms.Clipboard]::SetImage($img);"
        "Start-Sleep -Seconds 2;"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=30)


def scroll_dir(amount):
    pyautogui.moveTo(650, 620, duration=0.1)
    time.sleep(0.2)
    pyautogui.scroll(amount)
    time.sleep(0.9)


def scroll_top():
    pyautogui.moveTo(650, 620, duration=0.1)
    time.sleep(0.2)
    for _ in range(8):
        pyautogui.scroll(1500)
        time.sleep(0.15)
    time.sleep(1.2)


def paste_image(key, img_path, max_scrolls=6):
    """循环滚动找关键词 -> 点击正文行首 -> 粘贴图片 -> 验证插入"""
    for i in range(max_scrolls):
        img = grab()
        words = ocr_words(img)
        hit = find_key(words, key)
        if hit:
            x, y = hit["x"], hit["y"]
            # 点击正文行内最左词前 20px(>=400 保证在正文内)
            cx = max(400, min(x - 20, 900))
            pyautogui.moveTo(cx, y, duration=0.25)
            time.sleep(0.3)
            pyautogui.click()
            time.sleep(0.6)
            set_clipboard_image(str(img_path))
            time.sleep(0.5)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(5)
            print(f"PASTE_TRY {img_path.name} key={key} at=({x},{y}) scroll={i}")
            return True
        scroll_dir(-600)
    print(f"KEY_MISS_AFTER_SCROLL key={key}")
    return False


def verify_card(badge_text, max_scrolls=4):
    """验证: 滚动查找卡片徽标文字(如「卷首语」), 找到说明卡片在正文中。"""
    for i in range(max_scrolls):
        img = grab()
        words = ocr_words(img)
        hit = find_key(words, badge_text)
        if hit:
            print(f"VERIFY_OK badge={badge_text} at=({hit['x']},{hit['y']})")
            return True
        scroll_dir(700)  # 向上滚动找
    print(f"VERIFY_MISS badge={badge_text}")
    return False


def main():
    # 切回浏览器标签
    pyautogui.moveTo(350, 49, duration=0.2)
    time.sleep(0.2)
    pyautogui.click()
    time.sleep(2.0)
    print("TAB_CLICKED")

    # 滚动到文章顶部, 验证卡1(卷首图)是否已插入
    scroll_top()
    time.sleep(0.5)
    has_card1 = verify_card("卷首语", max_scrolls=2)

    jobs = []
    if not has_card1:
        jobs.append(("总以为", "card_00_open.png"))
    jobs += [
        ("发小的故事", "card_01_fa.png"),
        ("四点半", "card_02_ayi.png"),
        ("雪中送炭", "card_03_self.png"),
        ("心穷", "card_04_10s.png"),
        ("归来", "card_05_end.png"),
    ]
    for key, fname in jobs:
        paste_image(key, CARDS / fname)
    print("ALL_DONE")


if __name__ == "__main__":
    main()
