"""
配置加载与管理模块
支持 YAML 配置文件 + 环境变量
"""
import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel


# 加载 .env 文件
load_dotenv()


class DeepSeekConfig(BaseModel):
    api_key: str
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-v4-flash"
    max_tokens: int = 4096
    temperature: float = 0.25


class Site7tanConfig(BaseModel):
    base_url: str = ""
    login_url: str = ""
    username: str = ""
    password: str = ""
    publish_delay_min: int = 30
    publish_delay_max: int = 120


class SourceSiteConfig(BaseModel):
    name: str
    url: str
    scraper_type: str = "cms"
    list_selector: str = ""
    title_selector: str = ""
    desc_selector: str = ""
    logo_selector: str = ""
    screenshot_selector: str = ""
    download_selector: str = ""
    category_selector: str = ""
    enabled: bool = True


class OSSConfig(BaseModel):
    provider: str = "aliyun"
    access_key: str = ""
    secret_key: str = ""
    bucket: str = ""
    region: str = ""
    domain: str = ""


class CronJobConfig(BaseModel):
    name: str
    cron: str


class SchedulerConfig(BaseModel):
    cron_jobs: list[CronJobConfig] = []
    auto_publish: bool = False
    max_games_per_run: int = 5


class DownloaderConfig(BaseModel):
    max_concurrent: int = 3
    timeout: int = 3600
    retry: int = 3
    download_dir: str = "./downloads"
    image_compress: bool = True
    image_max_width: int = 1920
    image_quality: int = 85


class ReviewerConfig(BaseModel):
    sensitive_words_file: str = "./config/sensitive_words.txt"
    min_intro_length: int = 100
    min_screenshots: int = 1
    auto_approve: bool = True


class LoggingConfig(BaseModel):
    level: str = "INFO"
    retention: str = "30 days"
    rotation: str = "100 MB"


class AppConfig(BaseModel):
    deepseek: DeepSeekConfig
    site_7tan: Site7tanConfig
    source_sites: list[SourceSiteConfig] = []
    oss: OSSConfig
    scheduler: SchedulerConfig
    downloader: DownloaderConfig
    reviewer: ReviewerConfig
    logging: LoggingConfig


def _resolve_env_vars(value: Any) -> Any:
    """递归解析配置中的 ${ENV_VAR} 引用"""
    if isinstance(value, str):
        pattern = re.compile(r'\$\{(\w+)\}')
        matches = pattern.findall(value)
        for var in matches:
            env_val = os.environ.get(var, "")
            if pattern.fullmatch(value):
                return env_val
            value = value.replace(f"${{{var}}}", env_val)
        return value
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(v) for v in value]
    return value


# 全局配置单例
_config: Optional[AppConfig] = None
_config_dir: Path = Path(__file__).parent


def load_config(config_path: str = None) -> AppConfig:
    """加载配置"""
    global _config

    if config_path is None:
        config_path = _config_dir / "config.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    raw = _resolve_env_vars(raw)

    _config = AppConfig(**raw)
    return _config


def get_config() -> AppConfig:
    """获取当前配置（如果未加载则自动加载）"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(config_path: str = None) -> AppConfig:
    """重新加载配置"""
    return load_config(config_path)
