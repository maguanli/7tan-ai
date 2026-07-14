"""
配置加载与管理模块
支持 YAML 配置文件 + .env 环境变量注入 + 首次启动引导
"""
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv


def _get_root_dir():
    """获取项目根目录 — 兼容开发模式和 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


# 默认配置路径（exe 同级目录/config/ 下）
ROOT_DIR = _get_root_dir()
CONFIG_PATH = ROOT_DIR / "config" / "config.yaml"
ENV_PATH = ROOT_DIR / ".env"

# 加载 .env 文件 — 加载两次确保覆盖
load_dotenv()
_env_path = ROOT_DIR / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=True)


def _resolve_env_vars(value: Any) -> Any:
    """递归解析配置值中的 ${VAR} 环境变量引用"""
    if isinstance(value, str):
        pattern = re.compile(r'\$\{([^}]+)\}')
        matches = pattern.findall(value)
        if len(matches) == 1 and pattern.fullmatch(value.strip()):
            # 整值替换，保留原始类型（数字/布尔等）
            return os.getenv(matches[0], "")
        for var in matches:
            env_val = os.getenv(var, "")
            value = value.replace(f"${{{var}}}", env_val)
        return value
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(v) for v in value]
    return value


def load_config(config_path: Path = None) -> dict:
    """加载完整配置，解析环境变量"""
    if config_path is None:
        config_path = CONFIG_PATH

    if not config_path.exists():
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return _resolve_env_vars(raw) if raw else {}


def create_default_config(config_path: Path = None):
    """首次运行时创建默认配置（仅当文件不存在时）"""
    if config_path is None:
        config_path = CONFIG_PATH

    if config_path.exists():
        return  # 已有配置，不覆盖

    config_path.parent.mkdir(parents=True, exist_ok=True)
    default = {
        "ai": {
            "active": "deepseek",
            "configs": {
                "deepseek": {
                    "provider": "deepseek",
                    "model": "deepseek-v4-pro",
                    "base_url": "https://api.deepseek.com/v1",
                    "api_key": "",
                    "context_window": 128000,
                    "max_tokens": 4096,
                    "temperature": 0.7,
                },
                "ollama": {
                    "provider": "ollama",
                    "model": "qwen2.5:7b",
                    "base_url": "http://localhost:11434/v1",
                    "api_key": "ollama",
                    "context_window": 128000,
                    "max_tokens": 4096,
                    "temperature": 0.7,
                },
            },
        },
    }
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(default, f, allow_unicode=True, default_flow_style=False, indent=2)
    from loguru import logger
    logger.info(f"📝 已创建默认配置文件: {config_path}")


def save_config(config: dict, config_path: Path = None):
    """保存配置到 YAML 文件"""
    if config_path is None:
        config_path = CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, indent=2)


def _env_var_ref(key: str) -> str:
    """生成环境变量引用字符串"""
    return f"${{{key}}}"


def _generate_default_config(answers: dict) -> dict:
    """根据引导问答生成默认配置"""
    provider = answers.get("provider", "deepseek")
    model = answers.get("model", "deepseek-chat")
    base_url = answers.get("base_url", "https://api.deepseek.com/v1")
    return {
        "ai": {
            "active": provider,
            "configs": {
                provider: {
                    "provider": provider,
                    "model": model,
                    "base_url": base_url,
                    "api_key": _env_var_ref("DEEPSEEK_API_KEY"),
                    "context_window": 128000,
                    "max_tokens": 4096,
                    "temperature": 0.7,
                }
            },
        },
        "site_7tan": {
            "base_url": answers.get("tantan_url", "https://img.7tan.cn"),
            "login_url": answers.get("tantan_url", "https://img.7tan.cn") + "/login.php",
            "username": _env_var_ref("TANTAN_USERNAME"),
            "password": _env_var_ref("TANTAN_PASSWORD"),
            "publish_delay_min": 30,
            "publish_delay_max": 120,
        },
        "oss": {
            "provider": answers.get("oss_provider", "aliyun"),
            "access_key": _env_var_ref("OSS_ACCESS_KEY"),
            "secret_key": _env_var_ref("OSS_SECRET_KEY"),
            "bucket": _env_var_ref("OSS_BUCKET"),
            "region": "oss-cn-shanghai",
            "domain": _env_var_ref("OSS_DOMAIN"),
        },
        "storage": {
            "delete_after_upload": True,
            "image_retention_days": 30,
            "disk_cleanup_threshold_gb": 10,
        },
        "sources": {
            "sites": [],
            "crawl_interval": 360,
            "max_resources_per_run": 5,
        },
        "web": {
            "port": 9800,
            "auto_open_browser": True,
            "theme": "dark",
            "language": "zh-CN",
        },
        "scheduler": {
            "cron_jobs": [
                {"name": "每日早间更新", "cron": "0 8 * * *"},
                {"name": "每日午间更新", "cron": "0 12 * * *"},
                {"name": "每日晚间更新", "cron": "0 18 * * *"},
            ],
            "auto_publish": False,
            "daemon": False,
        },
        "network": {
            "http_proxy": "",
            "https_proxy": "",
            "connect_timeout": 30,
            "download_timeout": 7200,
            "browser_type": "chromium",
            "browser_path": "",
            "headless": False,
            "spider_download": False,
            "spider_list": "all",
        },
        "security": {
            "self_modify_confirm": True,
            "allow_modify_tools": True,
            "allow_modify_core": False,
            "sensitive_words_filter": True,
        },
        "integrity": {
            "enabled": True,
            "mode": "core",
            "auto_repair": False,
            "developer_mode": False,
            "confirm_phrase": "我已知晓风险并信任此次修改",
            "show_status": True,
            "log_all_checks": True,
            "tamper_alert_email": "",
        },
        "logging": {
            "level": "INFO",
            "retention": "30 days",
            "rotation": "100 MB",
        },
    }


def ensure_initialized(interactive: bool = True):
    """
    确保项目已初始化：
    1. 如果 config.yaml 不存在，从模板创建默认配置
    2. 如果 .env 不存在，从 .env.example 复制
    3. 创建必要的目录结构
    兼容开发模式和 PyInstaller 打包模式

    Args:
        interactive: 是否交互式引导（False 时静默生成默认配置）
    """
    import shutil
    from loguru import logger

    # 配置文件
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        # 尝试从模板复制（PyInstaller 打包后模板在 sys._MEIPASS）
        bundled_template = None
        if getattr(sys, 'frozen', False):
            bundled_template = Path(sys._MEIPASS) / "config" / "config.yaml"
        if bundled_template and bundled_template.exists():
            shutil.copy(bundled_template, CONFIG_PATH)
            logger.info(f"已从模板创建配置文件: {CONFIG_PATH}")
        else:
            logger.warning(f"配置文件不存在: {CONFIG_PATH}，将使用默认配置")
            save_config(_generate_default_config({}), CONFIG_PATH)

    # .env 文件
    env_file = ROOT_DIR / ".env"
    env_example = ROOT_DIR / ".env.example"
    if not env_file.exists():
        # 尝试从 bundled template 复制
        if getattr(sys, 'frozen', False):
            bundled_env = Path(sys._MEIPASS) / ".env.example"
            if bundled_env.exists():
                shutil.copy(bundled_env, env_example)
        if env_example.exists():
            shutil.copy(env_example, env_file)
            logger.info(f"已从模板创建 .env 文件，请编辑填写 API Key")
        else:
            env_file.touch()
            logger.warning("已创建空 .env 文件，请填写 API Key")

    # 必要目录
    for dirname in ["data", "logs", "downloads"]:
        (ROOT_DIR / dirname).mkdir(parents=True, exist_ok=True)

    # 敏感词文件
    sensitive_path = ROOT_DIR / "config" / "sensitive_words.txt"
    if not sensitive_path.exists():
        if getattr(sys, 'frozen', False):
            bundled_sensitive = Path(sys._MEIPASS) / "config" / "sensitive_words.txt"
            if bundled_sensitive.exists():
                shutil.copy(bundled_sensitive, sensitive_path)


def cli_first_time_setup() -> dict:
    """CLI 交互式首次启动引导，返回答案字典"""
    print("\n" + "=" * 44)
    print("  🤖 7坛AI小编 - 首次启动引导")
    print("=" * 44)
    print("\n检测到配置文件不存在，请完成以下设置:\n")

    answers = {}

    # [1/5] AI 模型选择
    print("[1/5] 选择 AI 模型:")
    providers = {
        "1": ("deepseek", "deepseek-chat", "https://api.deepseek.com/v1"),
        "2": ("openai", "gpt-4o", "https://api.openai.com/v1"),
        "3": ("ollama", "qwen2.5-7b", "http://localhost:11434/v1"),
        "4": ("siliconflow", "deepseek-ai/DeepSeek-V3", "https://api.siliconflow.cn/v1"),
        "5": ("doubao", "doubao-lite-128k", "https://ark.cn-beijing.volces.com/api/v3"),
    }
    for k, (name, model, url) in providers.items():
        print(f"  {k}. {name} ({model})")
    choice = input("  请选择 (1-5) [1]: ").strip() or "1"
    provider, model, base_url = providers.get(choice, providers["1"])
    answers["provider"] = provider
    answers["model"] = model
    answers["base_url"] = base_url

    # [2/5] API Key
    print(f"\n[2/5] 请填写 {provider.upper()} API Key (可在 .env 文件中修改):")
    api_key = input("  API Key: ").strip()
    answers["api_key"] = api_key

    # [3/5] 7坛后台
    print("\n[3/5] 7坛管理后台信息:")
    tantan_url = input("  网址 [https://img.7tan.cn]: ").strip()
    answers["tantan_url"] = tantan_url or "https://img.7tan.cn"
    tantan_user = input("  用户名: ").strip()
    tantan_pass = input("  密码: ").strip()
    answers["tantan_user"] = tantan_user
    answers["tantan_pass"] = tantan_pass

    # [4/5] 云存储
    print("\n[4/5] 云存储配置 (安装包上传):")
    oss_opts = {"1": "aliyun", "2": "tencent", "3": "qiniu", "4": "none"}
    print("  1. 阿里云 OSS")
    print("  2. 腾讯云 COS")
    print("  3. 七牛 Kodo")
    print("  4. 跳过（无法发布安装包）")
    oss_choice = input("  请选择 (1-4) [1]: ").strip() or "1"
    answers["oss_provider"] = oss_opts.get(oss_choice, "aliyun")

    if oss_choice != "4":
        answers["oss_key"] = input("  AccessKey ID: ").strip()
        answers["oss_secret"] = input("  AccessKey Secret: ").strip()
        answers["oss_bucket"] = input("  Bucket名称: ").strip()
        answers["oss_region"] = input("  地域 [oss-cn-shanghai]: ").strip() or "oss-cn-shanghai"
        answers["oss_domain"] = input("  自定义域名 (可选): ").strip()

    # [5/5] 源站
    print("\n[5/5] 添加源站 (一行一个网址，留空结束):")
    sources = []
    i = 1
    while True:
        url = input(f"  源站{i}: ").strip()
        if not url:
            break
        sources.append({"name": url.split("//")[-1].split("/")[0], "url": url, "enabled": True})
        i += 1
    answers["sources"] = sources

    print("\n" + "=" * 44)
    print("✅ 配置完成！已保存到 config.yaml")
    print("   敏感信息（API Key / 密码）已写入 .env 文件")
    print("=" * 44 + "\n")

    return answers


def ensure_initialized(interactive: bool = True) -> dict:
    """
    确保系统已初始化。
    如果配置文件不存在：
      - interactive=True: 运行 CLI 交互式首次设置引导
      - interactive=False: 静默生成默认配置（GUI 模式）
    返回配置字典。
    """
    if not CONFIG_PATH.exists():
        if interactive:
            print("⚠️  首次运行，正在启动配置引导...")
            answers = cli_first_time_setup()
        else:
            # GUI 模式：自动生成默认配置，用户可在设置页面修改
            answers = {}
        config = _generate_default_config(answers)
        save_config(config)

        # 写 .env
        env_lines = []
        if answers.get("api_key"):
            env_lines.append(f"DEEPSEEK_API_KEY={answers['api_key']}")
        if answers.get("tantan_user"):
            env_lines.append(f"TANTAN_USERNAME={answers['tantan_user']}")
        if answers.get("tantan_pass"):
            env_lines.append(f"TANTAN_PASSWORD={answers['tantan_pass']}")
        if answers.get("oss_key"):
            env_lines.append(f"OSS_ACCESS_KEY={answers['oss_key']}")
        if answers.get("oss_secret"):
            env_lines.append(f"OSS_SECRET_KEY={answers['oss_secret']}")
        if answers.get("oss_bucket"):
            env_lines.append(f"OSS_BUCKET={answers['oss_bucket']}")
        if answers.get("oss_region"):
            env_lines.append(f"OSS_REGION={answers['oss_region']}")
        if answers.get("oss_domain"):
            env_lines.append(f"OSS_DOMAIN={answers['oss_domain']}")

        if env_lines and not ENV_PATH.exists():
            with open(ENV_PATH, "w", encoding="utf-8") as f:
                f.write("# 7坛AI小编 环境变量\n")
                f.write("\n".join(env_lines) + "\n")

        # 重新加载环境变量
        load_dotenv()
        config = load_config()

        # 检查云存储
        if config.get("oss", {}).get("provider") == "none":
            print("⚠️  未配置云存储！游戏/软件安装包将无法上传，发布时无下载链接。")
            print("   请编辑 config.yaml 添加 oss 段配置，或进入对话模式输入「配置云存储」。")

    return load_config()
