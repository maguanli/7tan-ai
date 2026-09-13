# -*- coding: utf-8 -*-
"""find_xy2.py — 输出每行文本+词级坐标(ASCII安全)"""
import asyncio
import io
from collections import defaultdict

import mss
from PIL import Image


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
    out = []
    for yk in sorted(rows):
        ws = sorted(rows[yk], key=lambda w: w["x"])
        segs = []
        for w in ws:
            t = w["text"].encode("unicode_escape").decode()
            segs.append(f"{t}@{w['x']},{w['y']}")
        out.append(f"y~{yk*12}: " + " | ".join(segs))
    with open(r"D:\7tan\7tanAI\data\screenshots\xy_dump.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("SAVED xy_dump.txt", len(out), "rows")


if __name__ == "__main__":
    main()
