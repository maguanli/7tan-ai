"""检查下载 zip 与本地文件名的中文（ZIP 文件名编码是经典乱码源）。"""
import os
import sys
import zipfile

DOWNLOADS = r"D:\7tan\7tanAI\webmirror\downloads"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zip_name_result.txt")


def main():
    lines = []
    # 1) 本地是否有非 ASCII 文件名
    non_ascii = []
    for base, dirs, files in os.walk(DOWNLOADS):
        for n in list(dirs) + files:
            if any(ord(c) > 127 for c in n):
                non_ascii.append(os.path.join(base, n))
    lines.append(f"本地非 ASCII 文件名: {len(non_ascii)} 个")
    for p in non_ascii[:20]:
        lines.append("   " + os.path.relpath(p, DOWNLOADS))

    # 2) 检查已生成的 zip
    zips = [p for p in (os.path.join(DOWNLOADS, "_zips", f)
                        for f in os.listdir(os.path.join(DOWNLOADS, "_zips")))
            if p.endswith(".zip")]
    lines.append(f"\n已有 zip: {len(zips)} 个")
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            infos = zf.infolist()
            bad = []
            for i in infos:
                # 有 UTF-8 标志位(0x800) 或全 ASCII 才算正常
                if any(ord(c) > 127 for c in i.filename) and not (i.flag_bits & 0x800):
                    bad.append(i.filename)
            names_ok = all(i.filename == i.orig_filename for i in infos)
            lines.append(f"   {os.path.basename(z)}: {len(infos)} 项, "
                         f"缺 UTF-8 标志的中文名 {len(bad)} 个, "
                         f"名字可解码={names_ok}")
            for b in bad[:10]:
                lines.append(f"      ! {b}")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("done ->", OUT)


if __name__ == "__main__":
    main()
