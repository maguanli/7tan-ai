import sys
import asyncio

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
from PIL import Image

# 截取微信窗口
img = pyautogui.screenshot(region=(600, 300, 440, 480))
img.save(r"D:\7tan\7tanAI\data\screenshots\wc_full.png")

# 消息在 y=560(相对480的260)，时间戳应在 y 480-540 (相对窗口 180-240)
# 裁剪消息上方区域并放大3倍
crop = img.crop((0, 150, 440, 265))  # 相对窗口 y:150-265 -> 绝对 450-565
crop = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
crop.save(r"D:\7tan\7tanAI\data\screenshots\wc_timestamp_zoom.png")
print("saved zoom", flush=True)

# 顶部区域也截一下（可能对象名/时间）
crop2 = img.crop((0, 0, 440, 150))
crop2 = crop2.resize((crop2.width * 3, crop2.height * 3), Image.LANCZOS)
crop2.save(r"D:\7tan\7tanAI\data\screenshots\wc_top_zoom.png")
print("saved top", flush=True)


async def ocr_file(path):
    import winsdk.windows.media.ocr as ocr
    import winsdk.windows.graphics.imaging as imaging
    import winsdk.windows.storage as storage
    import winsdk.windows.globalization as globalization

    file = await storage.StorageFile.get_file_from_path_async(path)
    stream = await file.open_async(storage.FileAccessMode.READ)
    decoder = await imaging.BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    lang = globalization.Language("zh-CN")
    engine = ocr.OcrEngine.try_create_from_language(lang)
    result = await engine.recognize_async(bitmap)
    return [line.text for line in result.lines]


async def main():
    print("== timestamp area ==", flush=True)
    for t in await ocr_file(r"D:\7tan\7tanAI\data\screenshots\wc_timestamp_zoom.png"):
        print(repr(t), flush=True)
    print("== top area ==", flush=True)
    for t in await ocr_file(r"D:\7tan\7tanAI\data\screenshots\wc_top_zoom.png"):
        print(repr(t), flush=True)


asyncio.run(main())
