# -*- coding: utf-8 -*-
"""验证发布 zip：结构 / 敏感文件 / 完整性（ASCII 输出）"""
import zipfile
from pathlib import Path

ZIP = Path("dist/release/7tan-editor-v1.0.6.zip")
SENSITIVE = [".encryption_key", ".encryption_salt", "games.db", "auth/", "memory/",
             "sandbox/", "screenshots/", "_build", "_python", ".pem", "token", "credentials"]

print(f"[1] zip exists: {ZIP.exists()}  {ZIP.stat().st_size/1048576:.1f} MB")

with zipfile.ZipFile(ZIP) as zf:
    names = zf.namelist()
    print(f"[2] total files: {len(names)}")

    has_exe = any(n.endswith("7tan-editor.exe") for n in names)
    has_internal = any("/_internal/" in n for n in names)
    has_readme = "README.txt" in names
    has_build_info = "BUILD_INFO.txt" in names
    print(f"[3] structure: exe={has_exe} _internal={has_internal} README={has_readme} BUILD_INFO={has_build_info}")

    bad_src = [n for n in names if "/_build/" in n or "/_python/" in n or "rebuild.bat" in n]
    print(f"[4] source/python leftover: {len(bad_src)}  {'[OK] none' if not bad_src else bad_src[:5]}")

    bad_sens = [n for n in names if any(s in n.lower() for s in SENSITIVE)]
    print(f"[5] sensitive files: {len(bad_sens)}  {'[OK] none' if not bad_sens else bad_sens[:5]}")

    exe_names = [n for n in names if n.endswith("7tan-editor.exe")]
    if exe_names:
        exe_info = zf.getinfo(exe_names[0])
        print(f"[6] exe size: {exe_info.file_size/1048576:.1f} MB (zip {exe_info.compress_size/1048576:.1f} MB)")

    tops = sorted(set(n.split("/")[0] for n in names))
    print(f"[7] top-level: {tops}")

    # 抽查语音组件
    voice = [n for n in names if "piper" in n.lower() or "onnxruntime" in n.lower() or "edge_tts" in n.lower()]
    print(f"[8] voice components: {len(voice)} files")

    # 抽查视频编辑组件
    video = [n for n in names if "imageio_ffmpeg" in n.lower() or "ffmpeg" in n.lower()]
    print(f"[9] video/ffmpeg components: {len(video)} files")

print("[DONE] verification complete")
