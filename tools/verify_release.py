#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发布包核验工具（每次发版前必跑）

用法:
    python tools/verify_release.py 1.0.23
    python tools/verify_release.py 1.0.23 --md5     # 只输出 md5/size（写 version.json 用）

检查项:
    1. 两个 zip 内的 deploy.json 凭据字段是否已置空
    2. 全包反向搜索真实 GitHub 令牌 / 服务器密码（杜绝漏网）
    3. 包内 config.yaml 是否残留 .env 中的真实 API Key
    4. 包内 version.py 版本号是否为目标版本
    5. 实体积与 md5（写入 website/updates/version.json 用）

退出码: 0 全过 / 1 有失败
"""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REL = ROOT / "dist" / "release"


def md5_of(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_real_secrets() -> dict:
    """真实凭据：用于在包里反向搜索，证明没有泄露"""
    out = {}
    dj = ROOT / "config" / "deploy.json"
    if dj.exists():
        try:
            d = json.loads(dj.read_text(encoding="utf-8"))
            tok = (d.get("github") or {}).get("token")
            pwd = (d.get("server") or {}).get("password")
            if tok:
                out["github.token"] = tok
            if pwd:
                out["server.password"] = pwd
        except Exception:
            pass
    return out


def load_env_keys() -> dict:
    env = {}
    p = ROOT / ".env"
    if not p.exists():
        return env
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            v = v.strip().strip('"').strip("'")
            if v and not v.startswith("${"):
                env[k.strip()] = v
    return env


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    ver = sys.argv[1]
    only_md5 = "--md5" in sys.argv[2:]

    win = REL / f"7tan-editor-free-v{ver}.zip"
    if not win.exists():
        alt = REL / f"7tan-editor-v{ver}.zip"
        win = alt if alt.exists() else win
    web = REL / f"7tan-web-v{ver}.zip"

    if not win.exists():
        print(f"[FAIL] 找不到 Windows 包: {win}")
        sys.exit(1)

    if only_md5:
        for zp in (win, web):
            if zp.exists():
                print(f"{zp.name}  size={zp.stat().st_size}  md5={md5_of(zp)}")
        sys.exit(0)

    secrets = load_real_secrets()
    env = load_env_keys()
    oks, fails = [], []

    def ok(m):
        oks.append(m)

    def bad(m):
        fails.append(m)

    targets = [(win, ["7tan-editor/_internal/config/deploy.json", "7tan-src/config/deploy.json"])]
    if web.exists():
        targets.append((web, ["config/deploy.json"]))

    for zp, members in targets:
        with zipfile.ZipFile(zp) as zf:
            names = set(zf.namelist())

            # 1. deploy.json 凭据字段
            for m in members:
                if m not in names:
                    bad(f"{zp.name}: 缺文件 {m}")
                    continue
                try:
                    d = json.loads(zf.read(m).decode("utf-8", errors="replace"))
                except Exception as e:
                    bad(f"{zp.name}:{m} JSON 解析失败 {e}")
                    continue
                pwd = (d.get("server") or {}).get("password")
                tok = (d.get("github") or {}).get("token")
                if pwd in ("", None):
                    ok(f"{zp.name}:{m} server.password 已置空")
                else:
                    bad(f"{zp.name}:{m} server.password 仍为明文")
                if tok in ("", None):
                    ok(f"{zp.name}:{m} github.token 已置空")
                else:
                    bad(f"{zp.name}:{m} github.token 仍为明文")

            # 2. 全包反向搜索真实凭据
            text_ext = (".json", ".yaml", ".yml", ".txt", ".md", ".py", ".html", ".js", ".ini", ".cfg")
            for label, val in secrets.items():
                hit = []
                for n in names:
                    if not n.lower().endswith(text_ext):
                        continue
                    try:
                        t = zf.read(n).decode("utf-8", errors="replace")
                    except Exception:
                        continue
                    if val in t:
                        hit.append(n)
                if hit:
                    bad(f"{zp.name} 全包含真实 {label}: {hit[:3]}")
                else:
                    ok(f"{zp.name} 全包无真实 {label}")

            # 3. config.yaml 真实 API Key
            ymls = [n for n in names if n.endswith("config.yaml")]
            leaked = []
            for n in ymls:
                t = zf.read(n).decode("utf-8", errors="replace")
                for k, v in env.items():
                    if len(v) >= 16 and v in t:
                        leaked.append(f"{n}<-{k}")
            if leaked:
                bad(f"{zp.name} config.yaml 泄露真实密钥: {leaked[:5]}")
            else:
                ok(f"{zp.name} config.yaml 无真实 API key（检查 {len(ymls)} 个）")

            # 4. 版本号
            vpath = "7tan-src/src/config/version.py" if "7tan-src/src/config/version.py" in names else "src/config/version.py"
            if vpath in names:
                v = zf.read(vpath).decode("utf-8", errors="replace")
                if f'APP_VERSION = "{ver}"' in v:
                    ok(f"{zp.name} 包内 version.py = {ver}")
                else:
                    bad(f"{zp.name} 包内 version.py 版本不是 {ver}")
            else:
                bad(f"{zp.name} 找不到 version.py")

    print("=" * 66)
    for zp in (win, web):
        if zp.exists():
            print(f"{zp.name}  size={zp.stat().st_size}  md5={md5_of(zp)}")
    print("=" * 66)
    print(f"通过 {len(oks)} 项 / 失败 {len(fails)} 项")
    for m in oks:
        print(f"  [OK]   {m}")
    for m in fails:
        print(f"  [FAIL] {m}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
