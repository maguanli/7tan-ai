"""
安全模块 — 完整性校验引擎 + 安全检查
详见架构文档 §12 + §24

核心类:
- IntegrityChecker: 文件完整性校验引擎 (HMAC-SHA256)
- IntegrityReport: 校验报告数据类
- IntegrityError: 完整性异常
"""
import hashlib
import hmac
import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from loguru import logger

# 内置 HMAC 密钥（编译进 exe，不暴露在 json 中）
# ⚠️ 生产环境从环境变量或 exe 编译常量中读取
_SECRET = b"7tan_integrity_secret_v5"


# ============================================================
# 数据类
# ============================================================

@dataclass
class IntegrityReport:
    """完整性校验报告"""
    healthy: bool = True
    note: str = ""
    modified: list = field(default_factory=list)    # [(path, expected, actual), ...]
    missing: list = field(default_factory=list)      # [path, ...]
    extra: list = field(default_factory=list)        # 清单外的文件（可选）

    @property
    def is_clean(self) -> bool:
        return self.healthy and not self.modified and not self.missing

    @property
    def tampered_count(self) -> int:
        return len(self.modified) + len(self.missing)

    def __str__(self) -> str:
        if self.is_clean:
            return "✅ 完整性校验通过，所有核心文件未被篡改。"
        lines = [f"⚠️ 检测到 {self.tampered_count} 个文件异常！", ""]
        for path, expected, actual in self.modified:
            lines.append(f"  ❌ {path}")
            lines.append(f"     期望: {expected[:16]}...")
            lines.append(f"     实际: {actual[:16]}...")
        for path in self.missing:
            lines.append(f"  ❓ {path} — 文件丢失")
        return "\n".join(lines)


class IntegrityError(Exception):
    """完整性校验失败"""
    pass


# ============================================================
# IntegrityChecker (§24.4)
# ============================================================

class IntegrityChecker:
    """
    核心文件完整性校验引擎

    工作流:
    1. 加载 integrity.json → 验证 HMAC
    2. 逐一计算文件 SHA-256 → 比对期望值
    3. 输出 IntegrityReport
    """

    def __init__(
        self,
        manifest_path: str = "integrity.json",
        mode: Literal["core", "full"] = "core",
        secret: bytes = None,
    ):
        self.manifest_path = Path(manifest_path)
        self.mode = mode
        self.base_dir = Path(__file__).parent.parent.parent  # 项目根目录
        self._secret = secret or _SECRET

    # ----- 清单加载 -----

    def load_manifest(self) -> Optional[dict]:
        """加载完整性清单，验证 HMAC"""
        if not self.manifest_path.exists():
            return None

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        # 验证 manifest 自身未被篡改
        stored_hmac = manifest.pop("manifest_hmac", "")
        calculated_hmac = self._compute_manifest_hmac(manifest)

        if not hmac.compare_digest(calculated_hmac, stored_hmac):
            raise IntegrityError("❌ 完整性清单本身已被篡改！")

        # 恢复字段
        manifest["manifest_hmac"] = stored_hmac
        return manifest

    def _compute_manifest_hmac(self, manifest: dict) -> str:
        """计算 manifest 的 HMAC-SHA256"""
        # 排除 manifest_hmac 自身
        payload = {k: v for k, v in manifest.items() if k != "manifest_hmac"}
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hmac.new(self._secret, payload_bytes, hashlib.sha256).hexdigest()

    # ----- 文件哈希 -----

    def _hash_file(self, filepath: Path, algorithm: str = "sha256") -> str:
        """计算文件哈希（大文件分块读取，1MB 块，不爆内存）"""
        h = hashlib.new(algorithm)
        with open(filepath, "rb") as f:
            while chunk := f.read(1024 * 1024):  # 1MB 块
                h.update(chunk)
        return h.hexdigest()

    # ----- 校验 -----

    def check_all(self) -> "IntegrityReport":
        """校验所有清单文件"""
        manifest = self.load_manifest()
        if manifest is None:
            return IntegrityReport(healthy=True, note="首次运行，无完整性清单")

        report = IntegrityReport()
        expected_files = manifest.get("files", {})
        algorithm = manifest.get("algorithm", "sha256")

        for rel_path, expected_hash in expected_files.items():
            abs_path = self.base_dir / rel_path

            if not abs_path.exists():
                report.missing.append(rel_path)
                continue

            actual_hash = self._hash_file(abs_path, algorithm)

            if not hmac.compare_digest(actual_hash, expected_hash):
                report.modified.append((rel_path, expected_hash, actual_hash))

        report.healthy = report.tampered_count == 0
        return report

    def check_file(self, rel_path: str) -> tuple[bool, str]:
        """校验单个文件"""
        manifest = self.load_manifest()
        if manifest is None:
            return True, "无清单"

        expected_hash = manifest.get("files", {}).get(rel_path)
        if not expected_hash:
            return True, "不在清单中"

        abs_path = self.base_dir / rel_path
        if not abs_path.exists():
            return False, "文件丢失"

        actual = self._hash_file(abs_path)
        if hmac.compare_digest(actual, expected_hash):
            return True, "通过"
        return False, f"哈希不匹配: 期望 {expected_hash[:12]}... 实际 {actual[:12]}..."

    # ----- 清单生成 -----

    def generate_manifest(self) -> dict:
        """生成新的完整性清单（构建/发布时使用）"""
        from .manifest_template import get_files_by_level

        manifest = {
            "version": 1,
            "generated_at": datetime.now().isoformat(),
            "generated_by": "7tan-updater build v5.1.0",
            "algorithm": "sha256",
            "scope": self.mode,
            "files": {},
            "exclude_patterns": [
                "*.pyc", "__pycache__/**",
                "config.yaml", ".env",
                "data/**", "downloads/**",
                "logs/**", "backup/**",
                "*.log",
            ],
        }

        file_list = get_files_by_level(self.mode)

        for rel_path in file_list:
            abs_path = self.base_dir / rel_path
            if abs_path.exists():
                manifest["files"][rel_path] = self._hash_file(abs_path, "sha256")

        # 计算 HMAC
        manifest["manifest_hmac"] = self._compute_manifest_hmac(manifest.copy())
        return manifest

    def save_manifest(self, output_path: str = None):
        """生成并保存清单"""
        path = Path(output_path) if output_path else self.manifest_path
        manifest = self.generate_manifest()

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

        logger.info(f"🔒 完整性清单已保存: {path} ({len(manifest['files'])} 文件)")

    # ----- 自改进协调 (§24.5) -----

    def update_file_hash(self, rel_path: str):
        """
        AI 自改进修改文件后，更新 integrity.json 中的哈希
        详见 §24.5 自改进协调机制
        """
        manifest = self.load_manifest()
        if manifest is None:
            logger.warning("无清单，跳过哈希更新")
            return

        abs_path = self.base_dir / rel_path
        if not abs_path.exists():
            logger.error(f"文件不存在: {rel_path}")
            return

        new_hash = self._hash_file(abs_path)
        manifest["files"][rel_path] = new_hash
        manifest["generated_at"] = datetime.now().isoformat()

        # 重新计算 HMAC
        manifest["manifest_hmac"] = self._compute_manifest_hmac(manifest.copy())

        self.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        logger.info(f"🔑 已更新清单: {rel_path}")


# ============================================================
# 兼容旧 API 的函数（保持向后兼容）
# ============================================================

def generate_integrity_file(output_path: str = "integrity.json",
                            root_dir: str = ".") -> str:
    """生成完整性校验文件（兼容旧 API）"""
    checker = IntegrityChecker(manifest_path=output_path)
    checker.save_manifest(output_path)
    return str(Path(output_path).absolute())


def verify_integrity(integrity_file: str = "integrity.json") -> tuple[bool, list]:
    """
    验证文件完整性（兼容旧 API）
    返回 (是否通过, 问题列表)
    """
    checker = IntegrityChecker(manifest_path=integrity_file)
    try:
        report = checker.check_all()
    except IntegrityError as e:
        return False, [str(e)]

    issues = []
    for path in report.missing:
        issues.append(f"缺失: {path}")
    for path, expected, actual in report.modified:
        issues.append(f"校验失败: {path}")

    return report.is_clean, issues


# ============================================================
# 安全检查
# ============================================================

def check_security(config: dict = None) -> dict:
    """
    安全检查
    - 敏感文件权限
    - API key 是否硬编码
    - 沙盒配置
    """
    findings = []

    # 检查 .env 文件权限（Windows 跳过）
    env_file = Path(".env")
    if env_file.exists() and os.name != "nt":
        mode = env_file.stat().st_mode
        if mode & 0o077:  # 其他用户有权限
            findings.append("⚠️ .env 文件权限过于开放，建议 chmod 600")

    # 检查是否有 API key 暴露在提交中
    dangerous_patterns = ["sk-", "AKID", "LTAI"]
    for py_file in Path("src").rglob("*.py"):
        try:
            content = py_file.read_text(errors="ignore")
        except Exception:
            continue

        for pat in dangerous_patterns:
            if pat in content:
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if pat in line and "=" not in line and "#" not in line:
                        findings.append(f"⚠️ 疑似 API key 硬编码: {py_file}:{i+1}")

    return {
        "safe": len(findings) == 0,
        "findings": findings,
    }

