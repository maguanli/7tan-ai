# -*- coding: utf-8 -*-
"""检查 dist/release 中的 zip 是否含敏感文件/密钥，避免公开泄露

用法:
    python check_zip_secrets.py                # 自动扫描 dist/release/*.zip
    python check_zip_secrets.py <zip路径>...   # 指定 zip 扫描

发现敏感内容时退出码=1（供构建脚本预警），否则 0。
"""
import zipfile, re, os, sys, glob

DEFAULT_ZIP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "release")

SENSITIVE_NAME = re.compile(
    r"(\.env$|\.env\.|\.pem$|\.key$|\.p12$|\.pfx$|\.db$|\.sqlite"
    r"|secrets?|token|credential|password|passwd|id_rsa|\.sig$)", re.I)

KEY_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "DeepSeek/OpenAI/sensetime sk-"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "GitHub token"),
    (re.compile(r"ark-[A-Za-z0-9]{20,}"), "Volcano ark"),
    (re.compile(r"AKLT[A-Za-z0-9]{16,}"), "Zhipu AKLT"),
    (re.compile(r"aizj[A-Za-z0-9]{16,}"), "Ali aizj"),
    (re.compile(r"Bearer\s+[A-Za-z0-9\-_.]{20,}"), "Bearer token"),
    (re.compile(r"1[3-9]\d{9}"), "手机号"),
    (re.compile(r"\d{17}[\dXx]"), "身份证号"),
    (re.compile(r"img\.7tan\.cn"), "7tan 管理后台/API 域名"),
    (re.compile(r"www\.7tan\.com"), "7tan 主站域名"),
    (re.compile(r"username:\s*admin"), "默认后台用户名 admin"),
    (re.compile(r"base_url:\s*https?://"), "config 明文站点地址"),
]

# 注意：config.yaml 本身是软件运行必需（含站点配置/占位符），不列入敏感名；
# 但 config.yaml 里若出现明文 sk- 密钥，会被 KEY_PATTERNS 内容扫描抓到。
SENSITIVE_NAME = re.compile(
    r"(\.env$|\.env\.|\.pem$|\.key$|\.p12$|\.pfx$|\.db$|\.sqlite"
    r"|\.encryption_key|auth/|memory/|secrets?|token|credential|id_rsa|\.sig$)", re.I)


def scan_zip(path):
    print("=" * 70)
    print("扫描:", os.path.basename(path), f"({os.path.getsize(path)/1024/1024:.1f}MB)")
    try:
        z = zipfile.ZipFile(path)
    except Exception as e:
        print("  [错误] 无法打开:", e)
        return False
    names = z.namelist()
    print(f"  文件总数: {len(names)}")
    danger = False
    # 1) 文件名敏感
    hits = [n for n in names if SENSITIVE_NAME.search(n)]
    if hits:
        danger = True
        print(f"  [危险] 敏感文件名 {len(hits)} 个:")
        for h in hits[:50]:
            print("    -", h)
    else:
        print("  [OK] 无敏感文件名")
    # 2) 抽查关键文本文件内容（源码 py/txt/json/yaml 等，限于可读文本）
    text_ext = (".py", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini",
                ".cfg", ".md", ".env", ".sh", ".bat", ".html", ".js", ".ts")
    scanned = 0
    key_hits = []
    for n in names:
        low = n.lower()
        if not low.endswith(text_ext):
            continue
        if low.endswith((".min.js", ".min.css")):
            continue
        try:
            data = z.read(n)
        except Exception:
            continue
        if len(data) > 300_000:  # 跳过超大文件
            continue
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            continue
        scanned += 1
        for pat, label in KEY_PATTERNS:
            m = pat.search(text)
            if m:
                key_hits.append((n, label, m.group(0)[:30]))
                break  # 每文件只记一条
    print(f"  抽查文本文件: {scanned} 个")
    if key_hits:
        danger = True
        print(f"  [危险] 发现疑似密钥/隐私 {len(key_hits)} 处:")
        for n, label, sample in key_hits[:40]:
            print(f"    - {n}  [{label}] {sample}...")
    else:
        print("  [OK] 未发现疑似密钥/隐私")
    z.close()
    return not danger


def main():
    args = sys.argv[1:]
    if args:
        zips = args
    else:
        zips = sorted(glob.glob(os.path.join(DEFAULT_ZIP_DIR, "*.zip")))
    if not zips:
        print("未找到 zip 文件:", DEFAULT_ZIP_DIR)
        sys.exit(0)
    ok = True
    for p in zips:
        if os.path.exists(p):
            ok = scan_zip(p) and ok
        else:
            print("跳过(不存在):", p)
    print("=" * 70)
    if ok:
        print("检查完成：所有 zip 均未发现敏感内容 ✅")
        sys.exit(0)
    else:
        print("检查完成：发现敏感内容 ⚠️ 请勿分发该 zip！")
        sys.exit(1)


if __name__ == "__main__":
    main()
