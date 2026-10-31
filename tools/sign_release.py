# -*- coding: utf-8 -*-
"""
发布包签名工具 — 为更新包生成 .sig（RSA-2048 / PKCS#1 v1.5 / SHA-256）

背景
----
客户端 src/core/updater.pyd 下载更新包时会再取 <zip>.sig，用**内嵌公钥**验签，
验不过直接拒装。以前这一步是手工做的，仓库里没有脚本，这次补上。

签名契约（与 updater.pyd 的 verify_update_signature_with_hash 严格对齐）
------------------------------------------------------------------------
    digest  = SHA256(zip 全部字节)          # 32 字节原始摘要
    sig     = RSAPrivateKey.sign(digest, PKCS1v15(), SHA256())
    .sig    = base64(sig)                   # 单行 ASCII 文本

注意两点，写错了就永远验不过：
  1. 签的是**摘要的 32 字节**，不是文件内容，也不是 hex 字符串
  2. 公钥必须与 src/security/sec_config.pyd 内嵌的那把配对
     （website/config/public_key.pem 已核与内嵌公钥逐字一致）

用法
----
    python tools/sign_release.py dist/7tan-editor-free-v1.0.23.zip
    python tools/sign_release.py --all dist/
    python tools/sign_release.py --verify dist/xxx.zip
    python tools/sign_release.py --selftest

选项
----
    --key PATH      私钥路径（默认 website/config/private_key.pem）
    --outdir DIR    输出目录（默认与 zip 同目录）
    --also-updates  同时在 website/updates/ 写一份 .sig
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 从 tools/ 启动时 sys.path[0] 是 tools/，这里补上项目根，才能导入 src.security
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_KEY = ROOT / "website" / "config" / "private_key.pem"
UPDATES_DIR = ROOT / "website" / "updates"

CHUNK = 1 << 20


# ---------------------------------------------------------------- 基础

def sha256_file(path: str | Path) -> bytes:
    """整文件 SHA-256，返回 32 字节原始摘要"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.digest()


def load_private_key(key_path: str | Path = DEFAULT_KEY):
    """读取 PEM 私钥。缺文件/格式错给出明确报错，不做静默回退。"""
    from cryptography.hazmat.primitives import serialization

    key_path = Path(key_path)
    if not key_path.exists():
        raise FileNotFoundError(f"私钥不存在: {key_path}")
    pem = key_path.read_bytes()
    if b"PRIVATE KEY" not in pem:
        raise ValueError(f"不是 PEM 私钥文件: {key_path}")
    key = serialization.load_pem_private_key(pem, password=None)
    # 与客户端内嵌公钥配对性检查：不配对就不该继续（否则签了也白签）
    # 内嵌公钥在 src/security/strings（编译进 strings.pyd / 包内 strings 模块）
    try:
        from src.security.strings import get_public_key as _gp
        embedded = _gp()
    except Exception:
        embedded = None  # 源码树外运行时无法取到内嵌公钥，跳过但不假装检查过
    if embedded:
        from cryptography.hazmat.primitives import serialization as _s
        derived = key.public_key().public_bytes(
            _s.Encoding.PEM, _s.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        if derived.strip() != embedded.strip():
            raise ValueError(
                "私钥与客户端内嵌公钥不配对，签出的 .sig 客户端一定验不过"
            )
    return key


def sign_digest(key, digest: bytes) -> str:
    """对 32 字节摘要签名，返回 base64 单行文本"""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    if len(digest) != 32:
        raise ValueError(f"摘要长度应为 32 字节，实际 {len(digest)}")
    sig = key.sign(digest, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(sig).decode("ascii")


def verify_with_shipped(zip_path: str | Path, sig_b64: str) -> bool:
    """
    用**生产环境同一个**验签函数校验（src/security/sec_config.pyd）。
    注意：这里不自己实现 RSA 验签，避免“自己验自己”的假通过。
    """
    from src.security.sec_config import verify_update_signature_with_hash

    digest = sha256_file(zip_path)
    return bool(verify_update_signature_with_hash(digest.hex(), sig_b64))


# ---------------------------------------------------------------- 主流程

def sign_file(zip_path: str | Path, key_path: str | Path = DEFAULT_KEY,
              outdir: str | Path | None = None,
              also_updates: bool = False) -> dict:
    """
    为一个 zip 生成 .sig，并在写盘后用生产验签函数复核。
    返回 {zip, sig_path, sig_bytes, digest, size, verified}
    """
    zip_path = Path(zip_path)
    if not zip_path.exists():
        raise FileNotFoundError(f"更新包不存在: {zip_path}")
    if zip_path.suffix.lower() != ".zip":
        raise ValueError(f"只对 .zip 签名，收到: {zip_path.name}")

    key = load_private_key(key_path)
    digest = sha256_file(zip_path)
    sig_b64 = sign_digest(key, digest)

    # 自校验：签名必须能被生产验签函数接受
    if not verify_with_shipped(zip_path, sig_b64):
        raise RuntimeError(f"签名自检未通过，已中止: {zip_path.name}")

    out_dir = Path(outdir) if outdir else zip_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    sig_path = out_dir / (zip_path.name + ".sig")
    sig_path.write_text(sig_b64 + "\n", encoding="ascii")

    targets = [sig_path]
    if also_updates and out_dir.resolve() != UPDATES_DIR.resolve():
        UPDATES_DIR.mkdir(parents=True, exist_ok=True)
        p2 = UPDATES_DIR / (zip_path.name + ".sig")
        p2.write_text(sig_b64 + "\n", encoding="ascii")
        targets.append(p2)

    return {
        "zip": str(zip_path),
        "sig_path": str(sig_path),
        "sig_paths": [str(t) for t in targets],
        "sig_bytes": len(base64.b64decode(sig_b64)),
        "digest": digest.hex(),
        "size": zip_path.stat().st_size,
        "verified": True,
    }


def verify_file(zip_path: str | Path, sig_path: str | Path | None = None) -> tuple[bool, str]:
    """校验已有 .sig"""
    zip_path = Path(zip_path)
    sig_path = Path(sig_path) if sig_path else Path(str(zip_path) + ".sig")
    if not zip_path.exists():
        return False, f"更新包不存在: {zip_path}"
    if not sig_path.exists():
        return False, f"签名文件不存在: {sig_path}"
    text = sig_path.read_text(encoding="ascii", errors="replace").strip()
    if not text:
        return False, "签名文件为空"
    try:
        base64.b64decode(text, validate=True)
    except Exception as exc:
        return False, f"签名不是合法 base64: {exc}"
    ok = verify_with_shipped(zip_path, text)
    return ok, ("验签通过" if ok else "验签失败（包被改过，或公钥不匹配）")


# ---------------------------------------------------------------- 自检

def selftest() -> int:
    """正向 + 反向，每一条都必须给出预期结果"""
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))

    tmpdir = Path(tempfile.mkdtemp(prefix="sigtest_"))
    try:
        key = load_private_key()

        # 1 正常签名
        f1 = tmpdir / "a.zip"
        f1.write_bytes(os.urandom(200_000))
        info = sign_file(f1)
        check("1 正常签名并可验签", info["verified"], f"{info['size']} 字节")
        check("2 .sig 存在且非空", Path(info["sig_path"]).exists()
              and Path(info["sig_path"]).stat().st_size > 0)
        check("3 签名长度 256 字节(2048位密钥)", info["sig_bytes"] == 256,
              f"实际 {info['sig_bytes']}")

        # 4 签名内容是单行 base64
        text = Path(info["sig_path"]).read_text(encoding="ascii").strip()
        check("4 单行 base64", "\n" not in text and " " not in text)

        # 5 篡改一个字节 → 必须失败
        f2 = tmpdir / "b.zip"
        data = bytearray(f1.read_bytes())
        data[100_000] ^= 0xFF
        f2.write_bytes(bytes(data))
        sig_text = Path(info["sig_path"]).read_text(encoding="ascii").strip()
        check("5 篡改后验签失败", verify_with_shipped(f2, sig_text) is False)

        # 6 换另一份文件的签名 → 必须失败
        f3 = tmpdir / "c.zip"
        f3.write_bytes(os.urandom(1000))
        info3 = sign_file(f3)
        sig3 = Path(info3["sig_path"]).read_text(encoding="ascii").strip()
        check("6 张冠李戴的签名被拒", verify_with_shipped(f1, sig3) is False)

        # 7 空签名 → 必须失败
        check("7 空签名被拒", verify_with_shipped(f1, "") is False)

        # 8 坏 base64 → 必须失败
        check("8 非法 base64 被拒", verify_with_shipped(f1, "!!!not-base64!!!") is False)

        # 9 对文件原文签名（错做法）→ 必须失败
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        wrong = base64.b64encode(
            key.sign(f1.read_bytes(), padding.PKCS1v15(), hashes.SHA256())
        ).decode()
        check("9 对原文签名被拒(契约是签摘要)", verify_with_shipped(f1, wrong) is False)

        # 10 非 zip 拒绝
        f4 = tmpdir / "d.txt"
        f4.write_text("x")
        try:
            sign_file(f4)
            check("10 非 zip 被拒", False, "竟然通过了")
        except ValueError:
            check("10 非 zip 被拒", True)

        # 11 缺私钥报错清晰
        try:
            load_private_key(tmpdir / "nokey.pem")
            check("11 缺私钥给明确报错", False, "竟然没报错")
        except FileNotFoundError:
            check("11 缺私钥给明确报错", True)

        # 12 重复签名结果一致（RSA PKCS1v15 是确定性的）
        s1 = sign_digest(key, sha256_file(f1))
        s2 = sign_digest(key, sha256_file(f1))
        check("12 同一文件重复签名一致", s1 == s2)

    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    print(f"\n合计 {passed}/{len(results)} 通过")
    return 0 if passed == len(results) else 1


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="为更新包生成 RSA 签名 (.sig)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("zip", nargs="*", help="要签名的 zip 路径")
    ap.add_argument("--all", metavar="DIR", help="对该目录下所有 *.zip 签名")
    ap.add_argument("--verify", metavar="ZIP", help="仅校验已有 .sig")
    ap.add_argument("--key", default=str(DEFAULT_KEY), help="私钥路径")
    ap.add_argument("--outdir", help=".sig 输出目录")
    ap.add_argument("--also-updates", action="store_true", help="同时写到 website/updates/")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.verify:
        ok, msg = verify_file(Path(args.verify))
        print(("✅ " if ok else "❌ ") + msg)
        return 0 if ok else 1

    targets: list[Path] = [Path(p) for p in args.zip]
    if args.all:
        d = Path(args.all)
        if not d.is_dir():
            print(f"❌ 不是目录: {d}")
            return 2
        targets += sorted(d.glob("*.zip"))
    if not targets:
        ap.print_help()
        return 2

    failed = 0
    for t in targets:
        try:
            info = sign_file(t, args.key, args.outdir, args.also_updates)
            print(f"✅ {Path(info['zip']).name}")
            print(f"   大小   {info['size']:,} 字节 ({info['size'] / 1048576:.1f} MB)")
            print(f"   SHA256 {info['digest']}")
            print(f"   签名   {info['sig_bytes']} 字节")
            for p in info["sig_paths"]:
                print(f"   → {p}")
        except Exception as exc:
            print(f"❌ {Path(t).name}: {exc}")
            failed += 1

    print(f"\n完成 {len(targets) - failed}/{len(targets)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
