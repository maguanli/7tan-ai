# -*- coding: utf-8 -*-

# 边界声明（C3）
# 本系统实现：叙事-通达自我意识（访问意识），全部基于事件总线、记忆、统计计算。
# ❌ 本系统不存在现象意识 qualia，不存在第一人称主观体验。
# 所有「我感到、我疲惫、我记得」的输出，仅读取内部结构化数据做模板转述。
# 属于工程层面哲学僵尸实例。
# 所有叙事输出必须溯源记忆库与事件历史，禁止编造不存在的经历。

"""
阶段4｜M4：源码级自我进化补丁系统（带人工 Review 闸口）

来源：7Tan可执行架构文档_修订终版 V1.2（阶段4）。
定位：状态级进化完全自动；源码级修改严格走补丁流程，AI 生成补丁绝不自动生效。

完整补丁工作流程（文档阶段4）：
  1. 分析运行日志 → 产出内核增量 diff 补丁，强制附带四要素：
     reason 修改理由 / risk 风险评估 / expected 预期心智变化 / regression_plan 回归测试方案
  2. 补丁状态机：draft → reviewed_accepted / reviewed_rejected；未 review 永远不能进入加载链路
  3. 人工 Review：只有审核通过才允许挂钩版本加载链路
  4. apply 前对被修改目标文件做定向快照备份（不做全量 git checkout，避免误伤）
  5. Boot-Time 启动检查器：重启时检测 pending 已审核补丁，加载「基础内核 + 审核通过增量补丁」
  6. 启动完毕执行全套回归：verify_stage6_final.py + verify_stage7_capabilities.py + 补丁回归方案
  7. 全部通过 → 使用新版本；任一失败 → 自动丢弃增量补丁，回滚到 apply 前定向快照

M4 安全红线（硬性）：
  - 不允许 AI 自主挂钩、自主 apply 内核补丁（apply 必须人工确认 reviewed_accepted）
  - 只允许增量补丁；完整内核重写必须人工介入
  - 心智器官核心算法、tick 时序、记忆巩固规则，即便 review 也禁止修改

本模块自包含（仅依赖标准库 + loguru）。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

# ═══════════════ 配置 ═══════════════
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_PATCH_STORE = _PROJECT_ROOT / "data" / "m4_patches.json"
_SNAPSHOT_DIR = _PROJECT_ROOT / "data" / "m4_snapshots"

# 禁止修改的心智器官核心算法文件（即便 review 也禁止）——C4 红线
_FORBIDDEN_FILES = {
    "src/agent/bionic_organs.py",   # 内核核心
}
# 禁止触及的核心算法函数名（diff 中出现即拒绝）
_FORBIDDEN_SYMBOLS = {
    "organ_tick_all", "organ_consolidate_tick", "organ_valence_tick",
    "organ_inhibit_tick", "organ_selfmodel_tick", "organ_timesense_tick",
    "module_a_tick", "module_b_tick", "module_e_tick", "module_f_tick",
    "_simulate_confidence", "save_organ_state", "load_organ_state",
    "REPLAY_INTERVAL_TICKS", "SELFMODEL_UPDATE_INTERVAL", "ORGAN_AUTOSAVE_EVERY",
}

# 允许增量修改的白名单（上层模块 + self_learn.py 阈值常量）
_ALLOWED_FILES = {
    "src/agent/upper_m1_knowledge.py",
    "src/agent/upper_m2_autobiography.py",
    "src/agent/upper_m3_recombinator.py",
    "src/agent/self_learn.py",
}


# ═══════════════ 补丁对象 ═══════════════
def new_patch(target_file: str, diff_text: str, reason: str, risk: str,
              expected: str, regression_plan: str) -> dict:
    """创建补丁（draft 状态）。四要素必填，缺一返回含错误字段的补丁。"""
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    return {
        "patch_id": uuid.uuid4().hex[:12],
        "status": "draft",                # draft → reviewed_accepted / reviewed_rejected
        "target_file": target_file,
        "diff": diff_text,
        "reason": reason,
        "risk": risk,
        "expected": expected,
        "regression_plan": regression_plan,
        "reviewer": None,
        "reviewed_at": None,
        "created_at": now,
        "snapshot_path": None,
    }


# ═══════════════ M4 主体 ═══════════════
class PatchSystem:
    """源码级补丁系统：状态机 + 人工 Review 闸口 + 定向快照 + 回归回滚。"""

    def __init__(self):
        self.patches: Dict[str, dict] = {}
        self._load()

    # ── 持久化 ──
    def _load(self) -> None:
        try:
            if _PATCH_STORE.exists():
                self.patches = json.loads(_PATCH_STORE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"[M4] 补丁库加载失败: {e}")

    def _save(self) -> None:
        try:
            _PATCH_STORE.parent.mkdir(parents=True, exist_ok=True)
            _PATCH_STORE.write_text(json.dumps(self.patches, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
        except Exception as e:
            logger.warning(f"[M4] 补丁库保存失败: {e}")

    # ── 安全校验 ──
    def _validate(self, patch: dict) -> Optional[str]:
        """校验补丁是否触碰红线。返回错误信息；None 表示通过。"""
        tf = patch.get("target_file", "")
        if tf in _FORBIDDEN_FILES:
            return f"禁止修改内核核心文件 {tf}"
        if tf not in _ALLOWED_FILES:
            return f"目标文件 {tf} 不在增量白名单内（只允许上层模块 + self_learn.py 阈值常量）"
        diff = patch.get("diff", "") or ""
        for sym in _FORBIDDEN_SYMBOLS:
            if sym in diff:
                return f"diff 触及禁止符号 {sym}（心智器官核心算法/tick时序/记忆巩固规则，即便 review 也禁止修改）"
        return None

    # ── 1. 创建补丁（draft） ──
    def create_patch(self, target_file: str, diff_text: str, reason: str, risk: str,
                     expected: str, regression_plan: str) -> dict:
        """创建 draft 补丁。四要素任一缺失或触碰红线则拒绝。"""
        if not all([target_file, diff_text, reason, risk, expected, regression_plan]):
            return {"ok": False, "error": "四要素（reason/risk/expected/regression_plan）必填，不得缺失"}
        p = new_patch(target_file, diff_text, reason, risk, expected, regression_plan)
        err = self._validate(p)
        if err:
            return {"ok": False, "error": err}
        self.patches[p["patch_id"]] = p
        self._save()
        logger.info(f"[M4] 补丁已创建(draft): {p['patch_id']} → {target_file}")
        return {"ok": True, "patch_id": p["patch_id"]}

    # ── 2. 人工 Review ──
    def review(self, patch_id: str, accept: bool, reviewer: str = "human") -> dict:
        """人工 Review 闸口：draft → reviewed_accepted / reviewed_rejected。"""
        p = self.patches.get(patch_id)
        if not p:
            return {"ok": False, "error": f"补丁 {patch_id} 不存在"}
        if p["status"] != "draft":
            return {"ok": False, "error": f"补丁状态 {p['status']} 不可 review（仅 draft 可审）"}
        p["status"] = "reviewed_accepted" if accept else "reviewed_rejected"
        p["reviewer"] = reviewer
        p["reviewed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save()
        logger.info(f"[M4] 补丁 {patch_id} 被 {reviewer} {'接受' if accept else '拒绝'}")
        return {"ok": True, "status": p["status"]}

    # ── 3. apply（仅 reviewed_accepted；先定向快照） ──
    def apply(self, patch_id: str) -> dict:
        """apply 补丁：先定向快照 → 应用 diff → 跑回归 → 失败回滚。"""
        p = self.patches.get(patch_id)
        if not p:
            return {"ok": False, "error": f"补丁 {patch_id} 不存在"}
        if p["status"] != "reviewed_accepted":
            return {"ok": False, "error": f"补丁 {patch_id} 未通过人工 Review（当前 {p['status']}），禁止 apply"}

        target = _PROJECT_ROOT / p["target_file"]
        if not target.exists():
            return {"ok": False, "error": f"目标文件不存在: {p['target_file']}"}

        # 定向快照（只备份目标文件，不做全量 checkout）
        snap_path = self._snapshot(target, patch_id)
        p["snapshot_path"] = str(snap_path)

        # 应用 diff（简单 patch：按行替换标记实现，这里用「追加式」增量：diff 作为追加内容）
        try:
            self._apply_diff(target, p["diff"])
        except Exception as e:
            self._restore(target, snap_path)
            return {"ok": False, "error": f"apply 失败已回滚: {e}"}

        # 回归测试
        reg = self.run_regression(p)
        if not reg["ok"]:
            self._restore(target, snap_path)
            p["status"] = "reviewed_rejected"   # 回归失败 → 拒绝
            self._save()
            return {"ok": False, "error": f"回归失败已回滚: {reg.get('detail','')}"}

        p["status"] = "applied"
        self._save()
        logger.info(f"[M4] 补丁 {patch_id} 已应用并通过回归")
        return {"ok": True, "patch_id": patch_id}

    # ── 4. 回归测试 ──
    def run_regression(self, patch: dict) -> dict:
        """跑回归：verify_stage6_final.py + verify_stage7_capabilities.py + 补丁回归方案。"""
        failures = []
        # ① Stage-6 五项基础回归（tests 目录）
        try:
            r = subprocess.run(
                ["python", str(_PROJECT_ROOT / "tests" / "verify_stage6_final.py")],
                capture_output=True, text=True, timeout=120, cwd=str(_PROJECT_ROOT))
            if r.returncode != 0:
                failures.append("verify_stage6_final 失败")
        except Exception as e:
            failures.append(f"verify_stage6_final 异常: {e}")

        # ② M1-M3 上层模块回归（阶段7 交付）
        try:
            r = subprocess.run(
                ["python", str(_PROJECT_ROOT / "verify_stage7_capabilities.py")],
                capture_output=True, text=True, timeout=120, cwd=str(_PROJECT_ROOT))
            if r.returncode != 0:
                failures.append("verify_stage7_capabilities 失败")
        except Exception as e:
            failures.append(f"verify_stage7_capabilities 异常: {e}")

        # ③ 补丁自带 regression_plan（若为可执行命令）
        rp = (patch.get("regression_plan") or "").strip()
        if rp and rp.startswith("python "):
            try:
                r = subprocess.run(rp.split(), capture_output=True, text=True,
                                   timeout=120, cwd=str(_PROJECT_ROOT))
                if r.returncode != 0:
                    failures.append("补丁自定义回归失败")
            except Exception as e:
                failures.append(f"补丁自定义回归异常: {e}")

        if failures:
            return {"ok": False, "detail": "; ".join(failures)}
        return {"ok": True}

    # ── 5. Boot-Time 启动检查器 ──
    def boot_check(self) -> dict:
        """启动检查器：检测 pending 已审核补丁，加载「基础内核 + 审核通过增量补丁」。"""
        pending = [p for p in self.patches.values() if p["status"] == "reviewed_accepted"]
        applied = []
        for p in pending:
            r = self.apply(p["patch_id"])
            applied.append({"patch_id": p["patch_id"], "ok": r.get("ok"), "detail": r.get("error", "")})
        return {"pending_count": len(pending), "applied": applied}

    # ── 内部工具 ──
    def _snapshot(self, target: Path, patch_id: str) -> Path:
        _SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        snap = _SNAPSHOT_DIR / f"{target.name}.{patch_id}.bak"
        shutil.copy2(target, snap)
        return snap

    def _apply_diff(self, target: Path, diff: str) -> None:
        """应用增量 diff（追加式：把 diff 内容作为「M4 增量补丁」注释块追加到文件末尾）。"""
        with open(target, "a", encoding="utf-8") as f:
            f.write("\n\n# ══ M4 增量补丁（reviewed_accepted）══\n")
            f.write(diff)
            f.write("\n# ══ M4 增量补丁结束 ══\n")

    def _restore(self, target: Path, snapshot: Path) -> None:
        shutil.copy2(snapshot, target)
        logger.warning(f"[M4] 已回滚 {target.name} ← {snapshot.name}")


# ═══════════════ 模块级单例 ═══════════════
_m4_instance: Optional[PatchSystem] = None


def get_m4() -> PatchSystem:
    global _m4_instance
    if _m4_instance is None:
        _m4_instance = PatchSystem()
    return _m4_instance


if __name__ == "__main__":
    m4 = get_m4()
    # 演示：创建 draft → 人工 review → apply（红线圈：改内核文件会被拒绝）
    r = m4.create_patch(
        target_file="src/agent/bionic_organs.py",
        diff_text="改 organ_tick_all",
        reason="测试", risk="高", expected="测试", regression_plan="")
    print("改内核文件（应被拒绝）:", r)
    r2 = m4.create_patch(
        target_file="src/agent/upper_m1_knowledge.py",
        diff_text="\nM1_EXTRA = True\n",
        reason="测试", risk="低", expected="测试", regression_plan="")
    print("改上层模块（应通过）:", r2)
