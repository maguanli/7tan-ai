# -*- coding: utf-8 -*-
"""解析新 exe CArchive 结构 + 运行测试"""
import os, struct, subprocess, time

exe = r"D:\7tan\7tanAI\dist\7tan-editor\7tan-editor.exe"
size = os.path.getsize(exe)

with open(exe, "rb") as f:
    data = f.read()

pos = data.find(b"MEI\x0c\x0b\x0a\x0b\x0e")
out = []
out.append("exe: %d bytes" % size)
out.append("CArchive头偏移: %s" % pos)

if pos > 0:
    hdr = data[pos:pos+32]
    magic, length, toc_offset, toc_len, pyvers = struct.unpack(">8sIIIi", hdr[:24])
    out.append("package_len=%d toc_offset=%d toc_len=%d pyvers=%d" % (length, toc_offset, toc_len, pyvers))
    toc_start = pos + toc_offset
    toc_data = data[toc_start:toc_start+toc_len]
    entries = []
    off = 0
    while off < len(toc_data) and len(entries) < 30:
        entry_len = struct.unpack(">i", toc_data[off:off+4])[0]
        if entry_len <= 0:
            break
        entry_off, clen, ulen, cflag, tchar = struct.unpack(">iiiiBc", toc_data[off+4:off+21])
        name = toc_data[off+21:off+entry_len].split(b"\x00")[0].decode("utf-8", errors="replace")
        entries.append((name, tchar.decode(), clen))
        off += entry_len
    out.append("TOC 条目(前30):")
    for n, t, l in entries:
        out.append("   %s %s (%dB)" % (t, n, l))
    out.append("...共 %d 条" % len(entries))

# 检查 exe 里是否包含 PYZ 数据（内嵌）
pyz_marker = b"PYZ\x00"
out.append("\nexe 内 'PYZ\\x00' 出现次数: %d" % data.count(pyz_marker))

# 运行 exe 测试 30 秒
out.append("\n=== 运行测试 (30s) ===")
try:
    p = subprocess.Popen([exe], cwd=r"D:\7tan\7tanAI\dist\7tan-editor")
    time.sleep(30)
    if p.poll() is None:
        out.append("STILL-RUNNING (pid %d) -> GUI 存活" % p.pid)
        p.terminate()
        time.sleep(2)
        if p.poll() is None:
            p.kill()
        out.append("terminated")
    else:
        out.append("EXITED code=%s" % p.returncode)
except Exception as e:
    out.append("异常: %s" % e)

# 日志检查
logdir = r"D:\7tan\7tanAI\dist\7tan-editor\logs"
if os.path.isdir(logdir):
    for f in sorted(os.listdir(logdir)):
        pth = os.path.join(logdir, f)
        out.append("  log: %s (%dB)" % (f, os.path.getsize(pth)))
else:
    out.append("logs 目录不存在")

with open(r"D:\7tan\7tanAI\_exe_verify.txt", "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("ok")
