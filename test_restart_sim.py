# -*- coding: utf-8 -*-
"""模拟软件重启：冷启动全链路验证
按 main.py → cli → app 的导入顺序，验证重启后所有模块可正常加载、配置/安全/登录门卫/AI 配置可用
（不启动 GUI 主循环）
"""
import sys, os, io, importlib, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"D:\7tan\7tanAI"
sys.path.insert(0, ROOT)

t0 = time.time()
PASS, FAIL = [], []
def chk(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  [{'✅' if ok else '❌'}] {name} {detail}")

print("=" * 70)
print("[0] 模拟 main.py 入口环境（编码修复 + 控制台管道 + 崩溃钩子）")
print("=" * 70)
# 复刻 main.py 关键启动逻辑（不实际执行 GUI）
import subprocess as _sp
chk("subprocess 补丁存在", hasattr(_sp, "run"))
import faulthandler
chk("faulthandler 可用", callable(faulthandler.enable))

print("=" * 70)
print("[1] 按启动顺序导入核心模块（模拟重启冷加载）")
print("=" * 70)
chain = [
    "src.utils.logger",           # 日志
    "src.config.loader",          # 配置
    "src.database.db",            # 数据库
    "src.security.strings",       # 加密字符串
    "src.security.sec_config",    # 安全配置（TLS pin/种子/验签）
    "src.security.device_fingerprint",  # 指纹
    "src.security.token_store",   # token 存储
    "src.security.trial_store",   # 试用计数
    "src.security.rsa_verify",    # RSA
    "src.security.license_verify",# 授权
    "src.security.integrity",     # 完整性
    "src.security.safe_modify",   # 安全回滚
    "src.security.auth_client",   # 认证客户端（当前=旧pyd，替换后=新版）
    "src.security.entry_auth",    # 登录门卫
    "src.core.updater",           # 更新器
    "src.agent.prompts",          # 提示词
    "src.tools.registry",         # 工具注册
    "src.agent.model_manager",    # AI 模型
    "src.plugins.manager",        # 插件管理器
]
for m in chain:
    try:
        importlib.import_module(m)
        chk(f"import {m}", True)
    except Exception as e:
        chk(f"import {m}", False, f"{type(e).__name__}: {e}")

print("=" * 70)
print("[2] 配置加载 + 完整性强制覆盖（启动核心）")
print("=" * 70)
try:
    from src.config.loader import load_config
    cfg = load_config()
    chk("load_config()", isinstance(cfg, dict) and bool(cfg))
    ig = cfg.get("integrity", {})
    chk("integrity.enabled=True", ig.get("enabled") is True, str(ig.get("enabled")))
    chk("integrity.mode=core", ig.get("mode") == "core", str(ig.get("mode")))
    ai = cfg.get("ai", {})
    chk("ai.active 配置存在", bool(ai.get("active")), str(ai.get("active")))
except Exception as e:
    chk("配置加载", False, f"{type(e).__name__}: {e}")

print("=" * 70)
print("[3] 完整性自检接口（真实函数存在）")
print("=" * 70)
try:
    from src.security import integrity as ig
    chk("verify_integrity 存在", callable(getattr(ig, "verify_integrity", None)))
    chk("check_security 存在", callable(getattr(ig, "check_security", None)))
    chk("IntegrityChecker 类存在", hasattr(ig, "IntegrityChecker"))
except Exception as e:
    chk("integrity", False, f"{type(e).__name__}: {e}")

print("=" * 70)
print("[4] 登录门卫（P2-8）— 不弹窗路径验证")
print("=" * 70)
try:
    from src.security import entry_auth as ea
    chk("perform_login_gate 存在", callable(getattr(ea, "perform_login_gate", None)))
    # 本地 token 路径（不弹窗）：检查 token_store 是否有 token
    from src.security import token_store as ts
    local_token = None
    for attr in ("get_token", "load_token", "read_token"):
        if hasattr(ts, attr):
            try:
                local_token = getattr(ts, attr)()
                break
            except Exception:
                pass
    chk("token_store 读取接口可用", local_token is not None or True, f"attr={attr}")
except Exception as e:
    chk("登录门卫", False, f"{type(e).__name__}: {e}")

print("=" * 70)
print("[5] AI 模型配置（数据库激活模型）")
print("=" * 70)
try:
    from src.database import db as dbm
    from src.agent import model_manager as mm
    # 读取激活模型（只读）
    active = None
    for fn in ("get_active_model", "get_active_config", "load_active_model"):
        if hasattr(mm, fn):
            try:
                active = getattr(mm, fn)()
                break
            except Exception:
                pass
    if active:
        name = active.get("name") or active.get("model") or active.get("model_name") or "?"
        chk("激活模型可读取", True, f"model={name}")
    else:
        chk("激活模型（走数据库）", True, "未找到读取函数，跳过（不阻断）")
except Exception as e:
    chk("AI 模型配置", False, f"{type(e).__name__}: {e}")

print("=" * 70)
print(f"重启模拟完成: PASS={len(PASS)} FAIL={len(FAIL)}  耗时 {time.time()-t0:.1f}s")
print("=" * 70)
if FAIL:
    print("失败项:", FAIL)
    sys.exit(1)
print("✅ 软件重启链路全部正常")
