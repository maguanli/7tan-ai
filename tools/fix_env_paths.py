# -*- coding: utf-8 -*-
"""修正环境引擎 installed_software 表中 G 盘 → D 盘/C 盘的安装路径"""
import sqlite3, shutil, os, datetime

DB = r"D:\7tan\7tanAI\data\games.db"
BAK = r"D:\7tan\7tanAI\data\games.db.bak_pathfix_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# 备份
shutil.copy2(DB, BAK)
print("[OK] backup:", BAK)

conn = sqlite3.connect(DB)
cur = conn.cursor()

# (id, 新install_path, 新executable, 新version, notes追加说明)
updates = [
    (1,  r"D:\ffmpeg\bin\ffmpeg.exe",            "ffmpeg",            "9.0.1", "已从G盘迁移到D盘(ffmpeg 9.0.1 essentials)"),
    (4,  r"D:\nodejs",                           r"D:\nodejs\node.exe", "22.16.0", "已从G盘迁移到D盘"),
    (5,  r"D:\7-Zip",                            r"D:\7-Zip\7za.exe", "26.02", "已从G盘迁移到D盘(原7z.exe改为7za.exe)"),
    (17, r"C:\Program Files\Android\Android Studio", r"bin\studio64.exe", "2025.2.2.15", "按用户要求安装到C盘(2025.2.2.15)"),
    (18, r"D:\Android\Java\jdk-21.0.6+7",        r"bin\java.exe",     "21.0.6", "已从G盘迁移到D盘(Microsoft OpenJDK 21.0.6 LTS)"),
    (20, r"D:\gradle_cache",                     r"gradle.bat",       "8.10",  "已从G盘迁移到D盘(gradle-8.10)"),
    (21, r"D:\Android\Sdk",                      r"",                 "",      "已从G盘迁移到D盘(含platform-tools 37.0.1/build-tools 35.0.0/android-35)"),
    (25, r"D:\whisper_cpp",                      r"whisper-cli.exe",  "small", "已从G盘迁移到D盘(源码,需先编译Release)"),
    (26, r"D:\godot",                            r"D:\godot\Godot_v4.7.1-stable_win64.exe", "4.7.1", "已从G盘迁移到D盘"),
    (27, r"D:\Unity\UnityHub",                   r"D:\Unity\UnityHub\Unity Hub.exe", "3.x", "已从G盘迁移到D盘"),
    (28, r"D:\Unity\Editor\2022.3\Editor",       r"D:\Unity\Editor\2022.3\Editor\Unity.exe", "2022.3.62f3", "已从G盘迁移到D盘"),
    (41, r"D:\AI_Video\stable-diffusion-webui",  r"webui.bat",        "1.x",  "已从G盘迁移到D盘"),
    (42, r"D:\AI_Video\comfyui\ComfyUI",         r"main.py",          "latest", "已从G盘迁移到D盘"),
    (43, r"D:\AI_Video\stable-diffusion-webui\models\Stable-diffusion", r"AnythingV5Ink_ink.safetensors", "v5Ink", "已从G盘迁移到D盘(官方Ink变体2GB)"),
]

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
for sid, path, exe, ver, note in updates:
    cur.execute("""UPDATE installed_software
                   SET install_path=?, executable=?, version=?, is_working=1,
                       notes=?, updated_at=?
                   WHERE id=?""", (path, exe, ver, note, now, sid))
    print(f"  id={sid}: rows={cur.rowcount}")

conn.commit()

# 复查仍含 G:\ 的记录
cur.execute("SELECT id, name, install_path FROM installed_software WHERE install_path LIKE 'G:%' OR executable LIKE 'G:%'")
left = cur.fetchall()
print("\n[WARN] still G-drive:", left if left else "none")

conn.close()
print("\n[OK] db updated")
