"""
数据库模块 — SQLite + SQLAlchemy ORM
五张表: resources / task_logs / source_sites / ai_configs / conversation_history
"""
import base64
import json
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

    # 读取或生成 key（使用机器标识 + pyd 内置种子 + salt 派生）
    if _KEY_FILE.exists():
        key = _KEY_FILE.read_bytes()
    else:
        # P1-6b: 派生种子来自 sec_config.pyd（AES-256-GCM 加密，不落盘明文），
        #        攻击者仅凭源码/config.yaml 无法推断密钥，需逆向 pyd。
        #        兼容：已有 .encryption_key 文件的用户（老版本）继续用原密钥，数据不受影响。
        try:
            from ..security.sec_config import get_encryption_seed
            seed = get_encryption_seed().decode("utf-8", "ignore")
        except Exception:
            seed = ""
        machine_id = os.environ.get("COMPUTERNAME", "7tan-editor")
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(f"{machine_id}::{seed}".encode()))
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




class AiConfig(Base):
    """AI 模型配置表 — 替代 YAML 中的 ai.configs，集中管理所有 AI 模型设置"""
    __tablename__ = "ai_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String, nullable=False, unique=True)  # 如 'deepseek', 'glm-5.2'
    provider = Column(String, default="deepseek")
    model = Column(String, nullable=False)
    base_url = Column(String)
    api_key = Column(String)  # 加密存储
    context_window = Column(Integer, default=128000)
    max_tokens = Column(Integer, default=16384)
    temperature = Column(Float, default=0.25)
    is_active = Column(Integer, default=0)  # 1=当前激活
    extra_config = Column(JSON)  # 扩展配置
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self, mask_secrets: bool = False) -> dict:
        plain_key = self.get_api_key()
        if mask_secrets and len(plain_key) > 6:
            display_key = plain_key[:3] + "••••" + plain_key[-3:]
        else:
            display_key = plain_key
        return {
            "id": self.id, "config_key": self.config_key,
            "provider": self.provider, "model": self.model,
            "base_url": self.base_url, "api_key": display_key,
            "context_window": self.context_window,
            "max_tokens": self.max_tokens, "temperature": self.temperature,
            "is_active": self.is_active,
            "extra_config": self.extra_config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_api_key(self) -> str:
        """解密获取 API Key"""
        return decrypt_password(self.api_key or "")

    def set_api_key(self, plaintext: str):
        """加密存储 API Key"""
        self.api_key = encrypt_password(plaintext) if plaintext else ""


class AiVisionConfig(Base):
    """视觉 AI 模型配置表 — 桌面机器人视力增强（GLM-4V-Flash 等）"""
    __tablename__ = "ai_vision_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    api_key = Column(String)  # 加密存储
    base_url = Column(String, default="https://open.bigmodel.cn/api/paas/v4")
    model = Column(String, default="glm-4v-flash")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self, mask_secrets: bool = False) -> dict:
        plain_key = self.get_api_key()
        if mask_secrets and len(plain_key) > 6:
            display_key = plain_key[:3] + "••••" + plain_key[-3:]
        else:
            display_key = plain_key
        return {
            "id": self.id, "api_key": display_key,
            "base_url": self.base_url, "model": self.model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_api_key(self) -> str:
        """解密获取 API Key"""
        return decrypt_password(self.api_key or "")

    def set_api_key(self, plaintext: str):
        """加密存储 API Key"""
        self.api_key = encrypt_password(plaintext) if plaintext else ""


class ConversationHistory(Base):
    """对话历史表"""
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String)        # 'user' | 'assistant' | 'tool'
    content = Column(Text)
    tool_name = Column(String)
    session_id = Column(String)
    model = Column(String, default="")  # 生成该消息的 AI 模型
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "role": self.role, "content": self.content,
            "tool_name": self.tool_name, "session_id": self.session_id,
            "model": self.model or "",
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
    """初始化数据库（创建所有表 + 迁移 AI 配置）"""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    # 幂等迁移：为 conversation_history 添加 model 列（旧库升级）
    try:
        from sqlalchemy import text as _sa_text
        with engine.connect() as conn:
            cols = [r[1] for r in conn.execute(_sa_text("PRAGMA table_info(conversation_history)")).fetchall()]
            if "model" not in cols:
                conn.execute(_sa_text("ALTER TABLE conversation_history ADD COLUMN model VARCHAR DEFAULT ''"))
                conn.commit()
                logger.info("✅ 数据库迁移：conversation_history 增加 model 列")
    except Exception as e:
        logger.warning(f"数据库迁移(model列)跳过: {e}")
    # [优化] 为 conversation_history 添加复合索引（会话多时按 session 查询加速）
    try:
        from sqlalchemy import text as _sa_text2
        with engine.connect() as conn:
            conn.execute(_sa_text2("CREATE INDEX IF NOT EXISTS idx_conversation_session_created ON conversation_history (session_id, created_at)"))
            conn.commit()
            logger.info("✅ 数据库优化：conversation_history 增加 (session_id, created_at) 索引")
    except Exception as e:
        logger.warning(f"数据库索引创建跳过: {e}")
    # 从 YAML 迁移 AI 配置到数据库（仅首次）
    try:
        ensure_default_ai_config()
    except Exception as e:
        logger.warning(f"AI 配置迁移跳过: {e}")
    # 从 YAML/.env 迁移视觉模型配置到数据库（仅首次）
    try:
        migrate_vision_config_to_db()
    except Exception as e:
        logger.warning(f"视觉模型配置迁移跳过: {e}")
    # 从 JSON/TXT 迁移记忆和提示词到数据库（仅首次）
    try:
        migrate_memory_json_to_db()
    except Exception as e:
        logger.warning(f"记忆迁移跳过: {e}")
    try:
        migrate_prompts_txt_to_db()
    except Exception as e:
        logger.warning(f"提示词迁移跳过: {e}")
    # 环境引擎：空库时预置默认软件/引擎清单（发布包不含 db，首次运行此表为空）
    try:
        seed_default_installed_software()
    except Exception as e:
        logger.warning(f"环境引擎默认清单预置跳过: {e}")
    logger.info("✅ 数据库初始化完成")


# ===== AI 配置管理 =====

def get_all_ai_configs(mask_secrets: bool = True) -> list:
    """获取所有 AI 配置"""
    session = get_session()
    try:
        configs = session.query(AiConfig).order_by(AiConfig.id).all()
        return [c.to_dict(mask_secrets=mask_secrets) for c in configs]
    finally:
        session.close()


def get_active_ai_config(mask_secrets: bool = False) -> dict | None:
    """获取当前激活的 AI 配置"""
    session = get_session()
    try:
        cfg = session.query(AiConfig).filter(AiConfig.is_active == 1).first()
        return cfg.to_dict(mask_secrets=mask_secrets) if cfg else None
    finally:
        session.close()


def get_ai_config_by_key(config_key: str, mask_secrets: bool = False) -> dict | None:
    """按 config_key 获取 AI 配置"""
    session = get_session()
    try:
        cfg = session.query(AiConfig).filter(AiConfig.config_key == config_key).first()
        return cfg.to_dict(mask_secrets=mask_secrets) if cfg else None
    finally:
        session.close()


def save_ai_config(config_key: str, provider: str, model: str, base_url: str = "",
                   api_key: str = "", context_window: int = 128000,
                   max_tokens: int = 16384, temperature: float = 0.25,
                   is_active: int = 0, extra_config: dict = None) -> AiConfig:
    """保存或更新 AI 配置"""
    session = get_session()
    try:
        cfg = session.query(AiConfig).filter(AiConfig.config_key == config_key).first()
        if cfg is None:
            cfg = AiConfig(config_key=config_key)
            session.add(cfg)
        cfg.provider = provider
        cfg.model = model
        cfg.base_url = base_url
        cfg.context_window = context_window
        cfg.max_tokens = max_tokens
        cfg.temperature = temperature
        cfg.is_active = is_active
        cfg.extra_config = extra_config or {}
        if api_key and "••••" not in api_key:
            cfg.set_api_key(api_key)
        # 如果设置 is_active=1，先清除其他配置的激活状态
        if is_active:
            session.query(AiConfig).filter(
                AiConfig.config_key != config_key
            ).update({"is_active": 0})
        session.commit()
        logger.info(f"💾 AI 配置已保存: {config_key} ({model})")
        return cfg
    except Exception as e:
        session.rollback()
        logger.error(f"保存 AI 配置失败: {e}")
        raise
    finally:
        session.close()


def set_active_ai_config(config_key: str) -> bool:
    """切换激活的 AI 配置"""
    session = get_session()
    try:
        # 先清除所有
        session.query(AiConfig).update({"is_active": 0})
        # 设置目标
        result = session.query(AiConfig).filter(
            AiConfig.config_key == config_key
        ).update({"is_active": 1})
        session.commit()
        if result:
            logger.info(f"✅ 已激活 AI 配置: {config_key}")
            return True
        logger.warning(f"⚠️ 未找到 AI 配置: {config_key}")
        return False
    except Exception as e:
        session.rollback()
        logger.error(f"切换 AI 配置失败: {e}")
        return False
    finally:
        session.close()


def delete_ai_config(config_key: str) -> bool:
    """删除 AI 配置"""
    session = get_session()
    try:
        result = session.query(AiConfig).filter(AiConfig.config_key == config_key).delete()
        session.commit()
        if result:
            logger.info(f"🗑️ 已删除 AI 配置: {config_key}")
        return result > 0
    except Exception as e:
        session.rollback()
        logger.error(f"删除 AI 配置失败: {e}")
        return False
    finally:
        session.close()


# ===== 视觉 AI 模型配置管理（数据库存储） =====

def get_vision_config(mask_secrets: bool = True) -> dict | None:
    """获取视觉 AI 模型配置（单行）"""
    session = get_session()
    try:
        cfg = session.query(AiVisionConfig).order_by(AiVisionConfig.id).first()
        return cfg.to_dict(mask_secrets=mask_secrets) if cfg else None
    finally:
        session.close()


def save_vision_config(api_key: str = "", base_url: str = "",
                       model: str = "glm-4v-flash") -> dict:
    """保存视觉 AI 模型配置（单行 upsert，API Key 加密存储）"""
    session = get_session()
    try:
        cfg = session.query(AiVisionConfig).order_by(AiVisionConfig.id).first()
        if cfg is None:
            cfg = AiVisionConfig()
            session.add(cfg)
        if api_key and "••" not in api_key and "***" not in api_key:
            cfg.set_api_key(api_key)
        if base_url:
            cfg.base_url = base_url
        if model:
            cfg.model = model
        session.commit()
        logger.info(f"💾 视觉AI模型配置已保存到数据库: model={cfg.model}")
        return cfg.to_dict(mask_secrets=True)
    except Exception as e:
        session.rollback()
        logger.error(f"保存视觉AI模型配置失败: {e}")
        raise
    finally:
        session.close()


def delete_vision_config() -> bool:
    """删除视觉 AI 模型配置"""
    session = get_session()
    try:
        result = session.query(AiVisionConfig).delete()
        session.commit()
        if result:
            logger.info("🗑️ 已删除视觉AI模型配置")
        return result > 0
    except Exception as e:
        session.rollback()
        logger.error(f"删除视觉AI模型配置失败: {e}")
        return False
    finally:
        session.close()


def _read_project_env() -> dict:
    """读取项目根目录 .env 文件（键值对）"""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    result = {}
    if not env_path.exists():
        return result
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    except Exception:
        pass
    return result


def migrate_vision_config_to_db():
    """将 YAML/.env 中的视觉模型配置迁移到数据库（仅当数据库无记录且存在配置时）"""
    session = get_session()
    try:
        if session.query(AiVisionConfig).count() > 0:
            return
        api_key = base_url = model = ""
        try:
            from ..config.loader import load_config
            vision = (load_config().get("ai") or {}).get("vision") or {}
            api_key = str(vision.get("api_key", "") or "")
            base_url = str(vision.get("base_url", "") or "")
            model = str(vision.get("model", "") or "")
        except Exception:
            pass
        if not api_key or "${" in api_key:
            env = _read_project_env()
            api_key = api_key if api_key and "${" not in api_key else env.get("VISION_API_KEY", "")
            base_url = base_url or env.get("VISION_BASE_URL", "")
            model = model or env.get("VISION_MODEL", "")
        if api_key and "${" not in api_key:
            cfg = AiVisionConfig()
            cfg.set_api_key(api_key)
            cfg.base_url = base_url or "https://open.bigmodel.cn/api/paas/v4"
            cfg.model = model or "glm-4v-flash"
            session.add(cfg)
            session.commit()
            logger.info("👁️ 已从 YAML/.env 迁移视觉AI模型配置到数据库")
    except Exception as e:
        session.rollback()
        logger.warning(f"视觉AI模型配置迁移跳过: {e}")
    finally:
        session.close()


def migrate_ai_configs_from_yaml(yaml_config: dict):
    """将 YAML 中的 AI 配置迁移到数据库（首次初始化时调用）"""
    ai = yaml_config.get("ai", {})
    configs = ai.get("configs", {})
    active_key = ai.get("active", "")
    
    if not configs:
        return
    
    session = get_session()
    try:
        existing = session.query(AiConfig).count()
        if existing > 0:
            logger.info(f"📋 数据库已有 {existing} 条 AI 配置，跳过 YAML 迁移")
            return
        
        for key, cfg in configs.items():
            if not isinstance(cfg, dict):
                continue
            is_active = 1 if key == active_key else 0
            aicfg = AiConfig(
                config_key=key,
                provider=cfg.get("provider", "deepseek"),
                model=cfg.get("model", ""),
                base_url=cfg.get("base_url", ""),
                context_window=cfg.get("context_window", 128000),
                max_tokens=cfg.get("max_tokens", 16384),
                temperature=cfg.get("temperature", 0.25),
                is_active=is_active,
            )
            api_key = cfg.get("api_key", "")
            if api_key and not api_key.startswith("$"):
                aicfg.set_api_key(api_key)
            else:
                aicfg.api_key = api_key  # 保留 ${VAR} 引用
            session.add(aicfg)
            logger.info(f"📥 迁移 AI 配置: {key} ({cfg.get('model')})")
        
        session.commit()
        logger.info(f"✅ 已从 YAML 迁移 {len(configs)} 条 AI 配置到数据库")
    except Exception as e:
        session.rollback()
        logger.warning(f"⚠️ YAML 迁移失败（可能已存在）: {e}")
    finally:
        session.close()


def get_active_ai_config_raw() -> dict | None:
    """获取活跃配置的原始数据（含解密后的 api_key），用于 model_manager"""
    session = get_session()
    try:
        cfg = session.query(AiConfig).filter(AiConfig.is_active == 1).first()
        if not cfg:
            return None
        return {
            "config_key": cfg.config_key,
            "provider": cfg.provider,
            "model": cfg.model,
            "base_url": cfg.base_url,
            "api_key": cfg.get_api_key() or "",
            "context_window": cfg.context_window,
            "max_tokens": cfg.max_tokens,
            "temperature": cfg.temperature,
            "extra_config": cfg.extra_config,
        }
    finally:
        session.close()


def _get_ai_config_legacy(config_key: str) -> dict | None:
    """按 config_key 获取 AI 配置（含解密后的 api_key）"""
    session = get_session()
    try:
        cfg = session.query(AiConfig).filter(AiConfig.config_key == config_key).first()
        if not cfg:
            return None
        return {
            "config_key": cfg.config_key,
            "provider": cfg.provider,
            "model": cfg.model,
            "base_url": cfg.base_url,
            "api_key": cfg.get_api_key() or "",
            "context_window": cfg.context_window,
            "max_tokens": cfg.max_tokens,
            "temperature": cfg.temperature,
            "extra_config": cfg.extra_config,
        }
    finally:
        session.close()


def ensure_default_ai_config():
    """确保至少有一条 AI 配置（从 YAML 迁移或创建默认）"""
    session = get_session()
    try:
        count = session.query(AiConfig).count()
        if count > 0:
            return
    finally:
        session.close()
    
    # 尝试从 YAML 迁移
    from ..config.loader import load_config
    config = load_config()
    if config:
        migrate_ai_configs_from_yaml(config)
    
    # 再次检查
    session2 = get_session()
    try:
        count2 = session2.query(AiConfig).count()
        if count2 == 0:
            # 创建默认 deepseek 配置
            cfg = AiConfig(
                config_key="deepseek",
                provider="deepseek",
                model="deepseek-flash",
                base_url="https://api.deepseek.com/v1",
                context_window=128000,
                max_tokens=16384,
                temperature=0.25,
                is_active=1,
            )
            session2.add(cfg)
            session2.commit()
            logger.info("📝 已创建默认 AI 配置: deepseek")
    finally:
        session2.close()



# ===== Capability =====

class Capability(Base):
    """AI capability inventory"""
    __tablename__ = "capabilities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String, nullable=False)
    icon = Column(String, default="📦")
    sort_order = Column(Integer, default=0)
    name = Column(String, nullable=False)
    description = Column(String)
    tool_name = Column(String)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "category": self.category,
            "icon": self.icon, "sort_order": self.sort_order,
            "name": self.name, "description": self.description,
            "tool_name": self.tool_name, "is_active": self.is_active,
        }


def get_all_capabilities(active_only: bool = True) -> list:
    session = get_session()
    try:
        q = session.query(Capability).order_by(Capability.sort_order, Capability.id)
        if active_only:
            q = q.filter(Capability.is_active == 1)
        return [c.to_dict() for c in q.all()]
    finally:
        session.close()


def get_capabilities_grouped(active_only: bool = True) -> list:
    caps = get_all_capabilities(active_only=active_only)
    groups = {}
    group_order = {}
    for c in caps:
        cat = c["category"]
        if cat not in groups:
            groups[cat] = {"category": cat, "icon": c["icon"], "items": []}
            group_order[cat] = c["sort_order"]
        groups[cat]["items"].append({
            "name": c["name"], "desc": c["description"], "tool": c["tool_name"],
        })
    return sorted(groups.values(), key=lambda g: group_order.get(g["category"], 999))


def get_capability_summary() -> dict:
    caps = get_all_capabilities(active_only=True)
    cats = set(c["category"] for c in caps)
    return {
        "total_categories": len(cats),
        "total_tools": f"{len(caps)}+",
        "local_tools": [],
        "cloud_services": [],
    }


def migrate_capabilities_from_yaml():
    import yaml as _yaml
    session = get_session()
    try:
        if session.query(Capability).count() > 0:
            return
    finally:
        session.close()
    cap_path = Path(__file__).parent.parent.parent / "config" / "capabilities.yaml"
    if not cap_path.exists():
        return
    try:
        with open(cap_path, 'r', encoding='utf-8') as f:
            cap_data = _yaml.safe_load(f)
    except Exception:
        return
    caps = cap_data.get("capabilities", [])
    if not caps:
        return
    session = get_session()
    try:
        for idx, group in enumerate(caps):
            cat = group.get("category", "")
            icon = group.get("icon", "📦")
            for item in group.get("items", []):
                session.add(Capability(
                    category=cat, icon=icon, sort_order=idx,
                    name=item.get("name", ""),
                    description=item.get("desc", ""),
                    tool_name=item.get("tool", ""), is_active=1,
                ))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


# ===== InstalledSoftware =====

class InstalledSoftware(Base):
    """Installed software / environment inventory"""
    __tablename__ = "installed_software"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String, nullable=False)
    icon = Column(String, default="📦")
    name = Column(String, nullable=False, unique=True)
    version = Column(String)
    install_path = Column(String)
    executable = Column(String)
    is_in_path = Column(Integer, default=0)
    is_working = Column(Integer, default=1)
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "category": self.category, "icon": self.icon,
            "name": self.name, "version": self.version,
            "install_path": self.install_path, "executable": self.executable,
            "is_in_path": bool(self.is_in_path),
            "is_working": bool(self.is_working), "notes": self.notes,
        }


def get_installed_software_by_name(name: str):
    session = get_session()
    try:
        sw = session.query(InstalledSoftware).filter(InstalledSoftware.name == name).first()
        return sw.to_dict() if sw else None
    finally:
        session.close()


def seed_default_installed_software():
    """环境引擎：数据库为空时预置默认软件/引擎清单，避免新装用户看到空白页。

    发布包按安全策略剔除 *.db，用户首次运行 init_db 建表后此表为空；
    这里预置常用开发环境/引擎条目（版本待检测），用户点「重新扫描」后更新为真实结果。
    """
    _DEFAULT_SOFTWARE_SEED = [
        # ---- 💻 编程语言 ----
        ("Python",          "💻 编程语言", "🐍", "待检测（点击重新扫描更新）"),
        ("Pip",             "💻 编程语言", "📦", "待检测"),
        ("Node.js",         "💻 编程语言", "🟢", "待检测"),
        ("npm",             "💻 编程语言", "📦", "待检测"),
        ("Yarn",            "💻 编程语言", "🧶", "待检测"),
        ("pnpm",            "💻 编程语言", "⚡", "待检测"),
        ("Java (JDK)",      "💻 编程语言", "☕", "待检测"),
        ("Go",              "💻 编程语言", "🐹", "待检测"),
        ("Rust",            "💻 编程语言", "🦀", "待检测"),
        ("Ruby",            "💻 编程语言", "💎", "待检测"),
        ("PHP",             "💻 编程语言", "🐘", "待检测"),
        ("C/C++ (GCC/MinGW)", "💻 编程语言", "🛠", "待检测"),
        (".NET SDK",        "💻 编程语言", "🟣", "待检测"),
        # ---- 🛠 开发工具 ----
        ("Git",             "🛠 开发工具", "🔀", "待检测"),
        ("VS Code",         "🛠 开发工具", "🧩", "待检测"),
        ("IntelliJ IDEA",   "🛠 开发工具", "🧠", "待检测"),
        ("PyCharm",         "🛠 开发工具", "🐍", "待检测"),
        ("Eclipse",         "🛠 开发工具", "☕", "待检测"),
        ("Android Studio",  "🛠 开发工具", "🤖", "待检测"),
        ("Gradle",          "🛠 开发工具", "🏗", "待检测"),
        ("Maven",           "🛠 开发工具", "🅰", "待检测"),
        ("Docker",          "🛠 开发工具", "🐳", "待检测"),
        ("Docker Compose",  "🛠 开发工具", "🐳", "待检测"),
        ("kubectl",         "🛠 开发工具", "☸", "待检测"),
        ("Helm",            "🛠 开发工具", "⛵", "待检测"),
        ("Terraform",       "🛠 开发工具", "🏗", "待检测"),
        ("Ansible",         "🛠 开发工具", "🔧", "待检测"),
        ("Postman",         "🛠 开发工具", "📮", "待检测"),
        ("OpenSSH",         "🛠 开发工具", "🔑", "待检测"),
        # ---- 🗄 数据库 ----
        ("SQLite",          "🗄 数据库", "🗄", "待检测"),
        ("MySQL",           "🗄 数据库", "🐬", "待检测"),
        ("MariaDB",         "🗄 数据库", "🗄", "待检测"),
        ("PostgreSQL",      "🗄 数据库", "🐘", "待检测"),
        ("MongoDB",         "🗄 数据库", "🍃", "待检测"),
        ("Redis",           "🗄 数据库", "🔴", "待检测"),
        ("SQL Server",      "🗄 数据库", "🛢", "待检测"),
        # ---- 🌐 浏览器/网络 ----
        ("Google Chrome",   "🌐 浏览器", "🌐", "待检测"),
        ("Microsoft Edge",  "🌐 浏览器", "🧭", "待检测"),
        ("Firefox",         "🌐 浏览器", "🦊", "待检测"),
        ("curl",            "🌐 浏览器", "🌐", "待检测"),
        ("wget",            "🌐 浏览器", "⬇", "待检测"),
        ("Nginx",           "🌐 浏览器", "🌍", "待检测"),
        ("Apache HTTP Server", "🌐 浏览器", "🛰", "待检测"),
        ("OpenSSL",         "🌐 浏览器", "🔐", "待检测"),
        ("PuTTY",           "🌐 浏览器", "🖥", "待检测"),
        ("WinSCP",          "🌐 浏览器", "📁", "待检测"),
        ("FileZilla",       "🌐 浏览器", "🐇", "待检测"),
        # ---- 🎬 影音/录屏 ----
        ("FFmpeg",          "🎬 影音工具", "🎬", "待检测"),
        ("OBS Studio",      "🎬 影音工具", "🎥", "待检测"),
        ("Audacity",        "🎬 影音工具", "🎙", "待检测"),
        ("Edge TTS",        "🎬 影音工具", "🗣", "待检测"),
        ("Piper TTS",       "🎬 影音工具", "🗣", "待检测"),
        ("Whisper.cpp",     "🎬 影音工具", "🎤", "待检测"),
        ("剪映",             "🎬 影音工具", "✂", "待检测"),
        # ---- 🎨 AI绘画 ----
        ("Stable Diffusion WebUI", "🎨 AI绘画", "🎨", "待检测"),
        ("ComfyUI",         "🎨 AI绘画", "🖼", "待检测"),
        ("Anything V5 动漫模型", "🎨 AI绘画", "🎨", "待检测"),
        # ---- 🎮 游戏引擎 ----
        ("Godot",           "🎮 游戏引擎", "🎮", "待检测"),
        ("Unity Hub",       "🎮 游戏引擎", "🎮", "待检测"),
        ("Unity Editor",    "🎮 游戏引擎", "🎮", "待检测"),
        ("Unreal Engine",   "🎮 游戏引擎", "🎮", "待检测"),
        # ---- 📱 移动开发 ----
        ("Android SDK",     "📱 移动开发", "📱", "待检测"),
        ("ADB",             "📱 移动开发", "🔌", "待检测"),
        # ---- 🤖 自动化工具 ----
        ("pyautogui",       "🤖 自动化工具", "🤖", "待检测"),
        ("pyscreeze",       "🤖 自动化工具", "📸", "待检测"),
        ("pyperclip",       "🤖 自动化工具", "📋", "待检测"),
        ("pywinauto",       "🤖 自动化工具", "🖱", "待检测"),
        ("uiautomation",    "🤖 自动化工具", "🧩", "待检测"),
        ("mss",             "🤖 自动化工具", "🖥", "待检测"),
        ("pytesseract",     "🤖 自动化工具", "🔍", "待检测"),
        ("region_ocr",      "🤖 自动化工具", "🖼", "待检测"),
        # ---- 🗜 压缩工具 ----
        ("7-Zip",           "🗜 压缩工具", "🗜", "待检测"),
        ("WinRAR",          "🗜 压缩工具", "📦", "待检测"),
        ("Bandizip",        "🗜 压缩工具", "🎗", "待检测"),
        # ---- 🖥 系统工具 ----
        ("Windows Terminal", "🖥 系统工具", "🖥", "待检测"),
        ("PowerShell",      "🖥 系统工具", "⌨", "待检测"),
    ]
    session = get_session()
    try:
        cnt = session.query(InstalledSoftware).count()
        if cnt > 0:
            return
        for name, cat, icon, notes in _DEFAULT_SOFTWARE_SEED:
            session.add(InstalledSoftware(
                category=cat, icon=icon, name=name, version="",
                install_path="", executable="",
                is_in_path=0, is_working=0, notes=notes,
            ))
        session.commit()
        logger.info("✅ 环境引擎：已预置默认软件/引擎清单（可点重新扫描更新）")
    except Exception as e:
        session.rollback()
        logger.warning(f"环境引擎默认清单预置失败: {e}")
    finally:
        session.close()


def get_all_installed_software(grouped: bool = False):
    session = get_session()
    try:
        sw_list = session.query(InstalledSoftware).order_by(
            InstalledSoftware.category, InstalledSoftware.name
        ).all()
        items = [s.to_dict() for s in sw_list]
        if not grouped:
            return items
        groups = {}
        for item in items:
            cat = item["category"]
            if cat not in groups:
                groups[cat] = {"category": cat, "icon": item["icon"], "items": []}
            groups[cat]["items"].append(item)
        return list(groups.values())
    finally:
        session.close()


def upsert_installed_software(name, category="", icon="📦", version="",
                              install_path="", executable="",
                              is_in_path=False, is_working=True, notes=""):
    session = get_session()
    try:
        existing = session.query(InstalledSoftware).filter(
            InstalledSoftware.name == name
        ).first()
        if existing:
            existing.category = category or existing.category
            existing.icon = icon
            existing.version = version or existing.version
            existing.install_path = install_path or existing.install_path
            existing.executable = executable or existing.executable
            existing.is_in_path = 1 if is_in_path else existing.is_in_path
            existing.is_working = 1 if is_working else existing.is_working
            existing.notes = notes or existing.notes
            existing.updated_at = datetime.now()
        else:
            session.add(InstalledSoftware(
                category=category, icon=icon, name=name,
                version=version, install_path=install_path,
                executable=executable,
                is_in_path=1 if is_in_path else 0,
                is_working=1 if is_working else 0,
                notes=notes,
            ))
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"upsert_installed_software failed: {e}")
    finally:
        session.close()


def scan_and_sync_installed_software():
    """Scan system for installed dev tools and sync to DB.
    Strategy: 1) PATH check (where cmd)  2) known install paths  3) library check"""
    import subprocess
    import re

    # ---- Helper ----
    def _try_where(exe, vre=""):
        """Returns (ipath, version) or (None, None)"""
        try:
            r = subprocess.run(["where", exe], capture_output=True, text=True, timeout=5, shell=True)
            if r.returncode == 0 and r.stdout.strip():
                ipath = r.stdout.strip().split("\n")[0].strip()
                ver = ""
                if vre:
                    try:
                        r2 = subprocess.run([exe, vre], capture_output=True, text=True, timeout=5, shell=True)
                        m = re.search(vre, r2.stdout + r2.stderr)
                        if m:
                            ver = m.group(1)
                    except Exception:
                        pass
                return (ipath, ver)
        except Exception:
            pass
        return (None, None)

    # ===== PATH checks via 'where' =====
    path_checks = [
        ("FFmpeg",  "🎬 Video/Audio", "🎬", "ffmpeg",      "-version", r"ffmpeg version (\S+)"),
        ("Python",  "💻 Languages",   "🐍", "python",      "--version", r"Python (\S+)"),
        ("Git",     "🛠 DevOps",      "🔀", "git",         "--version", r"git version (\S+)"),
        ("Node.js", "💻 Languages",   "🟢", "node",        "--version", r"v(\S+)"),
        ("Java JDK","💻 Languages",   "☕", "java",        "-version",  r'version "(\S+)"'),
        ("Gradle",  "📱 Mobile Dev",  "🐘", "gradle",      "--version", r"Gradle (\S+)"),
        ("Docker",  "🛠 DevOps",      "🐳", "docker",      "--version", r"Docker version (\S+)"),
        ("7-Zip",   "📦 Compression", "🗜",  "7z",          "",          r"7-Zip (\S+)"),
        ("Edge TTS","🎬 Video/Audio", "🔊", "edge-tts",    "--version", ""),
        ("VS Code", "💻 Dev Tools",   "📝", "code",        "--version", r"^(\S+)"),
    ]

    for name, cat, icon, exe, varg, vre in path_checks:
        ipath, ver = _try_where(exe, vre)
        if ipath:
            upsert_installed_software(name=name, category=cat, icon=icon, version=ver,
                                      install_path=ipath, executable=exe, is_in_path=True, is_working=True)
        else:
            upsert_installed_software(name=name, category=cat, icon=icon,
                                      executable=exe, is_in_path=False, is_working=False)

    # ===== Known install paths (not in PATH, but we know where they are) =====
    known_paths = [
        ("FFmpeg",      "🎬 Video/Audio", "🎬", [
            r"G:\ffmpeg\bin\ffmpeg.exe",
            r"G:\AI_Video\bin\ffmpeg\bin\ffmpeg.exe",
            r"G:\AI_Video\ffmpeg\ffmpeg-8.1.2-essentials_build\bin\ffmpeg.exe",
            r"G:\ai_video_tools\ffmpeg\ffmpeg.exe",
            r"G:\tools\ffmpeg.exe",
        ]),
        ("VS Code",     "💻 Dev Tools",   "📝", [
            r"C:\Program Files\Microsoft VS Code\Code.exe",
            r"C:\Users\Administrator\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        ]),
        ("Node.js",     "💻 Languages",   "🟢", [
            r"C:\Program Files\nodejs\node.exe",
            r"C:\Program Files (x86)\nodejs\node.exe",
        ]),
        ("Docker",      "🛠 DevOps",      "🐳", [
            r"C:\Program Files\Docker\Docker\Docker Desktop.exe",
            r"C:\Program Files\Docker\Docker\resources\bin\docker.exe",
        ]),
        ("Gradle",      "📱 Mobile Dev",  "🐘", [
            r"C:\gradle\bin\gradle.bat",
            r"C:\Program Files\gradle\bin\gradle.bat",
        ]),
        ("Java JDK",    "💻 Languages",   "☕", [
            r"C:\Program Files\Java\jdk*\bin\java.exe",
            r"C:\Program Files\Eclipse Adoptium\jdk*\bin\java.exe",
            r"C:\Program Files\Android\Android Studio\jbr\bin\java.exe",
        ]),
        ("Android Studio","📱 Mobile Dev","🤖", [
            r"C:\Program Files\Android\Android Studio\bin\studio64.exe",
        ]),
        ("Android SDK", "📱 Mobile Dev",  "📱", [
            r"C:\Users\Administrator\AppData\Local\Android\Sdk",
        ]),
        ("7-Zip",       "📦 Compression", "🗜",  [
            r"C:\Program Files\7-Zip\7z.exe",
            r"G:\ai_video_tools\7-Zip\7z.exe",
        ]),
    ]

    for name, cat, icon, candidates in known_paths:
        # Only update if currently marked NOT working
        existing = get_installed_software_by_name(name)
        if existing and existing["is_working"]:
            continue
        for pat in candidates:
            if "*" in pat:
                import glob as _glob
                matches = _glob.glob(pat)
                if matches:
                    upsert_installed_software(name=name, category=cat, icon=icon,
                                              install_path=matches[0], is_working=True)
                    break
            elif os.path.exists(pat):
                upsert_installed_software(name=name, category=cat, icon=icon,
                                          install_path=pat, is_working=True)
                break

    # ===== PATH-only checks (directories, no exe) =====
    dir_checks = [
        ("ComfyUI",     "🎬 Video/Audio", "🎨", r"G:\AI_Video\comfyui"),
        ("SD WebUI",    "🎬 Video/Audio", "🖼",  r"G:\AI_Video\stable-diffusion-webui"),
        ("7tan Editor", "💻 Dev Tools",   "🅰", r"D:\7tan\7tanAI"),
    ]

    for name, cat, icon, chk in dir_checks:
        exists = os.path.isdir(chk)
        upsert_installed_software(
            name=name, category=cat, icon=icon,
            install_path=chk if exists else "", is_working=exists,
        )

    # ===== Library checks =====
    for name, cat, icon, notes in [
        ("MoviePy", "🎬 Video/Audio", "🎞", "Python lib, via pip"),
    ]:
        upsert_installed_software(
            name=name, category=cat, icon=icon, is_working=True, notes=notes,
        )

    logger.info("Installed software scan completed")


# ===== Memory =====

class Memory(Base):
    """AI 持久化记忆存储"""
    __tablename__ = "memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    section = Column(String, nullable=False, index=True)
    key = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    importance = Column(String, default="medium")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_memory_section_key", "section", "key", unique=True),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id, "section": self.section, "key": self.key,
            "content": self.content, "importance": self.importance,
            "created_at": str(self.created_at)[:19] if self.created_at else "",
            "updated_at": str(self.updated_at)[:19] if self.updated_at else "",
        }


def upsert_memory(section: str, key: str, content: str, importance: str = "medium") -> dict:
    """插入或更新一条记忆"""
    session = get_session()
    try:
        existing = session.query(Memory).filter(
            Memory.section == section, Memory.key == key
        ).first()
        if existing:
            existing.content = content
            existing.importance = importance
            existing.updated_at = datetime.now()
            result = {"action": "updated", "id": existing.id}
        else:
            m = Memory(section=section, key=key, content=content, importance=importance)
            session.add(m)
            session.flush()
            result = {"action": "created", "id": m.id}
        session.commit()
        return result
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_all_memories(section: str = None, keyword: str = None, limit: int = 500) -> list:
    """查询记忆列表"""
    session = get_session()
    try:
        q = session.query(Memory).order_by(
            Memory.updated_at.desc()
        )
        if section:
            q = q.filter(Memory.section == section)
        if keyword:
            kw = f"%{keyword}%"
            q = q.filter(
                (Memory.key.ilike(kw)) | (Memory.content.ilike(kw))
            )
        return [m.to_dict() for m in q.limit(limit).all()]
    finally:
        session.close()


def get_memory_summary() -> list:
    """记忆存储概览"""
    session = get_session()
    try:
        from sqlalchemy import func, case
        sections = session.query(
            Memory.section,
            func.count(Memory.id).label("total"),
            func.sum(
                case((Memory.importance == "high", 1), else_=0)
            ).label("high_count"),
            func.max(Memory.updated_at).label("last_updated"),
        ).group_by(Memory.section).all()
        return [
            {
                "section": s[0], "total": s[1], "high_count": s[2] or 0,
                "last_updated": str(s[3])[:19] if s[3] else "",
            }
            for s in sections
        ]
    finally:
        session.close()


def delete_memory(section: str, key: str) -> bool:
    """删除一条记忆"""
    session = get_session()
    try:
        m = session.query(Memory).filter(
            Memory.section == section, Memory.key == key
        ).first()
        if m:
            session.delete(m)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


# ===== 7Tan 模型记忆（tan_model_memory 表） =====

class TanModelMemoryEntry(Base):
    """7Tan 模型记忆存储 — 决策轨迹 / 预测误差历史（替代 JSON 文件持久化）

    结构：kind 区分两类数据，payload 存 JSON 序列化内容。
      - kind='traces'     → payload = [ {scene, action, action_finished, ...}, ... ]
      - kind='pe_history' → payload = [ 预测误差记录, ... ]
    """
    __tablename__ = "tan_model_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kind = Column(String, nullable=False, unique=True, index=True)
    payload = Column(Text, nullable=False)   # JSON 序列化
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "kind": self.kind,
            "updated_at": str(self.updated_at)[:19] if self.updated_at else "",
        }


def _ensure_tan_model_memory_table():
    """确保 tan_model_memory 表存在（幂等，仅建缺失表）"""
    try:
        Base.metadata.create_all(get_engine())
    except Exception as e:
        logger.warning(f"创建 tan_model_memory 表失败: {e}")


def load_tan_model_memory() -> dict:
    """读取 7Tan 模型记忆（数据库主存储）

    返回 {'traces': [...], 'pe_history': [...]}；无数据/异常返回空结构。
    """
    _ensure_tan_model_memory_table()
    out = {"traces": [], "pe_history": [], "knowledge": []}
    session = get_session()
    try:
        rows = session.query(TanModelMemoryEntry).all()
        for r in rows:
            try:
                out[r.kind] = json.loads(r.payload or "[]")
            except Exception:
                logger.warning(f"解析 7Tan 模型记忆 kind={r.kind} 失败，置空")
                out[r.kind] = []
    except Exception as e:
        logger.warning(f"读取 7Tan 模型记忆失败: {e}")
    finally:
        session.close()
    return out


def save_tan_model_memory(traces: list, pe_history: list, knowledge: list = None) -> bool:
    """保存 7Tan 模型记忆（整体覆盖 traces / pe_history 两条记录）"""
    _ensure_tan_model_memory_table()
    session = get_session()
    ok = True
    try:
        for kind, data in (("traces", traces), ("pe_history", pe_history), ("knowledge", knowledge or [])):
            payload = json.dumps(data or [], ensure_ascii=False)
            existing = session.query(TanModelMemoryEntry).filter(
                TanModelMemoryEntry.kind == kind
            ).first()
            if existing:
                existing.payload = payload
                existing.updated_at = datetime.now()
            else:
                session.add(TanModelMemoryEntry(kind=kind, payload=payload))
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"保存 7Tan 模型记忆失败: {e}")
        ok = False
    finally:
        session.close()
    return ok


# ===== Site Credential =====

class SiteCredential(Base):
    """站点凭据表 — 加密存储各网站登录凭据，替代 .env 明文密码
    
    支持两种认证方式：
    1. token: JWT Token（优先，通过 API 登录获取，可自动续期）
    2. password: 传统密码（回退方案，加密存储）
    """
    __tablename__ = "site_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site = Column(String, nullable=False, unique=True, index=True)  # '7tan_admin' / '7tan_api' 等
    username = Column(String, default="")
    password_encrypted = Column(String, default="")   # 加密存储的密码（回退方案）
    jwt_token = Column(Text, default="")               # JWT Token（优先使用）
    token_expires_at = Column(DateTime)                 # Token 过期时间
    cookies_json = Column(Text, default="")            # 浏览器 cookies（回退方案）
    api_base_url = Column(String, default="")          # API 基础 URL
    notes = Column(String, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def set_password(self, plaintext: str):
        """加密存储密码"""
        self.password_encrypted = encrypt_password(plaintext) if plaintext else ""

    def get_password(self) -> str:
        """解密获取密码"""
        return decrypt_password(self.password_encrypted or "")

    def set_token(self, token: str, expires_in: int = 2592000):
        """设置 JWT Token 及过期时间"""
        import time as _time
        self.jwt_token = token
        self.token_expires_at = datetime.fromtimestamp(_time.time() + expires_in)

    def is_token_valid(self) -> bool:
        """检查 Token 是否有效（未过期）"""
        import time as _time
        if not self.jwt_token:
            return False
        if not self.token_expires_at:
            return False
        return _time.time() < self.token_expires_at.timestamp()

    def to_dict(self, mask_secrets: bool = True) -> dict:
        d = {
            "id": self.id, "site": self.site, "username": self.username,
            "has_password": bool(self.password_encrypted),
            "has_token": bool(self.jwt_token),
            "token_valid": self.is_token_valid(),
            "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
            "api_base_url": self.api_base_url,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if not mask_secrets:
            d["password"] = self.get_password()
            d["jwt_token"] = self.jwt_token
        return d


# ----- SiteCredential CRUD -----

def get_site_credential(site: str, unmask: bool = False) -> dict | None:
    """获取站点凭据"""
    session = get_session()
    try:
        cred = session.query(SiteCredential).filter(SiteCredential.site == site).first()
        if cred:
            return cred.to_dict(mask_secrets=not unmask)
        return None
    finally:
        session.close()


def save_site_credential(site: str, username: str = "", password: str = "",
                         jwt_token: str = "", expires_in: int = 0,
                         api_base_url: str = "", cookies_json: str = "",
                         notes: str = "") -> dict:
    """保存或更新站点凭据。password 和 jwt_token 均会自动加密。
    
    Returns:
        {"success": True/False, "message": "...", "cred": {...}}
    """
    session = get_session()
    try:
        cred = session.query(SiteCredential).filter(SiteCredential.site == site).first()
        if cred is None:
            cred = SiteCredential(site=site)
            session.add(cred)

        if username:
            cred.username = username
        if password:
            cred.set_password(password)
        if jwt_token:
            cred.set_token(jwt_token, expires_in or 2592000)
        if api_base_url:
            cred.api_base_url = api_base_url
        if cookies_json:
            cred.cookies_json = cookies_json
        if notes:
            cred.notes = notes

        session.commit()
        logger.info(f"💾 站点凭据已保存: {site}")
        return {"success": True, "message": f"凭据 {site} 已保存",
                "cred": cred.to_dict(mask_secrets=True)}
    except Exception as e:
        session.rollback()
        logger.error(f"保存站点凭据失败: {e}")
        return {"success": False, "message": str(e)}
    finally:
        session.close()


def delete_site_credential(site: str) -> bool:
    """删除站点凭据"""
    session = get_session()
    try:
        result = session.query(SiteCredential).filter(SiteCredential.site == site).delete()
        session.commit()
        return result > 0
    except Exception as e:
        session.rollback()
        logger.error(f"删除站点凭据失败: {e}")
        return False
    finally:
        session.close()


def get_all_site_credentials() -> list:
    """获取所有站点凭据（脱敏）"""
    session = get_session()
    try:
        creds = session.query(SiteCredential).order_by(SiteCredential.id).all()
        return [c.to_dict(mask_secrets=True) for c in creds]
    finally:
        session.close()


def get_admin_password() -> str:
    """
    获取 7tan 管理后台密码（优先从加密数据库，回退到 .env 环境变量）。
    
    迁移逻辑：如果数据库无记录但 .env 有明文密码，自动加密迁移到数据库。
    """
    import os as _os

    # 1. 优先从加密数据库获取
    session = get_session()
    try:
        cred = session.query(SiteCredential).filter(
            SiteCredential.site == "7tan_admin"
        ).first()
        if cred:
            pwd = cred.get_password()
            if pwd:
                return pwd
    finally:
        session.close()

    # 2. 回退：从 .env 读取明文密码（旧版兼容）
    env_pwd = _os.getenv("TANTAN_PASSWORD", "")
    if env_pwd:
        # 自动迁移：将明文密码加密存入数据库
        logger.info("🔐 检测到 .env 明文密码，正在加密迁移到数据库...")
        # 从配置读取 base_url，不再硬编码
        try:
            from ..config.loader import load_config
            _cfg = load_config()
            _base_url = _cfg.get("site_7tan", {}).get("base_url", "")
        except Exception:
            _base_url = ""
        result = save_site_credential(
            site="7tan_admin",
            username=_os.getenv("TANTAN_USERNAME", "admin"),
            password=env_pwd,
            api_base_url=_base_url,
            notes="从 .env 自动迁移"
        )
        if result["success"]:
            logger.info("✅ 密码已加密迁移到数据库，建议从 .env 中删除 TANTAN_PASSWORD")
        return env_pwd

    return ""



def get_admin_username() -> str:
    """获取 7tan 管理后台用户名"""
    import os as _os
    session = get_session()
    try:
        cred = session.query(SiteCredential).filter(
            SiteCredential.site == "7tan_admin"
        ).first()
        if cred and cred.username:
            return cred.username
    finally:
        session.close()
    return _os.getenv("TANTAN_USERNAME", "admin")


def store_admin_token(jwt_token: str, expires_in: int = 2592000) -> bool:
    """存储管理员 JWT Token（从 API 登录获取后调用）"""
    result = save_site_credential(
        site="7tan_admin",
        jwt_token=jwt_token,
        expires_in=expires_in,
    )
    return result["success"]


def refresh_admin_token_via_api() -> bool:
    """通过 API 刷新管理员 Token"""
    from ..security.auth_client import refresh_token as api_refresh_token
    token = get_admin_token()
    if not token:
        return False
    result = api_refresh_token(token)
    if result.get("success") and result.get("token"):
        return store_admin_token(result["token"])
    return False

def get_admin_token() -> str | None:
    """获取 7tan 管理后台的有效 JWT Token（用于 API 认证）"""
    session = get_session()
    try:
        cred = session.query(SiteCredential).filter(
            SiteCredential.site == "7tan_admin"
        ).first()
        if cred and cred.is_token_valid():
            return cred.jwt_token
        return None
    finally:
        session.close()



# ===== Prompt =====

class Prompt(Base):
    """AI 系统提示词存储"""
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_type = Column(String, nullable=False, unique=True, index=True)
    content = Column(Text, nullable=False)
    reason = Column(String, default="")
    char_count = Column(Integer, default=0)
    line_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "prompt_type": self.prompt_type,
            "content": self.content, "reason": self.reason,
            "char_count": self.char_count, "line_count": self.line_count,
            "created_at": str(self.created_at)[:19] if self.created_at else "",
            "updated_at": str(self.updated_at)[:19] if self.updated_at else "",
        }


def upsert_prompt(prompt_type: str, content: str, reason: str = "") -> dict:
    """插入或更新提示词（自动建表）"""
    # 确保 prompts 表存在
    try:
        Base.metadata.create_all(bind=get_engine())
    except Exception:
        pass
    session = get_session()
    try:
        existing = session.query(Prompt).filter(
            Prompt.prompt_type == prompt_type
        ).first()
        char_count = len(content)
        line_count = content.count('\n') + 1
        if existing:
            existing.content = content
            existing.reason = reason
            existing.char_count = char_count
            existing.line_count = line_count
            existing.updated_at = datetime.now()
            result = {"action": "updated", "id": existing.id}
        else:
            p = Prompt(
                prompt_type=prompt_type, content=content, reason=reason,
                char_count=char_count, line_count=line_count,
            )
            session.add(p)
            session.flush()
            result = {"action": "created", "id": p.id}
        session.commit()
        return result
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_prompt_from_db(prompt_type: str) -> dict | None:
    """从数据库获取提示词"""
    session = get_session()
    try:
        p = session.query(Prompt).filter(
            Prompt.prompt_type == prompt_type
        ).first()
        return p.to_dict() if p else None
    finally:
        session.close()


def get_all_prompts() -> list:
    """获取所有提示词"""
    session = get_session()
    try:
        return [p.to_dict() for p in session.query(Prompt).order_by(Prompt.updated_at.desc()).all()]
    finally:
        session.close()


def migrate_memory_json_to_db():
    """将 data/memory/*.json 迁移到数据库（仅首次）"""
    import json as _json
    session = get_session()
    try:
        if session.query(Memory).count() > 0:
            return  # 已有数据，跳过
    finally:
        session.close()
    
    mem_dir = Path(__file__).parent.parent.parent / "data" / "memory"
    if not mem_dir.exists():
        return
    
    count = 0
    for fpath in mem_dir.glob("*.json"):
        section = fpath.stem
        try:
            data = _json.loads(fpath.read_text(encoding="utf-8"))
            entries = data.get("entries", [])
            for entry in entries:
                key = entry.get("key", "")
                content = entry.get("content", "")
                importance = entry.get("importance", "medium")
                if key and content:
                    try:
                        upsert_memory(section, key, content, importance)
                        count += 1
                    except Exception:
                        pass
        except Exception:
            pass
    logger.info(f"记忆迁移完成: {count} 条 → 数据库")


def migrate_prompts_txt_to_db():
    """将 data/prompts/*.txt 迁移到数据库；txt 不存在时用代码默认模板初始化"""
    prompts_dir = Path(__file__).parent.parent.parent / "data" / "prompts"
    
    session = get_session()
    try:
        if session.query(Prompt).count() > 0:
            return
    finally:
        session.close()
    
    count = 0
    if prompts_dir.exists():
        for fpath in prompts_dir.glob("*.txt"):
            prompt_type = fpath.stem
            try:
                content = fpath.read_text(encoding="utf-8")
                if content.strip():
                    upsert_prompt(prompt_type, content, "从文件迁移")
                    count += 1
            except Exception:
                pass
    
    # 文件不存在/为空 → 用代码内置默认模板兜底（保证新用户有完整提示词）
    if count == 0:
        try:
            from ..agent.prompts import DEFAULT_PROMPTS
            for ptype, content in DEFAULT_PROMPTS.items():
                if content.strip():
                    upsert_prompt(ptype, content, "默认模板初始化")
                    count += 1
        except Exception:
            pass
    logger.info(f"提示词迁移完成: {count} 条 → 数据库")