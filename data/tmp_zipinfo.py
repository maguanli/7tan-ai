# -*- coding: utf-8 -*-
"""临时脚本：对比两个 web zip 包的信息（文件数/大小/内部版本/时间）"""
import zipfile, os, sys, hashlib

base = r"D:\7tan\7tanAI\dist\release"
for name in ["7tan-web-v1.0.12.zip", "7tan-web-v2.3.2.zip"]:
    p = os.path.join(base, name)
    if not os.path.exists(p):
        print(name, "=> 不存在")
        continue
    with zipfile.ZipFile(p) as z:
        infos = z.infolist()
        total = sum(i.file_size for i in infos)
        print("=" * 60)
        print(name, "| 文件数:", len(infos), "| 解压后总大小: %.1f MB" % (total / 1048576))
        print("ZIP 创建时间:", os.path.getmtime(p))
        # 找关键文件
        keys = [i for i in infos if any(k in i.filename.lower() for k in ["启动网页", "start", "readme", "version", ".bat", ".command", ".sh", "platform_adapter"])]
        for i in keys[:20]:
            print("  ", i.filename, "|", i.file_size, "B")
