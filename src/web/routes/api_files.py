"""
文件浏览与编辑 API — 网页版代码编辑器（类 Harness 工作区）

GET    /api/files/tree?dir=rel      — 列出目录子项（懒加载）
GET    /api/files/read?path=rel     — 读取文本文件（≤2MB，拒绝二进制/敏感文件）
POST   /api/files/write             — 写入/覆盖文件 {path, content}（审计到 code_changes）
POST   /api/files/create            — 新建文件或文件夹 {path, type}
DELETE /api/files/delete?path=rel   — 删除文件（或空目录）

安全边界：
- 所有路径必须解析到项目根目录内（防目录穿越）
- 敏感文件/目录黑名单：.env*、.api_token、*.key/*.pem、*.db/*.sqlite、
  __pycache__、.git、node_modules 等拒绝读写
- 大目录/隐藏目录（node_modules、.git、.venv 等）树浏览标记 hidden，前端不展开
- 写操作记录审计事件（复用 code_change_bus，自动出现在「代码变更」页）
- 目录删除仅允许空目录（防止误删整个项目）
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api/files", tags=["files"])


def _get_project_root() -> Path:
    """获取项目根目录 — 兼容开发模式和 PyInstaller 打包"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent.parent


PROJECT_ROOT = _get_project_root()

# 隐藏目录（树浏览标记 hidden 不展开；读写一律拒绝）
HIDDEN_DIRS = {
    ".git", ".idea", ".vscode", ".venv", "venv", "__pycache__",
    "node_modules", "dist", "build", "logs",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".gitignore",
}
# 隐藏但允许读写的小文件例外（项目常用）
_HIDDEN_EXCEPT = {".gitignore", ".env.example", ".npmrc", ".yarnrc"}

# 敏感文件后缀（读写拒绝：密钥 / 数据库 / 二进制）
SENSITIVE_SUFFIXES = (
    ".key", ".pem", ".pfx", ".p12",
    ".db", ".sqlite", ".sqlite3",
    ".pyc", ".pyd", ".dll", ".exe", ".zip", ".rar", ".7z", ".gz", ".tar",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".svg",
)

MAX_READ_BYTES = 2 * 1024 * 1024   # 读文件上限 2MB
MAX_WRITE_CHARS = 2 * 1024 * 1024  # 写文件上限 2MB（字符）


def _resolve(rel: str) -> Optional[Path]:
    """把用户提供的相对路径解析为根内绝对路径；越界/非法返回 None。"""
    rel = (rel or "").strip().replace("\\", "/").lstrip("/")
    if not rel:
        return PROJECT_ROOT
    p = (PROJECT_ROOT / rel).resolve()
    try:
        p.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return None
    return p


def _is_sensitive(path: Path) -> bool:
    """敏感路径检查：任一路径段命中隐藏目录，或文件名命中敏感规则 → True"""
    try:
        rel = path.resolve().relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return True
    for part in rel.parts:
        if part in HIDDEN_DIRS:
            return True
        if part.startswith(".") and part not in _HIDDEN_EXCEPT:
            return True
        if part.startswith(".env"):
            return True
        low = part.lower()
        if low == ".api_token":
            return True
        for suf in SENSITIVE_SUFFIXES:
            if low.endswith(suf):
                return True
    return False


def _rel_str(p: Path) -> str:
    """绝对路径 → 相对项目根的正斜杠路径（供前端展示）"""
    try:
        return p.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


@router.get("/tree")
async def file_tree(dir: str = Query("", description="相对目录，空=项目根")):
    """列出目录子项（懒加载，一次只返回一层）"""
    root = _resolve(dir)
    if root is None:
        return {"error": "路径越界，仅允许项目根目录内", "entries": []}
    if not root.exists() or not root.is_dir():
        return {"error": "目录不存在", "entries": []}
    if _is_sensitive(root):
        return {"error": "该目录已列入隐藏/保护列表，不可浏览", "entries": [], "hidden": True}
    try:
        entries = []
        for child in sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            try:
                is_dir = child.is_dir()
            except OSError:
                continue
            # 隐藏判定：目录名在隐藏列表，或以 . 开头（.gitignore/.env.example 除外）
            hidden = (is_dir and child.name in HIDDEN_DIRS) or (
                child.name.startswith(".") and child.name not in _HIDDEN_EXCEPT
            )
            st = None
            try:
                st = child.stat()
            except OSError:
                pass
            entries.append({
                "name": child.name,
                "path": _rel_str(child),
                "type": "dir" if is_dir else "file",
                "hidden": bool(hidden),
                "size": st.st_size if (st and not is_dir) else 0,
                "mtime": int(st.st_mtime) if st else 0,
            })
        return {"root": _rel_str(root) or ".", "entries": entries}
    except Exception as e:
        return {"error": str(e), "entries": []}


@router.get("/read")
async def file_read(path: str = Query(..., description="文件相对路径")):
    """读取文本文件内容（≤2MB，拒绝二进制与敏感文件）"""
    p = _resolve(path)
    if p is None:
        return {"error": "路径越界，仅允许项目根目录内"}
    if not p.exists() or not p.is_file():
        return {"error": "文件不存在"}
    if _is_sensitive(p):
        return {"error": "敏感文件禁止在线读写（.env / 密钥 / 数据库 / 图片等）"}
    try:
        size = p.stat().st_size
        if size > MAX_READ_BYTES:
            return {"error": f"文件过大（{size / 1024 / 1024:.1f}MB > 2MB），请在本地编辑器打开"}
        data = p.read_bytes()
        if b"\x00" in data[:8192]:
            return {"error": "二进制文件不支持在线编辑"}
        text = data.decode("utf-8", errors="replace")
        return {"path": _rel_str(p), "content": text, "size": size, "mtime": int(p.stat().st_mtime)}
    except Exception as e:
        return {"error": f"读取失败: {e}"}


class FileWriteRequest(BaseModel):
    path: str
    content: str


@router.post("/write")
async def file_write(req: FileWriteRequest):
    """写入/覆盖文件（自动审计到「代码变更」页）"""
    p = _resolve(req.path)
    if p is None:
        return {"error": "路径越界，仅允许项目根目录内"}
    if p.is_dir():
        return {"error": "目标是一个目录，不能写入"}
    if _is_sensitive(p):
        return {"error": "敏感文件禁止在线读写（.env / 密钥 / 数据库 / 图片等）"}
    if len(req.content) > MAX_WRITE_CHARS:
        return {"error": "内容过大（>2MB）"}
    old_text = None
    try:
        if p.exists():
            old_text = p.read_text(encoding="utf-8", errors="replace")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(req.content, encoding="utf-8")
    except Exception as e:
        return {"error": f"写入失败: {e}"}
    # 审计 → 代码变更页
    try:
        from ...utils.code_change_bus import publish_file_change
        publish_file_change(
            action="web_edit",
            path=str(p),
            old_text=old_text,
            new_text=req.content,
            summary=f"[WEB 编辑器] {'修改' if old_text is not None else '新建'} {p.name}",
        )
    except Exception as e:
        logger.warning(f"[WEB 编辑器] 审计记录失败: {e}")
    logger.info(f"📝 [WEB 编辑器] 保存文件: {p}")
    return {"success": True, "path": _rel_str(p)}


class FileCreateRequest(BaseModel):
    path: str          # 完整相对路径（含新名称）
    type: str = "file" # file / dir


@router.post("/create")
async def file_create(req: FileCreateRequest):
    """新建文件或文件夹"""
    p = _resolve(req.path)
    if p is None:
        return {"error": "路径越界，仅允许项目根目录内"}
    if _is_sensitive(p):
        return {"error": "目标路径受保护，不可创建"}
    if p.exists():
        return {"error": "已存在同名文件/目录"}
    try:
        if req.type == "dir":
            p.mkdir(parents=True, exist_ok=False)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("", encoding="utf-8")
    except Exception as e:
        return {"error": f"创建失败: {e}"}
    logger.info(f"📝 [WEB 编辑器] 新建 {'目录' if req.type == 'dir' else '文件'}: {p}")
    return {"success": True, "path": _rel_str(p)}


@router.delete("/delete")
async def file_delete(path: str = Query(..., description="文件相对路径")):
    """删除文件或空目录（目录非空拒绝，防误删）"""
    p = _resolve(path)
    if p is None:
        return {"error": "路径越界，仅允许项目根目录内"}
    if not p.exists():
        return {"error": "目标不存在"}
    if _is_sensitive(p):
        return {"error": "目标受保护，不可删除"}
    if p.resolve() == PROJECT_ROOT.resolve():
        return {"error": "不能删除项目根目录"}
    try:
        if p.is_dir():
            if any(p.iterdir()):
                return {"error": "目录非空，禁止删除（防止误删整个目录）"}
            p.rmdir()
        else:
            p.unlink()
    except Exception as e:
        return {"error": f"删除失败: {e}"}
    logger.info(f"🗑️ [WEB 编辑器] 删除: {p}")
    return {"success": True}

