#!/usr/bin/env python3
"""生成 data/plugins/hashes.json — 内置插件 SHA-256 白名单 + HMAC 签名

用法: python tools/gen_plugin_hashes.py
依赖: src/security/plugin_guard（.py 或 .pyd）必须已存在

注意: 每次修改任何插件 tools.py 后必须重新运行本脚本，否则该插件将被拒绝加载。
"""
import hashlib
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from src.security.plugin_guard import sign_hashes
except ImportError as e:
    print(f"❌ 无法导入 src.security.plugin_guard: {e}")
    print("   请先运行: python tools/gen_plugin_guard.py")
    sys.exit(1)

PLUGIN_DIR = ROOT / "data" / "plugins"
OUT = PLUGIN_DIR / "hashes.json"


def main():
    plugins = {}
    count = 0
    if not PLUGIN_DIR.exists():
        print(f"❌ 插件目录不存在: {PLUGIN_DIR}")
        sys.exit(1)

    for pkg in sorted(PLUGIN_DIR.iterdir()):
        if not pkg.is_dir():
            continue
        tools = pkg / "tools.py"
        if not tools.exists():
            continue
        digest = hashlib.sha256(tools.read_bytes()).hexdigest()
        plugins[pkg.name] = digest
        count += 1

    # 规范化主体（sort_keys + 紧凑分隔符，与 plugin_guard.load_whitelist 一致）
    body = json.dumps(plugins, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sig = sign_hashes(body)

    data = {
        "version": 1,
        "plugins": plugins,
        "sig": sig,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 已生成: {OUT}")
    print(f"   插件数: {count}")
    print(f"   签名:   {sig[:24]}...")


if __name__ == "__main__":
    main()
