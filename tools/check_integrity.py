"""
完整性检查工具 — 命令行入口
用于生成和验证 SHA-256 清单文件
"""
import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.security.integrity import IntegrityChecker


def main():
    import argparse
    parser = argparse.ArgumentParser(description="7坛AI小编 完整性检查")
    parser.add_argument("action", choices=["check", "generate", "update"],
                        default="check", nargs="?",
                        help="check: 验证, generate: 生成清单, update: 更新文件哈希")
    parser.add_argument("--level", choices=["critical", "standard", "loose", "full"],
                        default="critical", help="检查级别 (默认: critical)")
    parser.add_argument("--file", help="更新单个文件哈希 (与 update 配合使用)")
    parser.add_argument("--manifest", default="integrity.json", help="清单文件路径")

    args = parser.parse_args()

    root = Path(__file__).parent.parent
    checker = IntegrityChecker(root=root)

    if args.action == "generate":
        report = checker.generate_manifest(args.manifest, level=args.level)
        print(report)
    elif args.action == "check":
        ok = checker.check_all(level=args.level)
        report = checker._report
        if report:
            print(report)
        sys.exit(0 if ok else 1)
    elif args.action == "update":
        if not args.file:
            print("❌ update 需要 --file 参数")
            sys.exit(1)
        checker.update_file_hash(args.manifest, args.file)
        print(f"✅ 已更新 {args.file} 的哈希值")


if __name__ == "__main__":
    main()
