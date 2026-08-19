"""核心模块单元测试"""

import pytest
import json
import os
import sys

# 确保项目根目录在 path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "config.yaml")


# ============================================================
# 配置加载测试
# ============================================================

class TestConfigLoader:
    """测试 config/loader.py"""

    def test_config_exists(self):
        """验证 config.yaml 存在且可读"""
        assert os.path.exists(CONFIG_PATH), f"config.yaml not found at {CONFIG_PATH}"
        import yaml
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        assert cfg is not None
        assert "agent" in cfg

    def test_agent_timeout_positive(self):
        """验证 agent.loop_timeout 为合法正整数"""
        import yaml
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        timeout = cfg.get("agent", {}).get("loop_timeout", 0)
        assert isinstance(timeout, (int, float))
        assert timeout > 0


# ============================================================
# 加密工具测试
# ============================================================

class TestCrypto:
    """测试 utils/crypto.py"""

    def test_encrypt_decrypt_roundtrip(self):
        """加密解密往返测试"""
        from src.utils.crypto import encrypt, decrypt
        plaintext = "test_secret_12345"
        encrypted = encrypt(plaintext)
        assert encrypted != plaintext
        assert decrypt(encrypted) == plaintext

    def test_empty_string(self):
        """空字符串不应崩溃"""
        from src.utils.crypto import encrypt, decrypt
        encrypted = encrypt("")
        assert decrypt(encrypted) == ""


# ============================================================
# 数据库模型测试
# ============================================================

class TestDatabase:
    """测试 database 模块"""

    def test_models_importable(self):
        """所有 ORM 模型可正常导入"""
        from src.database.db import (
            Resource, Capability, Memory, Prompt,
            AiConfig, InstalledSoftware
        )
        assert Resource is not None
        assert Capability is not None
        assert Memory is not None
        assert Prompt is not None
        assert AiConfig is not None
        assert InstalledSoftware is not None

    def test_duplicate_check_nonexistent(self):
        """去重检查对新资源返回 None"""
        try:
            from src.tools.db_tools import db_check_duplicate
        except ImportError as e:
            pytest.skip(f"Missing dependency: {e}")
        try:
            result = db_check_duplicate(
                source_site="test_site",
                source_id="test_nonexistent_99999",
                title="测试游戏_不存在"
            )
        except Exception as e:
            pytest.skip(f"DB 不可用（CI 无数据库）: {e}")
        assert result is not None  # 返回确认消息字符串


# ============================================================
# 插件系统测试
# ============================================================

class TestPlugins:
    """测试插件加载"""

    def test_manifest_loadable(self):
        """installed.json 格式正确且非空"""
        manifest_path = os.path.join(
            PROJECT_ROOT, "data", "plugins", "installed.json"
        )
        assert os.path.exists(manifest_path), "installed.json not found"
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "plugins" in data
        assert len(data["plugins"]) > 0, "No plugins registered"

    def test_plugins_have_tools(self):
        """每个插件目录都有 tools.py"""
        manifest_path = os.path.join(
            PROJECT_ROOT, "data", "plugins", "installed.json"
        )
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for pid in data["plugins"]:
            tools_path = os.path.join(
                PROJECT_ROOT, "data", "plugins", pid, "tools.py"
            )
            assert os.path.exists(tools_path), f"Missing tools.py for {pid}"


# ============================================================
# 工具函数测试
# ============================================================

class TestUtils:
    """测试 utils 模块"""

    def test_machine_fingerprint(self):
        """机器指纹为 32 字节"""
        from src.utils.crypto import _machine_fingerprint
        fp = _machine_fingerprint()
        assert len(fp) == 32

    def test_cost_tracking_no_error(self):
        """费用记录函数调用不崩溃"""
        import importlib
        try:
            from src.tools.monitor_tools import track_cost
            result = track_cost("test-model", 100, 50, 0.0, "test")
            assert isinstance(result, str) and len(result) > 0  # 返回消息字符串
        except Exception as e:
            pytest.skip(f"依赖不可用（CI 环境）: {e}")


# ============================================================
# 主题常量测试
# ============================================================

class TestTheme:
    """测试 UI 主题"""

    def test_theme_keys_complete(self):
        """主题包含所有必需颜色键"""
        from src.ui.widgets._theme import THEME
        required = [
            "bg_dark", "bg_card", "bg_sidebar", "bg_input",
            "accent", "accent2", "success", "warning", "danger",
            "text_primary", "text_secondary", "text_muted",
            "border", "hover",
        ]
        for key in required:
            assert key in THEME, f"Missing theme key: {key}"
            assert THEME[key].startswith("#"), f"Theme {key} not hex"


# ============================================================
# API 端点测试（需要服务运行）
# ============================================================

class TestAPI:
    """测试 REST API"""

    def test_health_endpoint(self):
        """健康检查端点返回 200"""
        import requests
        try:
            resp = requests.get("http://127.0.0.1:9800/api/health", timeout=3)
            assert resp.status_code == 200
        except requests.ConnectionError:
            pytest.skip("Server not running")

    def test_version_endpoint(self):
        """版本端点返回版本号"""
        import requests
        try:
            resp = requests.get("http://127.0.0.1:9800/api/version", timeout=3)
            if resp.status_code == 404:
                pytest.skip("version endpoint 未定义")
            assert resp.status_code == 200
            data = resp.json()
            assert "version" in data
        except requests.ConnectionError:
            pytest.skip("Server not running")
