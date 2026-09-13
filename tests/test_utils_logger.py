"""
src.utils.logger 单元测试
真实 API: setup_logging(level, retention, rotation, log_dir)
src.utils.helpers: slugify_filename / human_readable_size / parse_size_to_bytes / ensure_dir 等
"""
from pathlib import Path

from src.utils.logger import setup_logging
from src.utils.helpers import (
    slugify_filename, human_readable_size, parse_size_to_bytes,
    ensure_dir, disk_usage_gb, file_md5, file_sha256,
)


class TestSetupLogging:
    """日志初始化（使用临时目录，避免污染真实 logs/）"""

    def test_creates_log_dir(self, tmp_path):
        log_dir = str(tmp_path / "mylogs")
        setup_logging(log_dir=log_dir)
        assert Path(log_dir).exists()

    def test_returns_logger(self, tmp_path):
        result = setup_logging(log_dir=str(tmp_path / "L"))
        assert result is not None

    def test_custom_level(self, tmp_path):
        setup_logging(level="DEBUG", log_dir=str(tmp_path / "L2"))
        assert Path(tmp_path / "L2").exists()


class TestSlugify:
    def test_basic(self):
        # python-slugify 默认用连字符分隔
        assert slugify_filename("Hello World") == "hello-world"

    def test_max_length(self):
        out = slugify_filename("a " * 200, max_length=50)
        assert len(out) <= 50

    def test_special_chars_removed(self):
        out = slugify_filename("a/b\\c:d*e?f")
        assert "/" not in out and "\\" not in out and ":" not in out


class TestHumanReadableSize:
    def test_bytes(self):
        assert "B" in human_readable_size(512)

    def test_kb(self):
        assert "KB" in human_readable_size(2048)

    def test_mb(self):
        assert "MB" in human_readable_size(5 * 1024 * 1024)

    def test_gb(self):
        assert "GB" in human_readable_size(3 * 1024 ** 3)

    def test_zero(self):
        assert human_readable_size(0) == "0.0 B"


class TestParseSizeToBytes:
    def test_gb(self):
        assert parse_size_to_bytes("1GB") == 1024 ** 3

    def test_gb_with_space(self):
        assert parse_size_to_bytes("2 GB") == 2 * 1024 ** 3

    def test_bytes_unit(self):
        assert parse_size_to_bytes("100B") == 100

    def test_plain_number(self):
        # 无单位时按字节解析
        assert parse_size_to_bytes("2048") == 2048

    def test_invalid_returns_none(self):
        assert parse_size_to_bytes("not a size") is None

    def test_empty_returns_none(self):
        assert parse_size_to_bytes("") is None

    def test_kb_parses_correctly(self):
        """修复单位降序匹配后，KB/MB/GB/TB 均能正确解析。"""
        assert parse_size_to_bytes("10KB") == 10 * 1024
        assert parse_size_to_bytes("10 KB") == 10 * 1024


class TestEnsureDir:
    def test_creates_nested(self, tmp_path):
        target = str(tmp_path / "a" / "b" / "c")
        p = ensure_dir(target)
        assert Path(target).exists()
        assert isinstance(p, Path)

    def test_existing_dir_ok(self, tmp_path):
        p = ensure_dir(str(tmp_path))
        assert p.exists()


class TestFileHashes:
    def test_md5(self, tmp_path):
        f = tmp_path / "x.bin"
        f.write_bytes(b"hello")
        assert file_md5(f) == "5d41402abc4b2a76b9719d911017c592"

    def test_sha256(self, tmp_path):
        f = tmp_path / "y.bin"
        f.write_bytes(b"hello")
        assert file_sha256(f) == (
            "2cf24dba5fb0a30e26e83b2ac5b9e29e"
            "1b161e5c1fa7425e73043362938b9824"
        )

    def test_empty_file_md5(self, tmp_path):
        f = tmp_path / "empty"
        f.write_bytes(b"")
        assert file_md5(f) == "d41d8cd98f00b204e9800998ecf8427e"


class TestDiskUsage:
    def test_returns_float(self, tmp_path):
        val = disk_usage_gb(str(tmp_path))
        assert isinstance(val, float)
        assert val >= 0
