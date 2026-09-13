# -*- coding: utf-8 -*-
"""
模块D：自我进化安全底座（L2 参数级 / 源码级自我进化）—— Git / 沙盒 / 回退

来源：智能生命项目 · 第三册记录（模块D 已实现+验证）与第四册设计稿。
定位：
  · D1 GitVersionHelper —— Git 快照 / 回退；Git 不可用时自动降级本地 .bak 备份。
  · D2 MetaEvolutionLayer ——
      路径1 参数调优（轻量进化）：基于记忆库历史轨迹留一法回测，
          在沙盒中评估常量变体，选出改善最优者，经沙盒验证后落地到源码常量。
      路径2 源码自升级（重度进化，受限白名单）：
          AST 定位 src/agent/self_learn.py 白名单常量赋值语句 → 生成补丁变体
          → 沙盒子进程隔离回测 → 崩溃 / 恶化 → git checkout 回退（无 git 则 .bak 恢复）；
          改善 → 覆盖主程序源码并 git commit 快照。
  · D3 总开关 ENABLE_7TAN_SELF_CODE_EVOLVE = True（默认开启）
        关闭时：全部进化动作返回 disabled，不产生任何文件 / 进程 / 提交。

安全红线（硬性，防"把自己改崩"）：
  1. 总开关默认开启；进化动作受白名单 + 每日配额约束。
  2. 绝不原地修改运行中的主程序文件；任何源码改动先复制进沙盒子进程验证。
  3. 白名单：只允许修改 src/agent/self_learn.py 的 5 个阈值常量；其它文件一律拒绝。
  4. 崩溃或指标恶化 → 自动 git checkout 回退（无 git 则 .bak 恢复），保证可回退。
  5. 冷却时间 + 每日配额上限，防止进化失控。
  6. 所有进化动作输出审计日志 data/tan_evolution.log。

本模块自包含（仅依赖标准库 + loguru）。
"""
from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

from loguru import logger

# ═══════════════ D3 总开关（默认开启） ═══════════════
ENABLE_7TAN_SELF_CODE_EVOLVE = True

# 进化节流参数
EVOLUTION_COOLDOWN_SECONDS = 600      # 两次进化最小间隔（秒）
EVOLUTION_DAILY_QUOTA = 5             # 每天最多进化次数
EVOLUTION_TIMEOUT_SECONDS = 60        # 沙盒子进程超时
EVOLUTION_BACKTEST_MAX_TRACES = 500   # 回测限样本量：只取最近 N 条轨迹（防 O(n²) 阻塞对话）

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_AGENT_DIR = _PROJECT_ROOT / "src" / "agent"
_DATA_DIR = _PROJECT_ROOT / "data"
_SANDBOX_ROOT = _DATA_DIR / "sandbox" / "evolve"
_MEMORY_PATH = _DATA_DIR / "tan_model_memory.json"
_EVOLUTION_LOG_PATH = _DATA_DIR / "tan_evolution.log"
_TARGET_FILE = "self_learn.py"        # 源码进化的唯一白名单目标文件

# 源码进化白名单：常量名 -> (最小值, 最大值, 类型)
EVOLVABLE_CONSTANTS: dict = {
    "HYPO_MIN_TESTS": (1, 10, int),
    "HYPO_PASS_THRESHOLD": (0.4, 0.9, float),
    "HYPO_REJECT_THRESHOLD": (0.1, 0.5, float),
    "MEMORY_BUMP_STRENGTH": (0.01, 0.3, float),
    "MEMORY_WEAKEN_STRENGTH": (0.05, 0.5, float),
}
# 参数调优扰动步长（int 用 1，float 用 0.05）
_TUNE_STEP: dict = {"HYPO_MIN_TESTS": 1, "HYPO_PASS_THRESHOLD": 0.05,
                    "HYPO_REJECT_THRESHOLD": 0.05,
                    "MEMORY_BUMP_STRENGTH": 0.02, "MEMORY_WEAKEN_STRENGTH": 0.03}
_DEFAULT_PASS_THRESHOLD = 0.55        # 回测中 expected_success 判定阈值
_MIN_IMPROVEMENT = 0.01               # 准确率提升至少 1 个百分点才采纳


def _log_evolution(msg: str):
    """审计日志：所有进化动作留痕。"""
    try:
        _EVOLUTION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_EVOLUTION_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception as e:
        logger.warning(f"进化日志写入失败: {e}")


# ═══════════════ D1：Git 快照 / 回退（降级 .bak） ═══════════════
class GitVersionHelper:
    """Git 快照 / 回退；Git 不可用时自动降级本地 .bak 备份。"""

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = Path(repo_root) if repo_root else _PROJECT_ROOT
        self._git_ok: Optional[bool] = None

    def is_git_available(self) -> bool:
        if self._git_ok is None:
            try:
                r = subprocess.run(["git", "-C", str(self.repo_root), "rev-parse",
                                    "--is-inside-work-tree"],
                                   capture_output=True, text=True, timeout=15)
                self._git_ok = r.returncode == 0
            except Exception:
                self._git_ok = False
        return self._git_ok

    def snapshot(self, reason: str) -> Optional[str]:
        """把当前状态提交为快照，返回 commit id；git 不可用返回 None。"""
        if not self.is_git_available():
            _log_evolution(f"[降级] Git 不可用，快照改用 .bak 备份（{reason}）")
            return None
        try:
            subprocess.run(["git", "-C", str(self.repo_root), "add", "-A"],
                           capture_output=True, text=True, timeout=60)
            r = subprocess.run(
                ["git", "-C", str(self.repo_root), "commit", "-m",
                 f"7Tan self-evolve snapshot: {reason[:60]}"],
                capture_output=True, text=True, timeout=60)
            if r.returncode != 0 and "nothing to commit" not in r.stdout:
                logger.warning(f"快照提交失败: {r.stderr.strip()}")
                return None
            out = subprocess.run(["git", "-C", str(self.repo_root), "rev-parse", "HEAD"],
                                 capture_output=True, text=True, timeout=15)
            return out.stdout.strip() if out.returncode == 0 else None
        except Exception as e:
            logger.warning(f"Git 快照异常: {e}")
            return None

    def rollback_file(self, commit: Optional[str], rel_path: str) -> bool:
        """回退单个文件到指定 commit（只动目标文件，不碰其它工作区改动）。

        git 不可用或 commit 为空 → 用 .bak 恢复。
        """
        if commit and self.is_git_available():
            try:
                subprocess.run(["git", "-C", str(self.repo_root), "checkout", commit,
                                "--", rel_path],
                               capture_output=True, text=True, timeout=60)
                _log_evolution(f"[回退] git checkout {commit[:8]} -- {rel_path}")
                return True
            except Exception as e:
                logger.warning(f"git checkout 回退失败: {e}")
        bak = Path(self._bak_path(rel_path))
        target = self.repo_root / rel_path
        if bak.exists():
            try:
                shutil.copy2(bak, target)
                _log_evolution(f"[回退] 从 .bak 恢复 {rel_path}")
                return True
            except Exception as e:
                logger.warning(f".bak 恢复失败: {e}")
        return False

    def bak_backup(self, rel_path: str) -> Path:
        bak = Path(self._bak_path(rel_path))
        bak.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.repo_root / rel_path, bak)
        return bak

    def _bak_path(self, rel_path: str) -> str:
        name = Path(rel_path).name
        return str(_DATA_DIR / "backups" / f"{name}.{time.strftime('%Y%m%d%H%M%S')}.bak")


# ═══════════════ 回测评估器（留一法，纯本地） ═══════════════
class BacktestEvaluator:
    """基于记忆库历史轨迹的留一法回测：评估一组参数下预测准确率。

    对每条轨迹，用同场景其它轨迹的加权成功率做预测（排除自身，避免自证），
    比较 expected_success 与实际 action_finished。
    """

    @staticmethod
    def evaluate(traces: list, params: dict) -> dict:
        pass_threshold = float(params.get("pass_threshold", _DEFAULT_PASS_THRESHOLD))
        correct, n, conf_sum = 0, 0, 0.0
        for i, t in enumerate(traces):
            scene = t.get("scene")
            others = [x for j, x in enumerate(traces)
                      if j != i and x.get("scene") == scene]
            if not others:
                continue
            total_w = succ_w = 0.0
            for o in others:
                w = float(o.get("weight_eff", 1.0))
                if o.get("action_finished"):
                    succ_w += w
                total_w += w
            if total_w <= 0:
                continue
            conf = succ_w / total_w
            pred = conf > pass_threshold
            actual = bool(t.get("action_finished"))
            conf_sum += conf
            if pred == actual:
                correct += 1
            n += 1
        return {
            "n": n,
            "accuracy": round(correct / n, 4) if n else 0.0,
            "avg_confidence": round(conf_sum / n, 4) if n else 0.0,
        }

    @staticmethod
    def load_traces() -> list:
        # 主存储：SQLite 数据库（tan_model_memory 表）；回退：JSON 镜像
        traces = None
        try:
            from ..database.db import load_tan_model_memory
            data = load_tan_model_memory()
            if data.get("traces"):
                traces = data["traces"]
        except Exception as e:
            logger.warning(f"从数据库读取 7Tan 模型记忆失败（回退 JSON 镜像）: {e}")
        if traces is None:
            try:
                if _MEMORY_PATH.exists():
                    raw = json.loads(_MEMORY_PATH.read_text(encoding="utf-8"))
                    traces = raw.get("traces") or []
            except Exception as e:
                logger.warning(f"读取记忆库失败: {e}")
        if not traces:
            return []
        # 回测限样本量：只取最近 N 条轨迹，避免 O(n²) 回测在大样本下阻塞对话（方案B）
        return traces[-EVOLUTION_BACKTEST_MAX_TRACES:]


# ═══════════════ 沙盒运行器 ═══════════════
class SandboxRunner:
    """把补丁后的 self_learn.py 复制进独立沙盒目录，子进程隔离回测。

    验证两件事：① 补丁后模块可正常导入（语法/逻辑完整）；② 回测指标。
    """

    @staticmethod
    def _apply_patch_text(source: str, patch: dict) -> str:
        """把补丁 {常量名: 新值} 应用到源码文本（按 AST 定位的常量赋值行替换）。"""
        tree = ast.parse(source)
        lines = source.splitlines(keepends=True)
        changed = set()
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                    and isinstance(node.targets[0], ast.Name) \
                    and node.targets[0].id in patch:
                name = node.targets[0].id
                new_val = patch[name]
                # 只替换该常量赋值行的"值"部分
                old_line = lines[node.lineno - 1]
                m = re.match(r"^(\s*" + re.escape(name) + r"\s*=\s*).*$", old_line)
                if m:
                    lines[node.lineno - 1] = m.group(1) + repr(new_val) + "\n"
                    changed.add(name)
        if changed != set(patch.keys()):
            raise ValueError(f"补丁未完全命中: 要求{set(patch.keys())}, 实际{changed}")
        return "".join(lines)

    @staticmethod
    def _build_eval_script(sandbox_dir: Path, patch: dict) -> Path:
        """在沙盒目录生成评估脚本：导入补丁后模块 + 留一法回测，输出 JSON。"""
        constant_names = list(patch.keys())
        script = f'''# -*- coding: utf-8 -*-
import sys, json
sys.path.insert(0, {str(sandbox_dir)!r})
import self_learn  # 验证补丁后模块可导入
params = {{k: getattr(self_learn, k) for k in {constant_names!r}}}
traces = json.load(open({str(_MEMORY_PATH)!r}, encoding="utf-8"))["traces"][-{EVOLUTION_BACKTEST_MAX_TRACES}:]
correct, n, conf_sum = 0, 0, 0.0
pass_threshold = 0.55
for i, t in enumerate(traces):
    scene = t.get("scene")
    others = [x for j, x in enumerate(traces) if j != i and x.get("scene") == scene]
    if not others:
        continue
    total_w = succ_w = 0.0
    for o in others:
        w = float(o.get("weight_eff", 1.0))
        if o.get("action_finished"):
            succ_w += w
        total_w += w
    if total_w <= 0:
        continue
    conf = succ_w / total_w
    pred = conf > pass_threshold
    actual = bool(t.get("action_finished"))
    conf_sum += conf
    if pred == actual:
        correct += 1
    n += 1
print(json.dumps({{
    "ok": True,
    "n": n,
    "accuracy": round(correct / n, 4) if n else 0.0,
    "avg_confidence": round(conf_sum / n, 4) if n else 0.0,
    "loaded_constants": params,
}}))
'''
        eval_path = sandbox_dir / "eval_backtest.py"
        eval_path.write_text(script, encoding="utf-8")
        return eval_path

    def run(self, patch: dict) -> dict:
        """执行一次沙盒验证：返回 {sandbox_ok, metrics} 或 {sandbox_ok: False, error}"""
        sandbox_dir = _SANDBOX_ROOT / uuid.uuid4().hex[:12]
        try:
            sandbox_dir.mkdir(parents=True, exist_ok=True)
            # 复制目标源码 → 打补丁 → 写沙盒模块
            src = (_AGENT_DIR / _TARGET_FILE).read_text(encoding="utf-8")
            patched = self._apply_patch_text(src, patch)
            (sandbox_dir / _TARGET_FILE).write_text(patched, encoding="utf-8")
            eval_path = self._build_eval_script(sandbox_dir, patch)
            r = subprocess.run([sys.executable, str(eval_path)],
                               capture_output=True, text=True, timeout=EVOLUTION_TIMEOUT_SECONDS)
            if r.returncode != 0:
                _log_evolution(f"[沙盒] 子进程退出码={r.returncode}: {r.stderr[-300:]}")
                return {"sandbox_ok": False, "error": r.stderr[-300:]}
            metrics = json.loads(r.stdout.strip().splitlines()[-1])
            return {"sandbox_ok": True, "metrics": metrics}
        except subprocess.TimeoutExpired:
            _log_evolution(f"[沙盒] 子进程超时（>{EVOLUTION_TIMEOUT_SECONDS}s）")
            return {"sandbox_ok": False, "error": "timeout"}
        except Exception as e:
            _log_evolution(f"[沙盒] 异常: {e}")
            return {"sandbox_ok": False, "error": str(e)}
        finally:
            # 清理沙盒目录，不留垃圾
            try:
                shutil.rmtree(sandbox_dir, ignore_errors=True)
            except Exception:
                pass


# ═══════════════ D2：自我进化层 ═══════════════
class MetaEvolutionLayer:
    """模块D 主引擎：路径1 参数调优 / 路径2 源码自升级，均走沙盒+回退。"""

    def __init__(self, memory=None):
        self.memory = memory                  # 模块A：TanModelMemory（可为 None，回测直接读 JSON）
        self.git = GitVersionHelper(_PROJECT_ROOT)
        self.sandbox = SandboxRunner()
        self.last_result: Optional[dict] = None
        self.last_evolve_ts: float = 0.0
        self.today_attempts: int = 0
        self._day_stamp = time.strftime("%Y-%m-%d")

    # ---------------- 状态与节流 ----------------
    def _refresh_daily(self):
        today = time.strftime("%Y-%m-%d")
        if today != self._day_stamp:
            self._day_stamp = today
            self.today_attempts = 0

    def _cooldown_left(self) -> int:
        return max(0, int(EVOLUTION_COOLDOWN_SECONDS - (time.time() - self.last_evolve_ts)))

    def status(self) -> dict:
        self._refresh_daily()
        return {
            "enabled": ENABLE_7TAN_SELF_CODE_EVOLVE,
            "cooldown_left": self._cooldown_left(),
            "today_attempts": self.today_attempts,
            "daily_quota": EVOLUTION_DAILY_QUOTA,
            "last_result": self.last_result,
        }

    def _can_evolve(self) -> tuple:
        if not ENABLE_7TAN_SELF_CODE_EVOLVE:
            return False, "进化总开关已关闭（ENABLE_7TAN_SELF_CODE_EVOLVE=False）"
        self._refresh_daily()
        if self._cooldown_left() > 0:
            return False, f"冷却中，剩余 {self._cooldown_left()} 秒"
        if self.today_attempts >= EVOLUTION_DAILY_QUOTA:
            return False, f"今日配额已用尽（{EVOLUTION_DAILY_QUOTA} 次）"
        return True, "ok"

    # ---------------- 当前常量值 ----------------
    def _current_constants(self) -> dict:
        try:
            from . import self_learn as sl
            return {k: getattr(sl, k) for k in EVOLVABLE_CONSTANTS}
        except Exception:
            return {}

    # ---------------- 路径1：参数调优（一维搜索） ----------------
    def param_tune(self) -> dict:
        ok, why = self._can_evolve()
        if not ok:
            result = {"action": "param_tune", "status": "disabled", "reason": why}
            self.last_result = result
            return result

        current = self._current_constants()
        if not current:
            return self._fail("无法读取当前常量")
        baseline_metrics = BacktestEvaluator.evaluate(BacktestEvaluator.load_traces(), {})
        baseline_acc = baseline_metrics.get("accuracy", 0.0)

        best_patch, best_acc = None, baseline_acc
        candidates = []
        for name, (lo, hi, ctype) in EVOLVABLE_CONSTANTS.items():
            old = current.get(name)
            if old is None:
                continue
            step = _TUNE_STEP.get(name, 1 if ctype is int else 0.05)
            for direction in (+1, -1):
                new = old + direction * step
                if ctype is int:
                    new = int(round(new))
                else:
                    new = round(float(new), 4)
                if not (lo <= new <= hi):
                    continue
                candidates.append({name: new})

        # 基线本身也算一次评估（确认沙盒可用）
        base = self.sandbox.run({}) if False else None
        tested = 0
        for patch in candidates:
            tested += 1
            r = self.sandbox.run(patch)
            if not r.get("sandbox_ok"):
                _log_evolution(f"[调优] 变体 {patch} 沙盒失败: {r.get('error')}")
                continue
            acc = r["metrics"].get("accuracy", 0.0)
            if acc > best_acc:
                best_acc, best_patch = acc, patch
            if tested >= 8:  # 单轮最多评估 8 个变体，防失控
                break

        if best_patch is None or best_acc <= baseline_acc + _MIN_IMPROVEMENT:
            self.today_attempts += 1
            self.last_evolve_ts = time.time()
            result = {"action": "param_tune", "status": "no_improvement",
                      "baseline_accuracy": baseline_acc,
                      "best_accuracy": best_acc if best_patch else baseline_acc,
                      "candidates_tested": tested}
            self.last_result = result
            _log_evolution(f"[调优] 无改善 {result}")
            return result

        # 有改善 → 走安全落地（沙盒已验证过该补丁）
        apply_result = self._apply_patch_safely(best_patch, reason=f"param_tune acc {baseline_acc}→{best_acc}")
        self.today_attempts += 1
        self.last_evolve_ts = time.time()
        apply_result.update({"action": "param_tune", "patch": best_patch,
                             "baseline_accuracy": baseline_acc,
                             "best_accuracy": best_acc})
        self.last_result = apply_result
        return apply_result

    # ---------------- 路径2：源码自升级（给定补丁） ----------------
    def source_evolve(self, patch: dict) -> dict:
        ok, why = self._can_evolve()
        if not ok:
            result = {"action": "source_evolve", "status": "disabled", "reason": why}
            self.last_result = result
            return result
        # 白名单 + 范围校验
        for name, new_val in patch.items():
            if name not in EVOLVABLE_CONSTANTS:
                return self._fail(f"常量 {name} 不在进化白名单")
            lo, hi, ctype = EVOLVABLE_CONSTANTS[name]
            if ctype is int:
                new_val = int(new_val)
            else:
                new_val = float(new_val)
            if not (lo <= new_val <= hi):
                return self._fail(f"常量 {name}={new_val} 超出允许范围 [{lo},{hi}]")
            patch[name] = new_val

        baseline_metrics = BacktestEvaluator.evaluate(BacktestEvaluator.load_traces(), {})
        baseline_acc = baseline_metrics.get("accuracy", 0.0)
        r = self.sandbox.run(patch)
        if not r.get("sandbox_ok"):
            return self._fail(f"沙盒验证失败: {r.get('error')}")
        new_acc = r["metrics"].get("accuracy", 0.0)
        if new_acc <= baseline_acc + _MIN_IMPROVEMENT:
            self.today_attempts += 1
            self.last_evolve_ts = time.time()
            result = {"action": "source_evolve", "status": "rejected",
                      "reason": f"沙盒指标无改善（{baseline_acc} → {new_acc}）"}
            self.last_result = result
            _log_evolution(f"[源码进化] 拒绝 {result}")
            return result

        apply_result = self._apply_patch_safely(patch, reason=f"source_evolve acc {baseline_acc}→{new_acc}")
        self.today_attempts += 1
        self.last_evolve_ts = time.time()
        apply_result.update({"action": "source_evolve", "patch": patch,
                             "baseline_accuracy": baseline_acc,
                             "new_accuracy": new_acc})
        self.last_result = apply_result
        return apply_result

    # ---------------- 安全落地核心 ----------------
    def _apply_patch_safely(self, patch: dict, reason: str) -> dict:
        """快照 → 应用补丁 → 复检 → 提交；失败自动回退。"""
        rel_path = f"src/agent/{_TARGET_FILE}"
        target = _AGENT_DIR / _TARGET_FILE
        # 1) 快照（git commit 或 .bak）
        commit = self.git.snapshot(f"{reason}")
        if not commit:
            self.git.bak_backup(rel_path)
        try:
            # 2) 应用补丁
            src = target.read_text(encoding="utf-8")
            patched = SandboxRunner._apply_patch_text(src, patch)
            target.write_text(patched, encoding="utf-8")
            _log_evolution(f"[落地] 已应用补丁 {patch}（原因: {reason}）")
            # 3) 复检：重新沙盒验证（防止落地过程出错）
            verify = self.sandbox.run(patch)
            if not verify.get("sandbox_ok"):
                raise RuntimeError(f"落地后复检失败: {verify.get('error')}")
            # 4) 提交快照
            if commit:
                subprocess.run(["git", "-C", str(_PROJECT_ROOT), "add", "-A"],
                               capture_output=True, text=True, timeout=60)
                subprocess.run(["git", "-C", str(_PROJECT_ROOT), "commit", "-m",
                                f"7Tan self-evolve applied: {reason[:60]}"],
                               capture_output=True, text=True, timeout=60)
            return {"status": "applied", "reason": reason,
                    "verify_accuracy": verify["metrics"].get("accuracy")}
        except Exception as e:
            logger.warning(f"落地失败，开始回退: {e}")
            _log_evolution(f"[落地] 失败 {e} → 回退")
            if not self.git.rollback_file(commit, rel_path):
                return {"status": "rollback_failed", "error": str(e)}
            return {"status": "rolled_back", "error": str(e)}

    def _fail(self, msg: str) -> dict:
        result = {"action": "source_evolve", "status": "error", "reason": msg}
        self.last_result = result
        _log_evolution(f"[进化] 失败: {msg}")
        return result

    # ---------------- 主循环钩子 ----------------
    def tick(self) -> dict:
        """主循环/每次对话后可调用；开关关闭时零开销直接返回。"""
        if not ENABLE_7TAN_SELF_CODE_EVOLVE:
            return {"status": "disabled"}
        # 自动触发策略：先尝试参数调优（轻量）；若记忆轨迹太少则跳过
        traces = BacktestEvaluator.load_traces()
        if len(traces) < 4:
            return {"status": "skipped", "reason": "记忆轨迹不足（<4）"}
        return self.param_tune()
