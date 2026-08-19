"""
完整性检查工具 - 命令行入口
用于生成和验证 SHA-256 清单文件

用法:
  python tools/check_integrity.py check           # 校验完整性
  python tools/check_integrity.py generate        # 重新生成清单
  python tools/check_integrity.py update --file src/xxx.py   # 更新单文件哈希
"""
import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.security.integrity import IntegrityChecker


def main():
    import argparse
    parser = argparse.ArgumentParser(description="7tanAI 完整性检查")
    parser.add_argument("action", choices=["check", "generate", "update"],
                        default="check", nargs="?",
                        help="check: 验证, generate: 生成清单, update: 更新文件哈希")
    parser.add_argument("--level", choices=["core", "full"],
                        default="full", help="检查范围 (默认: full)")
    parser.add_argument("--file", help="更新单个文件哈希 (与 update 配合使用)")
    parser.add_argument("--manifest", default="integrity.json", help="清单文件路径")

    args = parser.parse_args()

    root = Path(__file__).parent.parent
    checker = IntegrityChecker(manifest_path=str(root / args.manifest), mode=args.level)

    if args.action == "generate":
        checker.save_manifest(str(root / args.manifest))
        print("[OK] manifest generated: %s" % args.manifest)
    elif args.action == "check":
        report = checker.check_all()
        print("healthy: %s | tampered: %s" % (report.healthy, report.tampered_count))
        for f in (getattr(report, "missing", None) or []):
            print("  MISSING: %s" % f)
        for f, exp, act in (getattr(report, "modified", None) or []):
            print("  MODIFIED: %s (expect %s... actual %s...)" % (f, exp[:12], act[:12]))
        if report.healthy:
            print("[OK] integrity check passed")
        sys.exit(0 if report.healthy else 1)
    elif args.action == "update":
        if not args.file:
            print("ERROR: update needs --file")
            sys.exit(1)
        checker.update_file_hash(args.file)
        print("[OK] hash updated: %s" % args.file)


if __name__ == "__main__":
    main()
