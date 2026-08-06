import sys
import asyncio

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import winsdk.windows.media.ocr as ocr
    import winsdk.windows.graphics.imaging as imaging
    import winsdk.windows.storage as storage
    import winsdk.windows.globalization as globalization
except Exception as e:
    print("import fail:", e, flush=True)
    sys.exit(1)


async def main():
    path = r"D:\7tan\7tanAI\data\screenshots\menu_crop.png"
    file = await storage.StorageFile.get_file_from_path_async(path)
    stream = await file.open_async(storage.FileAccessMode.READ)
    decoder = await imaging.BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    lang = globalization.Language("zh-CN")
    engine = ocr.OcrEngine.try_create_from_language(lang)
    if engine is None:
        engine = ocr.OcrEngine.try_create_from_user_profile_languages()
    result = await engine.recognize_async(bitmap)
    for line in result.lines:
        print(line.text, flush=True)


asyncio.run(main())
