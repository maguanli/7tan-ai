# -*- coding: utf-8 -*-
"""重新打包：剔除用户数据/隐私文件，生成 GitHub Release 干净发布包"""
import zipfile, os, re, shutil, time

SRC = r"D:\7tan\7tanAI\dist\release"
DST = r"D:\7tan\7tanAI\dist\release\github"
os.makedirs(DST, exist_ok=True)

ZIPS = [
    "7tan-editor-v1.0.13.zip",
    "7tan-editor-free-v1.0.13.zip",
    "7tan-web-v1.0.13.zip",
]

# 排除规则（路径片段，统一小写匹配）
EXCLUDE_PARTS = (
    "/ocr_work/",            # 微信截图+OCR文本（含手机号）
    "/data/uploads/",        # 用户上传数据
    "/data/screenshots/",    # 用户截图
    "/data/camera_vision/",  # 摄像头抓拍
    "/data/recordings/",     # 录音
    "/data/downloads/",      # 下载缓存
    "/data/output/",         # 输出
    "/backups/",             # 备份（含旧数据库）
    "/logs/",                # 日志
)
EXCLUDE_EXT = (".db", ".sqlite", ".db-wal", ".db-shm", ".p12", ".pfx", ".sig")
# 私钥类文件名（cacert.pem 是CA证书必须保留）
EXCLUDE_PEM_KEY = ("private", "id_rsa", "id_ed25519", "server.key", "secret.key")

def is_private_key(name):
    low = name.lower()
    if not (low.endswith(".pem") or low.endswith(".key")):
        return False
    return any(k in low for k in EXCLUDE_PEM_KEY)
EXCLUDE_EXACT = {".env"}

def should_exclude(name):
    low = name.lower()
    if any(p in low for p in EXCLUDE_PARTS):
        return True
    if low.endswith(EXCLUDE_EXT):
        return True
    if is_private_key(low):
        return True
    base = os.path.basename(low)
    if base in EXCLUDE_EXACT:
        return True
    return False

for zp in ZIPS:
    src_path = os.path.join(SRC, zp)
    dst_path = os.path.join(DST, zp)
    t0 = time.time()
    zin = zipfile.ZipFile(src_path)
    excluded = []
    total = 0
    with zipfile.ZipFile(dst_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zout:
        for item in zin.infolist():
            total += 1
            if should_exclude(item.filename):
                excluded.append(item.filename)
                continue
            data = zin.read(item.filename)
            zout.writestr(item, data)
    zin.close()
    dt = time.time() - t0
    newsize = os.path.getsize(dst_path)
    print(f"{zp}: 总{total} 排除{len(excluded)} → {newsize/1024/1024:.1f}MB ({dt:.0f}s)")
    for e in excluded[:30]:
        print("   排除:", e)
    if len(excluded) > 30:
        print(f"   ... 等 {len(excluded)} 个")
print("全部完成，输出目录:", DST)
