# -*- coding: utf-8 -*-
"""真正测试 zoompan/subtitles 滤镜可用性"""
import subprocess

tests = [
    ("zoompan", 'ffmpeg -hide_banner -y -f lavfi -i color=c=blue:s=720x1280:d=1 -vf "zoompan=z=\'min(zoom+0.01,1.5)\':d=30:s=720x1280:fps=30" -frames:v 5 -f null -'),
    ("subtitles(ass)", 'ffmpeg -hide_banner -y -f lavfi -i color=c=blue:s=720x1280:d=1 -vf "subtitles=f=test.ass" -frames:v 2 -f null -'),
    ("drawtext", 'ffmpeg -hide_banner -y -f lavfi -i color=c=blue:s=720x1280:d=1 -vf "drawtext=text=\'abc\':fontsize=30" -frames:v 2 -f null -'),
]
for name, cmd in tests:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
    err = (r.stderr or '')[-400:]
    ok = r.returncode == 0
    print(f"[{name}] {'OK' if ok else 'FAIL'}")
    if not ok:
        print("   ", err.replace('\n', ' | ')[:350])
