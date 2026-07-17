"""
数据库模块 — SQLite + SQLAlchemy ORM
四张表: resources / task_logs / source_sites / conversation_history
"""
import base64
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey,
    Index, JSON, create_engine, event
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship
from loguru import logger
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# ===== 持久化数据目录 =====

def _get_data_dir() -> Path:
    """获取持久化数据目录（兼容源码运行和 PyInstaller 打包）
    
    优先级：
    1. config.yaml 中的 storage.data_dir（避免构建时被清除）
    2. PyInstaller 打包：优先复用源码 data 目录，避免对话丢失
    3. PyInstaller 打包回退：EXE 同目录下的 data 文件夹
    4. 源码运行：项目根目录下的 data 文件夹
    """
    # 优先从配置文件读取自定义数据目录
    config_dir = _try_read_config_data_dir()
    if config_dir:
        return config_dir
    
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包：检测源码 data 目录是否存在（保持跨运行数据一致）
        exe_dir = Path(sys.executable).parent          # dist/7tan-editor/
        dist_dir = exe_dir.parent                       # dist/
        source_data = dist_dir.parent / "data"          # 项目根/data/
        if source_data.exists() and (source_data / "games.db").exists():
            return source_data
        # 回退：EXE 同级 data 目录
        return exe_dir / "data"
    else:
        # 源码运行：项目根目录下的 data 文件夹
        return Path(__file__).parent.parent.parent / "data"


def _try_read_config_data_dir() -> Optional[Path]:
    """尝试从 config.yaml 读取 storage.data_dir，用于将数据目录指向 dist 之外"""
    try:
        import yaml
        if getattr(sys, 'frozen', False):
            config_path = Path(sys.executable).parent / "config" / "config.yaml"
        else:
            config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            if data and 'storage' in data and data['storage'].get('data_dir'):
                path = Path(data['storage']['data_dir'])
                path.mkdir(parents=True, exist_ok=True)
                return path
    except Exception:
        pass
    return None


# ===== 密码加密工具 =====

_KEY_FILE = _get_data_dir() / ".encryption_key"
_SALT_FILE = _get_data_dir() / ".encryption_salt"
_fernet: Fernet = None


def _get_fernet() -> Fernet:
    """获取或创建 Fernet 加密实例"""
    global _fernet
    if _fernet is not None:
        return _fernet

    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 读取或生成 salt
    if _SALT_FILE.exists():
        salt = _SALT_FILE.read_bytes()
    else:
        salt = os.urandom(16)
        _SALT_FILE.write_bytes(salt)

    # 读取或生成 key（使用机器标识 + salt 派生）
    if _KEY_FILE.exists():
        key = _KEY_FILE.read_bytes()
    else:
        # 使用机器名 + 固定种子派生密钥
        machine_id = os.environ.get("COMPUTERNAME", "7tan-editor")
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
        _KEY_FILE.write_bytes(key)

    _fernet = Fernet(key)
    return _fernet


def encrypt_password(plaintext: str) -> str:
    """加密密码"""
    if not plaintext:
        return ""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_password(ciphertext: str) -> str:
    """解密密码"""
    if not ciphertext:
        return ""
    try:
        f = _get_fernet()
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        logger.warning("⚠️ 密码解密失败，可能密钥已变更")
        return ""


class Base(DeclarativeBase):
    pass


class Resource(Base):
    """资源表 — 游戏 + 软件"""
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_type = Column(String, nullable=False, default="game")  # 'game' | 'software'
    title = Column(String, nullable=False)
    original_title = Column(String)
    alias = Column(String)

    # 来源信息
    source_url = Column(String)
    source_site = Column(String)
    source_id = Column(String)

    # 分类
    category = Column(String)

    # 版本信息
    version = Column(String)
    is_update = Column(Integer, default=0)
    previous_id = Column(Integer)
    update_log = Column(Text)

    # 基本信息
    platform = Column(String)
    language = Column(String)
    file_size = Column(String)
    file_size_bytes = Column(Integer)

    # AI 改写内容
    intro = Column(Text)
    features = Column(JSON)
    requirements = Column(JSON)
    install_guide = Column(Text)
    tags = Column(JSON)

    # 资源文件
    logo_local = Column(String)
    logo_remote = Column(String)
    screenshots_local = Column(JSON)
    screenshots_remote = Column(JSON)

    # 下载链接
    download_original = Column(String)
    download_oss = Column(String)
    download_md5 = Column(String)
    package_local = Column(String)

    # 时间线
    source_publish_date = Column(String)
    status = Column(String, default="pending")
    publish_id = Column(Integer)
    publish_url = Column(String)
    error_message = Column(Text)

    # Token 成本
    token_prompt = Column(Integer, default=0)
    token_completion = Column(Integer, default=0)
    cost_estimate = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    published_at = Column(DateTime)

    __table_args__ = (
        Index("idx_resources_type", "resource_type"),
        Index("idx_resources_status", "status"),
        Index("idx_resources_source", "source_site", "source_id"),
        Index("idx_resources_title", "title"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id, "resource_type": self.resource_type,
            "title": self.title, "original_title": self.original_title,
            "alias": self.alias, "source_url": self.source_url,
            "source_site": self.source_site, "source_id": self.source_id,
            "category": self.category, "version": self.version,
            "is_update": self.is_update, "previous_id": self.previous_id,
            "update_log": self.update_log, "platform": self.platform,
            "language": self.language, "file_size": self.file_size,
            "file_size_bytes": self.file_size_bytes, "intro": self.intro,
            "features": self.features, "requirements": self.requirements,
            "install_guide": self.install_guide, "tags": self.tags,
            "logo_local": self.logo_local, "logo_remote": self.logo_remote,
            "screenshots_local": self.screenshots_local,
            "screenshots_remote": self.screenshots_remote,
            "download_original": self.download_original,
            "download_oss": self.download_oss, "package_local": self.package_local,
            "source_publish_date": self.source_publish_date,
            "status": self.status, "publish_id": self.publish_id,
            "publish_url": self.publish_url, "error_message": self.error_message,
            "token_prompt": self.token_prompt,
            "token_completion": self.token_completion,
            "cost_estimate": self.cost_estimate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }


class TaskLog(Base):
    """任务日志表"""
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(Integer, ForeignKey("resources.id"))
    task_type = Column(String)       # browse/download/rewrite/upload/publish/review
    status = Column(String)          # running/success/failed/retrying
    message = Column(Text)
    retry_count = Column(Integer, default=0)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)

    resource = relationship("Resource", backref="task_logs")

    def to_dict(self) -> dict:
        return {
            "id": self.id, "resource_id": self.resource_id,
            "task_type": self.task_type, "status": self.status,
            "message": self.message, "retry_count": self.retry_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


class SourceSite(Base):
    """源站配置表"""
    __tablename__ = "source_sites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    site_type = Column(String, default="game")  # 'game' | 'software' | 'both'
    need_login = Column(Integer, default=0)
    login_url = Column(String)
    login_username = Column(String)
    login_password = Column(String)       # 加密存储
    cookies_json = Column(Text)
    enabled = Column(Integer, default=1)
    last_crawl_at = Column(DateTime)
    crawl_interval = Column(Integer, default=360)  # 分钟
    notes = Column(Text)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "url": self.url,
            "site_type": self.site_type, "need_login": self.need_login,
            "login_url": self.login_url, "login_username": self.login_username,
            "enabled": self.enabled,
            "last_crawl_at": self.last_crawl_at.isoformat() if self.last_crawl_at else None,
            "crawl_interval": self.crawl_interval, "notes": self.notes,
        }

    def set_password(self, plaintext: str):
        """加密存储密码"""
        self.login_password = encrypt_password(plaintext)

    def get_password(self) -> str:
        """解密获取密码"""
        return decrypt_password(self.login_password or "")


class ConversationHistory(Base):
    """对话历史表"""
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String)        # 'user' | 'assistant' | 'tool'
    content = Column(Text)
    tool_name = Column(String)
    session_id = Column(String)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "role": self.role, "content": self.content,
            "tool_name": self.tool_name, "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# 全局引擎和会话工厂
_engine = None
_SessionLocal = None


def get_engine(db_path: str = None):
    """获取数据库引擎（单例）"""
    global _engine
    if _engine is None:
        if db_path is None:
            db_path = _get_data_dir() / "games.db"
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        _engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )

        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return _engine


def get_session() -> Session:
    """获取一个新的数据库会话"""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        from sqlalchemy.orm import sessionmaker
        _SessionLocal = sessionmaker(bind=engine)
    return _SessionLocal()


def init_db(db_path: str = None):
    """初始化数据库（创建所有表）"""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    logger.info("✅ 数据库初始化完成")
