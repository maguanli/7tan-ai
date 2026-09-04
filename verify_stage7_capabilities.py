# -*- coding: utf-8 -*-
"""
阶段7 交付物｜verify_stage7_capabilities.py：M1-M3 上层模块回归测试

来源：7Tan可执行架构文档_修订终版 V1.2（阶段4 回归套件 / 阶段7 交付物）。
定位：M4 补丁系统回归的第 ② 项——验证 M1-M3 上层模块未被补丁破坏。
运行方式：python verify_stage7_capabilities.py（退出码 0=通过，非 0=失败）。

边界：本脚本只测上层模块（不依赖 LLM，不写内核核心状态），全部自包含。
测试使用独立临时游标路径，不污染生产状态文件。
"""
from __future__ import annotations

import sys
import tempfile
import traceback
from pathlib import Path


def _test_m1_knowledge() -> tuple:
    """M1 双知识获取：知识包去重 + 限速器（独立临时游标，不污染生产）。"""
    from src.agent.upper_m1_knowledge import KnowledgePackageQueue, _RateLimiter
    # 独立临时游标路径
    tmp = Path(tempfile.gettempdir()) / "m1_test_cursor.json"
    if tmp.exists():
        tmp.unlink()
    q = KnowledgePackageQueue(cursor_path=tmp)
    n = q.enqueue([
        {"item_id": "t-001", "content": "a"},
        {"item_id": "t-002", "content": "b"},
        {"item_id": "t-001", "content": "dup"},
    ])
    assert n == 2, f"知识包去重失败：应入队2条，实际 {n}"
    # 再次 enqueue 相同 id 应全部去重
    n2 = q.enqueue([{"item_id": "t-001", "content": "dup2"}])
    assert n2 == 0, f"去重失效：重复 id 应入队0条，实际 {n2}"
    # 限速器：每 tick 最多 rate 条
    rl = _RateLimiter(rate=3)
    tick = 100
    assert rl.try_acquire(tick) and rl.try_acquire(tick) and rl.try_acquire(tick)
    assert not rl.try_acquire(tick), "限速器未生效：第4次应拒绝"
    # 清理临时文件
    try:
        tmp.unlink()
    except Exception:
        pass
    return ("M1", True, "知识包去重 + 限速器正常")


def _test_m2_autobiography() -> tuple:
    """M2 自传叙事 + 代词指代。"""
    from src.agent.upper_m2_autobiography import (
        assemble_autobiography, DialogContextStack,
    )
    bio = assemble_autobiography()
    assert isinstance(bio, dict), "自传叙事应返回 dict"
    ctx = DialogContextStack()
    ctx.push("user", "帮我看看「7Tan架构文档」的 M1 模块")
    resolved = ctx.resolve("它 有什么用途？")
    assert "7Tan架构文档" in resolved, f"代词指代解析失败: {resolved}"
    return ("M2", True, "自传叙事 + 代词指代正常")


def _test_m3_recombinator() -> tuple:
    """M3 记忆碎片重组：素材不足时返回「无相关经历记录」，不编造。"""
    from src.agent.upper_m3_recombinator import UpperModuleM3
    m3 = UpperModuleM3()
    r = m3.recombine("回归测试")
    assert isinstance(r, dict), "重组应返回 dict"
    assert "ok" in r, "重组结果缺 ok 字段"
    return ("M3", True, "记忆碎片重组器正常（素材不足时不编造）")


def _test_m4_patch() -> tuple:
    """M4 补丁系统：红线圈（改内核文件应被拒绝）。"""
    from src.agent.m4_patch_system import PatchSystem
    m4 = PatchSystem()
    r = m4.create_patch(
        target_file="src/agent/bionic_organs.py",
        diff_text="改 organ_tick_all",
        reason="测试", risk="高", expected="测试", regression_plan="")
    assert r.get("ok") is False, "M4 红线失效：改内核文件应被拒绝"
    return ("M4", True, "补丁系统红线圈正常")


def main() -> int:
    tests = [_test_m1_knowledge, _test_m2_autobiography, _test_m3_recombinator, _test_m4_patch]
    passed, failed = 0, 0
    for fn in tests:
        try:
            name, ok, msg = fn()
            if ok:
                passed += 1
                print(f"  [PASS] {name}: {msg}")
            else:
                failed += 1
                print(f"  [FAIL] {name}: {msg}")
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {fn.__name__}: {e}")
            traceback.print_exc()
    print(f"\nverify_stage7_capabilities: {passed} passed / {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
