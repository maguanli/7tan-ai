# -*- coding: utf-8 -*-
"""
P0-3 重试统一修复：
1. model_manager._chat_with_retry 手写重试循环 → utils/retry.py @retry 装饰器
2. agent_loop 顶层重试 5 次 → 3 次（避免 5×11 嵌套爆炸），不可重试错误直接抛
3. tools/check_integrity.py 适配新版 IntegrityChecker 接口（manifest_path/mode）
"""
from pathlib import Path

ROOT = Path(r"D:\7tan\7tanAI")


def patch_model_manager():
    p = ROOT / "src" / "agent" / "model_manager.py"
    src = p.read_text(encoding="utf-8")

    # 1) import 行补充 RetryConfig + 新增模块级重试策略
    old_import = "from ..utils.retry import retry, is_retryable_error, classify_policy, RETRY_POLICIES"
    new_import = (
        "from ..utils.retry import retry, is_retryable_error, classify_policy, RETRY_POLICIES, RetryConfig\n"
        "\n"
        "\n"
        "# LLM 调用重试策略（统一走 utils/retry.py，避免手写重试循环）\n"
        "_LLM_RETRY_CFG = RetryConfig(\n"
        "    max_retries=5,\n"
        "    base_delay=2.0,\n"
        "    max_delay=120.0,\n"
        "    backoff=2.0,\n"
        "    jitter=True,\n"
        "    name=\"LLM调用\",\n"
        ")"
    )
    assert old_import in src, "model_manager: import 行未找到"
    src = src.replace(old_import, new_import, 1)

    # 2) 替换 _chat_with_retry 方法体（从 def 到下一个 def _get_client 之前）
    start_marker = "    def _chat_with_retry(self, client, **kwargs):"
    end_marker = "    def _get_client(self):"
    i = src.find(start_marker)
    j = src.find(end_marker)
    assert i != -1 and j != -1 and i < j, "model_manager: 方法边界未找到"
    new_method = (
        "    def _chat_with_retry(self, client, **kwargs):\n"
        "        \"\"\"带智能重试的 chat 调用（重试统一走 utils/retry.py 装饰器）\"\"\"\n"
        "        # Clean surrogate chars before API call\n"
        "        kwargs = self._sanitize_surrogates(kwargs)\n"
        "        return self._chat_once(client, **kwargs)\n"
        "\n"
        "    @retry(policy=_LLM_RETRY_CFG, auto_classify=False)\n"
        "    def _chat_once(self, client, **kwargs):\n"
        "        \"\"\"单次 chat.completions.create 调用。\n"
        "        由 @retry 统一处理：指数退避 + 抖动 + 错误分类（400 等不可重试错误直接抛出）。\n"
        "        \"\"\"\n"
        "        return client.chat.completions.create(**kwargs)\n"
        "\n"
    )
    src = src[:i] + new_method + src[j:]
    p.write_text(src, encoding="utf-8")
    print("✅ model_manager.py 修复完成")


def patch_agent_loop():
    p = ROOT / "src" / "agent" / "agent_loop.py"
    lines = p.read_text(encoding="utf-8").split("\n")

    out = []
    inserted_abort = False
    inserted_main = False
    i = 0
    while i < len(lines):
        line = lines[i]
        # 可中止分支（16 空格缩进）
        if line == "                except Exception as e:":
            out.append(line)
            if i + 1 < len(lines) and lines[i + 1].strip() == "last_error = e":
                out.append("                    if not is_retryable_error(e):")
                out.append("                        # 不可重试错误（如 400 参数错误）直接结束，不浪费重试")
                out.append('                        holder["error"] = e')
                out.append("                        return")
                inserted_abort = True
            i += 1
            continue
        # 主循环分支（8 空格缩进）
        if line == "        except Exception as e:":
            out.append(line)
            if i + 1 < len(lines) and lines[i + 1].strip() == "last_error = e":
                out.append("            if not is_retryable_error(e):")
                out.append("                # 不可重试错误（如 400 参数错误）直接抛出，不浪费重试")
                out.append("                raise")
                inserted_main = True
            i += 1
            continue
        out.append(line)
        i += 1

    assert inserted_abort and inserted_main, \
        f"agent_loop: 分支未全部命中 abort={inserted_abort} main={inserted_main}"
    src = "\n".join(out)

    # import is_retryable_error
    old_imp = "from .model_manager import track_cost_internal, _fix_surrogates"
    new_imp = ("from ..utils.retry import is_retryable_error\n"
               "from .model_manager import track_cost_internal, _fix_surrogates")
    assert old_imp in src, "agent_loop: import 行未找到"
    src = src.replace(old_imp, new_imp, 1)

    # MAX_RETRIES 5 → 3（顶层兜底，底层已含 5 次重试）
    old_max = "MAX_RETRIES = 5           # 总共最多 5 次重试（含首次）"
    new_max = "MAX_RETRIES = 3           # 顶层兜底重试（底层 model.call_with_retry 已含 5 次，避免 5×11 嵌套爆炸）"
    assert old_max in src, "agent_loop: MAX_RETRIES 未找到"
    src = src.replace(old_max, new_max, 1)

    p.write_text(src, encoding="utf-8")
    print("✅ agent_loop.py 修复完成")


def rewrite_check_integrity():
    p = ROOT / "tools" / "check_integrity.py"
    content = '''"""
完整性检查工具 — 命令行入口
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
    parser = argparse.ArgumentParser(description="7坛AI小编 完整性检查")
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
        print(f"✅ 已生成完整性清单: {args.manifest}")
    elif args.action == "check":
        report = checker.check_all()
        print(f"健康: {report.healthy} | 篡改文件: {report.tampered_count}")
        for f in getattr(report, "missing", []) or []:
            print(f"  ❌ 缺失: {f}")
        for f, exp, act in getattr(report, "modified", []) or []:
            print(f"  ❌ 修改: {f} (期望 {exp[:12]}... 实际 {act[:12]}...)")
        if report.healthy:
            print("✅ 完整性校验通过")
        sys.exit(0 if report.healthy else 1)
    elif args.action == "update":
        if not args.file:
            print("❌ update 需要 --file 参数")
            sys.exit(1)
        checker.update_file_hash(args.file)
        print(f"✅ 已更新 {args.file} 的哈希值")


if __name__ == "__main__":
    main()
'''
    p.write_text(content, encoding="utf-8")
    print("✅ tools/check_integrity.py 重写完成")


if __name__ == "__main__":
    patch_model_manager()
    patch_agent_loop()
    rewrite_check_integrity()
    print("🎉 全部补丁完成")
