# -*- coding: utf-8 -*-
"""验证新构建的 v1.0.16 发布包是否含敏感信息（只读检查，不执行zip内任何内容）"""
import zipfile, re, sys, io
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ZIPS = [
    r"D:\7tan\7tanAI\dist\release\7tan-editor-v1.0.16.zip",
    r"D:\7tan\7tanAI\dist\release\7tan-web-v1.0.16.zip",
]

# 关键文件清单（进包敏感文件）
KEY_FILES = [
    "7tan-editor/_internal/config/config.yaml",
    "7tan-editor/_internal/config/capabilities.yaml",
    "7tan-editor/7Tan使用说明书.html",
    "7tan-editor/7Tan使用说明书.md",
    "7tan-src/config/config.yaml",
    "7tan-src/src/ui/app.py",
    "7tan-src/src/ui/login_dialog.py",
    "7tan-src/src/ui/welcome_wizard.py",
    "7tan-src/src/utils/user_stats.py",
    "7tan-src/src/web/static/guide.html",
    "7tan-src/src/web/static/index.html",
    "7tan-src/src/core/telemetry.py",
    "7tan-src/src/tools/registry.py",
    "7tan-src/src/web/routes/api_settings.py",
    "7tan-src/src/web/static/app.js",
    "7tan-src/tools/security_src/auth_client_src.py",
    "7tan-src/tools/security_src/device_fingerprint.py",
    "7tan-src/tools/security_src/sec_config.py",
    "7tan-src/tools/security_src/updater.py",
    "7tan-src/data/plugins/self_evolution/tools.py",
    "7tan-src/data/plugins/viral_writer/license.py",
    "7tan-src/data/plugins/hashes.json",
    "7tan-editor/_internal/data/plugins/hashes.json",
    "7tan-editor/_internal/cryptography-49.0.0.dist-info/sboms/cryptography-rust.cyclonedx.json",
]

PATTERNS = {
    "后台域名 img.7tan.cn": r"img\.7tan\.cn",
    "官网 www.7tan.com": r"www\.7tan\.com",
    "明文用户名 admin": r"username:\s*admin",
    "真实key sk-长串": r"sk-[A-Za-z0-9]{16,}",
    "手机号": r"1[3-9]\d{9}",
    "明文base_url(7tan)": r"https?://[a-z0-9.-]*7tan[a-z0-9.-]*",
}

def read_text(zf, name):
    try:
        data = zf.read(name)
        for enc in ("utf-8", "gbk", "latin-1"):
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode("latin-1", errors="replace")
    except Exception as e:
        return None

def find_member(zf, suffix):
    """按后缀模糊查找 zip 内成员（兼容大小写/路径差异）"""
    for n in zf.namelist():
        if n.lower().endswith(suffix.lower()):
            return n
    return None

for zip_path in ZIPS:
    print("=" * 70)
    print("扫描:", zip_path)
    try:
        zf = zipfile.ZipFile(zip_path)
    except Exception as e:
        print("  [错误] 无法打开:", e)
        continue
    names = zf.namelist()
    print("  文件总数:", len(names))
    total_hits = 0
    checked = 0
    # 1) 精确清单
    for kf in KEY_FILES:
        member = kf if kf in names else None
        if member is None:
            base = kf.split("/", 1)[-1]
            member = find_member(zf, base)
        if member is None:
            continue
        text = read_text(zf, member)
        checked += 1
        if text is None:
            continue
        for label, pat in PATTERNS.items():
            ms = re.findall(pat, text)
            if ms:
                total_hits += 1
                shown = [m[:40] for m in ms[:3]]
                print(f"  [命中] {member} | {label}: {shown}")
    # 2) 兜底：对文本类成员全局扫 sk- 与 img.7tan.cn（限文本成员）
    scanned = 0
    for n in names:
        if n.endswith((".yaml", ".py", ".html", ".md", ".js", ".json", ".txt", ".php")):
            scanned += 1
            text = read_text(zf, n)
            if not text:
                continue
            for label, pat in (("后台域名", r"img\.7tan\.cn"), ("真实key", r"sk-[A-Za-z0-9]{16,}")):
                ms = re.findall(pat, text)
                if ms:
                    total_hits += 1
                    print(f"  [命中] {n} | {label}: {[m[:40] for m in ms[:2]]}")
    print(f"  检查文本成员: {scanned} 个 | 敏感命中总数: {total_hits}")
    if total_hits == 0:
        print("  ✅ 结论: 未发现敏感内容，包干净")
    else:
        print("  ⚠️ 结论: 发现敏感内容，需要处理")
    zf.close()
print("=" * 70)
print("验证完成")
