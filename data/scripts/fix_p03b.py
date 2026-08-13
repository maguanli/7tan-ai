# -*- coding: utf-8 -*-
"""
P0-3 重试统一修复（续）：
2. agent_loop 顶层重试 5 次 → 3 次，不可重试错误直接抛
3. tools/check_integrity.py 适配新版 IntegrityChecker 接口
（model_manager.py 已在上一轮完成）
"""
from pathlib import Path

ROOT = Path(r"D:\7tan\7tanAI")


def patch_agent_loop():
    p = ROOT / "src" / "agent" / "agent_loop.py"
    src = p.read_text(encoding="utf-8")

    # import is_retryable_error（幂等）
    old_imp = "from .model_manager import track_cost_internal, _fix_surrogates"
    new_imp = ("from ..utils.retry import is_retryable_error\n"
               "from .model_manager import track_cost_internal, _fix_surrogates")
    if old_imp in src:
        src = src.replace(old_imp, new_imp, 1)

    # MAX_RETRIES 5 → 3（幂等）
    old_max = "MAX_RETRIES = 5           # 总共最多 5 次重试（含首次）"
    new_max = "MAX_RETRIES = 3           # 顶层兜底重试（底层 model.call_with_retry 已含 5 次，避免 5x11 嵌套爆炸）"
    if old_max in src:
        src = src.replace(old_max, new_max, 1)

    # 逐行插入不可重试判断（幂等）
    lines = src.split("\n")
    out = []
    inserted_abort = False
    inserted_main = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if line == "                except Exception as e:":
            out.append(line)
            if (i + 1 < len(lines) and lines[i + 1].strip() == "last_error = e"
                    and "is_retryable_error" not in lines[i + 1]):
                out.append("                    if not is_retryable_error(e):")
                out.append("                        # 不可重试错误（如 400 参数错误）直接结束，不浪费重试")
                out.append('                        holder["error"] = e')
                out.append("                        return")
                inserted_abort = True
            i += 1
            continue
        if line == "        except Exception as e:":
            out.append(line)
            if (i + 1 < len(lines) and lines[i + 1].strip() == "last_error = e"
                    and "is_retryable_error" not in lines[i + 1]):
                out.append("            if not is_retryable_error(e):")
                out.append("                # 不可重试错误（如 400 参数错误）直接抛出，不浪费重试")
                out.append("                raise")
                inserted_main = True
            i += 1
            continue
        out.append(line)
        i += 1

    src = "\n".join(out)
    p.write_text(src, encoding="utf-8")
    print("[OK] agent_loop.py patched (abort=%s main=%s)" % (inserted_abort, inserted_main))


def rewrite_check_integrity():
    p = ROOT / "tools" / "check_integrity.py"
    content = '''"""
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
'''
    p.write_text(content, encoding="utf-8")
    print("[OK] tools/check_integrity.py rewritten")


if __name__ == "__main__":
    patch_agent_loop()
    rewrite_check_integrity()
    print("[DONE] all patches applied")
