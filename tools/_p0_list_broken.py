# -*- coding: utf-8 -*-
import sys, zipfile
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RELEASE = Path(r"D:\7tan\7tanAI\dist\release")
for zname in sorted(RELEASE.glob("*.zip")):
    with zipfile.ZipFile(zname) as zf:
        hits = [n for n in zf.namelist() if "broken" in n.lower()]
    print(f"== {zname.name} ==")
    for h in hits:
        print(f"   {h}")
    print()
