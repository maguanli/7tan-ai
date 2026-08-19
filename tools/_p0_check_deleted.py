# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

files = [
    r"D:\7tan\7tanAI\dist\_python\Lib\idlelib\idle_test\test_autocomplete.py",
    r"D:\7tan\7tanAI\dist\_python\Lib\site-packages\Crypto\SelfTest\Cipher\test_AES.py",
    r"D:\7tan\7tanAI\dist\_python\Lib\site-packages\aiohttp\test_utils.py",
    r"D:\7tan\7tanAI\dist\_python\Lib\site-packages\pytest\__init__.py",
    r"D:\7tan\7tanAI\dist\7tan-editor\_internal\tzdata\zoneinfo\Australia\Broken_Hill",
    r"D:\7tan\7tanAI\dist\_build\data\sandbox\test_13ff69519d50_1785503445.py",
    r"D:\7tan\7tanAI\dist\_build\data\_check_chat.py",
    r"D:\7tan\7tanAI\dist\_build\src\agent\model_manager.py.bak",
]
for f in files:
    p = Path(f)
    print(("EXISTS " if p.exists() else "DELETED"), f)
