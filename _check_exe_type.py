# -*- coding: utf-8 -*-
"""判断当前 exe 是 onefile 还是 onedir 产物"""
import os, struct

exe = r"D:\7tan\7tanAI\dist\7tan-editor\7tan-editor.exe"
size = os.path.getsize(exe)

with open(exe, "rb") as f:
    data = f.read()

# 找 CArchive 头 (MEI\014\013\012\013\016 在文件末尾附近)
pos = data.find(b"MEI\x0c\x0b\x0a\x0b\x0e")
print(f"exe: {size} bytes, CArchive头偏移: {pos}")

if pos > 0:
    # 解析 CArchive 头 (32字节: magic 8 + lengthofpackage 4 + toc 4 + toc_len 4 + pyvers 4 + pylibname 8)
    hdr = data[pos:pos+32]
    magic, length, toc_offset, toc_len, pyvers = struct.unpack(">8sIIIi", hdr[:24])
    print(f"magic={magic}, package_len={length}, toc_offset={toc_offset}, toc_len={toc_len}, pyvers={pyvers}")
    # 读 TOC 前几项
    toc_start = pos + toc_offset
    toc_data = data[toc_start:toc_start+toc_len]
    entries = []
    off = 0
    while off < len(toc_data) and len(entries) < 20:
        # CArchive TOC 项: entry_len(4) + offset(4) + compress_len(4) + uncomp_len(4) + compress_flag(1) + type_char(1) + name
        entry_len = struct.unpack(">i", toc_data[off:off+4])[0]
        if entry_len <= 0:
            break
        entry_off, clen, ulen, cflag, tchar = struct.unpack(">iiiiBc", toc_data[off+4:off+21])
        name = toc_data[off+21:off+entry_len].split(b"\x00")[0].decode("utf-8", errors="replace")
        entries.append((name, tchar.decode(), clen))
        off += entry_len
    print("TOC 条目(前20):")
    for n, t, l in entries:
        print(f"   {t} {n} ({l}B)")

# 检查 _internal 里有没有 python312.zip / PYZ 类似物
internal = r"D:\7tan\7tanAI\dist\7tan-editor\_internal"
print("\n_internal 关键文件:")
for f in sorted(os.listdir(internal)):
    full = os.path.join(internal, f)
    if os.path.isfile(full):
        print(f"  {f} ({os.path.getsize(full)}B)")
