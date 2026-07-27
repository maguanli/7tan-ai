"""
安全修改门控模块
编译成 .pyd 后无法被反编译，保护文件修改权限检查。

职责:
    - 修改前：语法检查 + 自动备份 + 关键文件保护
    - 启动失败后：从备份回滚
    - 权限门控：检查是否允许修改安装目录内的文件
"""
import ast
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .license_verify import verify_license, LicenseError


# ============================================================
# 配置
# ============================================================

# 安装目录（编译时确定）
_INSTALL_DIR = Path(__file__).resolve().parent.parent.parent

# 备份目录
_BACKUP_DIR = _INSTALL_DIR / "data" / "backups"
_BACKUP_INDEX = _BACKUP_DIR / "index.json"

# 最大备份版本数
_MAX_BACKUPS = 5

# 不允许直接修改的关键文件
_PROTECTED_FILES: set[str] = {
    "main.py",
    "safe_modify.py",
    "safe_modify.pyd",
    "license_verify.py",
    "license_verify.pyd",
    "rsa_verify.py",
    "rsa_verify.pyd",
    "strings.py",
}


# ============================================================
# 异常类
# ============================================================

class ModifyRejected(Exception):
    """修改被拒绝"""
    pass


# ============================================================
# 内部辅助
# ============================================================

def _is_inside_install_dir(fp: Path) -> bool:
    """检查文件是否在安装目录内"""
    try:
        fp.resolve().relative_to(_INSTALL_DIR.resolve())
        return True
    except ValueError:
        return False


# ============================================================
# 修改前检查
# ============================================================

def pre_modify_check(filepath: str, new_content: str) -> bool:
    """
    修改前的安全检查。

    检查项:
        1. Python 语法检查
        2. 关键文件保护
        3. 自动备份原文件（仅安装目录内的文件）
        4. 文件大小合理性

    Args:
        filepath: 要修改的文件路径
        new_content: 新内容

    Returns:
        True 表示可以安全修改

    Raises:
        ModifyRejected: 检查不通过
    """
    fp = Path(filepath).resolve()

    # === 检查1: Python 语法 ===
    if fp.suffix == ".py":
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            raise ModifyRejected(f"语法错误，拒绝修改：{e.lineno}行 — {e.msg}")

    # === 检查2: 关键文件保护 ===
    if fp.name.lower() in _PROTECTED_FILES:
        raise ModifyRejected(
            f"核心文件 {fp.name} 不允许直接修改。\n"
            "请通过安全模块提供的接口操作。"
        )

    # === 检查3: 文件大小合理性 ===
    if fp.exists():
        old_size = fp.stat().st_size
        new_size = len(new_content.encode("utf-8"))
        if new_size < 10 and old_size > 1000:
            raise ModifyRejected(
                f"新内容过短（{new_size}字节 vs 原{old_size}字节），疑似误删，拒绝修改"
            )

    # === 检查4: 自动备份（仅安装目录内的文件） ===
    if fp.exists() and _is_inside_install_dir(fp):
        _create_backup(str(fp))

    return True


# ============================================================
# 备份管理
# ============================================================

def _load_index() -> dict:
    """加载备份索引"""
    if _BACKUP_INDEX.exists():
        try:
            return json.loads(_BACKUP_INDEX.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_index(index: dict) -> None:
    """保存备份索引"""
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    _BACKUP_INDEX.write_text(json.dumps(index, indent=2, ensure_ascii=False), "utf-8")


def _create_backup(filepath: str) -> str:
    """
    创建文件备份，保留最近 _MAX_BACKUPS 个版本。

    仅备份安装目录内的文件，目录外的文件跳过。

    Args:
        filepath: 要备份的文件路径（必须在安装目录内）

    Returns:
        备份文件路径，目录外文件返回空字符串
    """
    fp = Path(filepath).resolve()
    if not _is_inside_install_dir(fp):
        return ""

    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{fp.name}.{timestamp}"
    backup_path = _BACKUP_DIR / backup_name

    shutil.copy2(fp, backup_path)

    # 更新索引
    index = _load_index()
    key = str(fp.relative_to(_INSTALL_DIR.resolve()))
    if key not in index:
        index[key] = []
    index[key].append(backup_name)

    # 只保留最近 N 个
    while len(index[key]) > _MAX_BACKUPS:
        old = index[key].pop(0)
        old_path = _BACKUP_DIR / old
        if old_path.exists():
            old_path.unlink()

    _save_index(index)
    return str(backup_path)


def restore_latest_backup() -> list[str]:
    """
    回滚所有有备份的文件到最近版本。

    Returns:
        成功回滚的文件列表
    """
    index = _load_index()
    restored: list[str] = []

    for rel_path, backups in index.items():
        if not backups:
            continue

        # 取最近的备份
        latest_backup = backups[-1]
        backup_path = _BACKUP_DIR / latest_backup
        target_path = _INSTALL_DIR / rel_path

        if not backup_path.exists():
            continue

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, target_path)
            restored.append(rel_path)
        except OSError:
            continue

    return restored


def restore_all_from_backup() -> list[str]:
    """
    恢复所有文件的第一个备份版本（安全模式用）。

    Returns:
        成功恢复的文件列表
    """
    index = _load_index()
    restored: list[str] = []

    for rel_path, backups in index.items():
        if not backups:
            continue

        first_backup = backups[0]
        backup_path = _BACKUP_DIR / first_backup
        target_path = _INSTALL_DIR / rel_path

        if not backup_path.exists():
            continue

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, target_path)
            restored.append(rel_path)
        except OSError:
            continue

    return restored


# ============================================================
# 权限门控
# ============================================================

def can_modify_self(token_str: str) -> bool:
    """
    检查是否有权限修改软件自身。

    Args:
        token_str: JWT Token

    Returns:
        True 如果是专业版且未过期
    """
    try:
        result = verify_license(token_str)
        return result["level"] == "pro"
    except LicenseError:
        return False


def check_write_permission(target_path: str, token_str: str) -> bool:
    """
    写入文件前检查权限。

    - 目标在安装目录外 → 始终允许（用户自己的项目）
    - 目标在安装目录内 → 检查专业版授权

    Args:
        target_path: 写入目标路径
        token_str: JWT Token

    Returns:
        True 表示允许写入

    Raises:
        ModifyRejected: 权限不足
    """
    target = Path(target_path).resolve()

    # 不在安装目录内 → 允许
    if not _is_inside_install_dir(target):
        return True

    # 在安装目录内 → 检查专业版
    if not can_modify_self(token_str):
        raise ModifyRejected(
            "修改软件自身需要专业版授权。\n"
            "请在 7tan.com 升级到专业版（200元/半年）。"
        )

    return True


def get_backup_count() -> int:
    """获取当前备份数量"""
    index = _load_index()
    return sum(len(v) for v in index.values())
