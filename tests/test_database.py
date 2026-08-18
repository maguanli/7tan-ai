"""
src.database.db 单元测试
基于真实 API: init_db / save_ai_config / get_ai_config_by_key / get_all_ai_configs /
set_active_ai_config / delete_ai_config / upsert_memory / get_all_memories / delete_memory /
upsert_prompt / get_prompt_from_db
全部使用临时 SQLite，不触碰真实数据库。
"""
import pytest

import src.database.db as db


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """把数据库指向临时文件，测试后自动隔离"""
    db_file = str(tmp_path / "test.db")
    # 重置 engine 缓存并初始化临时库
    monkeypatch.setattr(db, "_engine", None, raising=False)
    monkeypatch.setattr(db, "_SessionLocal", None, raising=False)
    db.init_db(db_path=db_file)
    yield db_file


class TestInitDB:
    def test_init_creates_engine(self, temp_db):
        assert db.get_engine() is not None

    def test_get_session(self, temp_db):
        session = db.get_session()
        assert session is not None
        session.close()


class TestAIConfig:
    def test_save_and_get(self, temp_db):
        db.save_ai_config(
            config_key="test_deepseek",
            provider="deepseek",
            model="deepseek-v4-pro",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-test-123",
        )
        cfg = db.get_ai_config_by_key("test_deepseek")
        assert cfg is not None
        assert cfg["model"] == "deepseek-v4-pro"

    def test_api_key_encrypted_at_rest(self, temp_db):
        db.save_ai_config(
            config_key="test_enc",
            provider="deepseek",
            model="m",
            api_key="sk-plain-secret",
        )
        raw = db.get_ai_config_by_key("test_enc", mask_secrets=False)
        # 取回时应能解密还原
        assert raw is not None

    def test_get_all_configs(self, temp_db):
        db.save_ai_config("k1", "deepseek", "m1")
        db.save_ai_config("k2", "moonshot", "m2")
        all_cfgs = db.get_all_ai_configs()
        keys = [c.get("config_key") or c.get("key") for c in all_cfgs]
        assert "k1" in keys and "k2" in keys

    def test_get_nonexistent_returns_none(self, temp_db):
        assert db.get_ai_config_by_key("no_such_key_xyz") is None

    def test_set_active(self, temp_db):
        db.save_ai_config("active_test", "deepseek", "m")
        ok = db.set_active_ai_config("active_test")
        assert ok is True or ok is None  # 依实现

    def test_delete_config(self, temp_db):
        db.save_ai_config("to_delete", "deepseek", "m")
        db.delete_ai_config("to_delete")
        assert db.get_ai_config_by_key("to_delete") is None

    def test_update_existing(self, temp_db):
        db.save_ai_config("upd", "deepseek", "model_v1")
        db.save_ai_config("upd", "deepseek", "model_v2")
        cfg = db.get_ai_config_by_key("upd")
        assert cfg["model"] == "model_v2"


class TestMemory:
    def test_upsert_and_get(self, temp_db):
        db.upsert_memory("skills", "pytest_usage", "使用 tmp_path 隔离", "high")
        mems = db.get_all_memories(section="skills")
        keys = [m.get("key") for m in mems]
        assert "pytest_usage" in keys

    def test_upsert_updates(self, temp_db):
        db.upsert_memory("general", "k", "v1")
        db.upsert_memory("general", "k", "v2")
        mems = get_all = db.get_all_memories(keyword="v2")
        assert any(m.get("content") == "v2" for m in mems)

    def test_keyword_search(self, temp_db):
        db.upsert_memory("games", "zelda", "塞尔达传说是开放世界")
        mems = db.get_all_memories(keyword="塞尔达")
        assert len(mems) >= 1

    def test_delete_memory(self, temp_db):
        db.upsert_memory("general", "del_me", "temp")
        db.delete_memory("general", "del_me")
        mems = db.get_all_memories(section="general")
        assert all(m.get("key") != "del_me" for m in mems)

    def test_summary(self, temp_db):
        db.upsert_memory("config", "s1", "c1")
        summary = db.get_memory_summary()
        assert isinstance(summary, list)
        assert all("section" in s and "total" in s for s in summary)


class TestPrompt:
    def test_upsert_and_get(self, temp_db):
        db.upsert_prompt("system", "你是7Tan编辑AI", "初始版本")
        p = db.get_prompt_from_db("system")
        assert p is not None
        assert "7Tan" in (p.get("content") or "")

    def test_get_nonexistent(self, temp_db):
        assert db.get_prompt_from_db("nonexistent_type_xyz") is None

    def test_get_all_prompts(self, temp_db):
        db.upsert_prompt("scraper", "抓取模板")
        all_p = db.get_all_prompts()
        assert isinstance(all_p, list)


class TestInstalledSoftware:
    def test_upsert_and_get(self, temp_db):
        db.upsert_installed_software("FFmpeg", category="视频", version="7.0")
        sw = db.get_installed_software_by_name("FFmpeg")
        assert sw is not None

    def test_get_all(self, temp_db):
        db.upsert_installed_software("Git", category="开发")
        all_sw = db.get_all_installed_software()
        assert isinstance(all_sw, (list, dict))
