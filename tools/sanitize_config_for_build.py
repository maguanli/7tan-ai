#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建前敏感配置清洗工具（防发布包泄露 API Key）

用法:
    python tools/sanitize_config_for_build.py --apply    构建前清洗（含明文则备份+脱敏）
    python tools/sanitize_config_for_build.py --restore  构建后恢复本地真实配置
    python tools/sanitize_config_for_build.py --check    检查 config 目录是否含明文密钥（CI 用）

设计:
    - 真实密钥只存 .env（发布包黑名单已排除 .env，见 package_release.py EXCLUDE_FILE_PATTERNS）
    - config/*.yaml 一律使用 ${VAR} 占位符（src/config/loader.py 启动时从环境变量展开）
    - --apply  扫描 config/*.yaml，把残留的真实密钥值替换为 ${VAR} 占位符；
               仅当检测到明文时才更新备份，保证备份永远是最新真实版（幂等安全）
    - --restore 从 tools/_secrets_backup/ 恢复真实配置（本地开发始终可用）
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
BACKUP_DIR = ROOT / "tools" / "_secrets_backup"
ENV_FILE = ROOT / ".env"

# 参与脱敏的敏感变量（值非空且不是 ${} 占位符时才会进入反向映射）
SENSITIVE_KEYS = {
    "SENSETIME_API_KEY", "DEEPSEEK_API_KEY", "VISION_API_KEY",
    "MOONSHOT_API_KEY", "OSS_ACCESS_KEY", "OSS_SECRET_KEY",
    "TANTAN_PASSWORD", "TANTAN_USERNAME", "TANTAN_BASE_URL",
    "TANTAN_LOGIN_URL", "TANTAN_PING_URL", "TANTAN_PING_FALLBACK",
    "MYSQL_PASSWORD", "DB_PASSWORD",
}


def parse_env(path: Path) -> dict:
    """手写解析 .env：返回 {KEY: VALUE}（忽略注释/空行，去掉引号）"""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and v:
            env[k] = v
    return env


def build_reverse_map(env: dict) -> dict:
    """真实值 → ${VAR} 反向映射，只收录敏感变量且值非占位符"""
    mapping = {}
    for k, v in env.items():
        if k in SENSITIVE_KEYS and v and not v.startswith("${"):
            mapping[v] = f"${{{k}}}"
    return mapping


def yaml_files():
    return [p for p in CONFIG_DIR.glob("*.y*ml") if p.is_file()]


def json_files():
    return [p for p in CONFIG_DIR.glob("*.json") if p.is_file()]


# deploy.json 中需要脱敏的凭据字段路径（点号分隔）
JSON_SECRET_PATHS = [("server", "password"), ("github", "token")]


def _walk_secret_node(data: dict, path: tuple):
    """按路径取父 dict（JSON_SECRET_PATHS 的长度固定为 2）"""
    node = data
    for key in path[:-1]:
        node = node.get(key) if isinstance(node, dict) else None
        if not isinstance(node, dict):
            return None
    return node if isinstance(node, dict) else None


def sanitize_json() -> int:
    """清洗 config/*.json：把已知凭据字段置空；返回置空处数"""
    total = 0
    for p in json_files():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] {p.name}: JSON 解析失败，未脱敏（{e}）")
            continue
        changed = 0
        for path in JSON_SECRET_PATHS:
            node = _walk_secret_node(data, path)
            if node and node.get(path[-1]):
                node[path[-1]] = ""
                changed += 1
        if changed:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, BACKUP_DIR / (p.name + ".bak"))
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[清洗] {p.name}: 置空 {changed} 个凭据字段")
            total += changed
        else:
            print(f"[OK]   {p.name}: 无明文凭据")
    return total


def sanitize(env: dict) -> int:
    """清洗 config/*.yaml + config/*.json：含明文则先备份再替换；返回替换处数"""
    mapping = build_reverse_map(env)
    total = 0
    if not mapping:
        print("[SKIP] .env 中没有可脱敏的真实密钥")
        return total + sanitize_json()
    for p in yaml_files():
        text = p.read_text(encoding="utf-8")
        new, hits = text, 0
        for real, placeholder in mapping.items():
            if real in new:
                hits += new.count(real)
                new = new.replace(real, placeholder)
        if hits:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, BACKUP_DIR / (p.name + ".bak"))  # 仅含明文时更新备份
            p.write_text(new, encoding="utf-8")
            print(f"[清洗] {p.name}: 替换 {hits} 处明文密钥")
            total += hits
        else:
            print(f"[OK]   {p.name}: 无明文密钥")
    total += sanitize_json()
    return total


def restore() -> int:
    """从备份恢复 config 真实配置；返回恢复文件数"""
    if not BACKUP_DIR.exists():
        print("[SKIP] 无备份目录，跳过恢复")
        return 0
    count = 0
    for bak in BACKUP_DIR.glob("*.bak"):
        dst = CONFIG_DIR / (bak.name[:-4])  # 去掉 .bak 后缀
        if dst.exists() or True:
            shutil.copy2(bak, dst)
            count += 1
    return count


def check(env: dict) -> list:
    """返回 [(文件名, 残留位置)] 明文残留列表"""
    mapping = build_reverse_map(env)
    bad = []
    for p in yaml_files():
        text = p.read_text(encoding="utf-8")
        for real in mapping:
            if real in text:
                bad.append((p.name, real[:12] + "..."))
    for p in json_files():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for path in JSON_SECRET_PATHS:
            node = _walk_secret_node(data, path)
            if node and node.get(path[-1]):
                bad.append((p.name, ".".join(path)))
    return bad


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("--apply", "--restore", "--check"):
        print(__doc__)
        sys.exit(2)
    env = parse_env(ENV_FILE)
    if args[0] == "--apply":
        print("== sanitize --apply ==")
        t = sanitize(env)
        print(f"[完成] 共处理 {t} 处明文密钥；config/*.yaml 为占位符版，config/*.json 凭据已置空（发布安全）")
        sys.exit(0)
    elif args[0] == "--restore":
        print("== sanitize --restore ==")
        n = restore()
        print(f"[完成] 已恢复 {n} 个文件（本地真实配置还原）")
        sys.exit(0)
    elif args[0] == "--check":
        bad = check(env)
        if bad:
            print(f"[危险] {len(bad)} 个文件仍含明文密钥:")
            for name, sample in bad:
                print(f"  - {name}: {sample}")
            sys.exit(1)
        print("[OK] config 目录无明文密钥")
        sys.exit(0)


if __name__ == "__main__":
    main()
