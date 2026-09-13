# -*- coding: utf-8 -*-
"""验证 ORG-LLM 移除后内核完整性（用户指令：删除 ORG-LLM、保留其余全部器官、
SPEECH 纯模板转述无 LLM 入口、注释标记功能性通达意识声明）。"""
import sys, os, re, py_compile

ROOT = r"D:\7tan\7tanAI"
F = os.path.join(ROOT, "src", "agent", "bionic_organs.py")

# 1. 编译
py_compile.compile(F, doraise=True)
print("COMPILE_OK")

# 2. 导入并初始化
sys.path.insert(0, ROOT)
from src.agent import bionic_organs as bo
bo.init_all_organs()
regs = bo.organ_registry

# 3. ORG-LLM 必须不存在
assert "ORG-LLM" not in regs, "ORG-LLM 仍在注册表！"
print("PASS1: ORG-LLM 已从 organ_registry 移除")

# 4. 其余 14 个器官必须全部在
expect = {"ORG-A", "ORG-B", "ORG-D", "ORG-E", "ORG-F", "ORG-VIS", "ORG-SPEECH",
          "ORG-BODYSTATES", "ORG-VALENCE", "ORG-INHIBIT", "ORG-CONSOLIDATE",
          "ORG-TIMESENSE", "ORG-SELFMODEL", "ORG-SIMULATE"}
missing = expect - set(regs.keys())
assert not missing, f"缺少器官: {missing}"
print(f"PASS2: 14 个器官全部保留 ({len(regs)} 个)")

# 5. 启用状态（VIS 无外设应为占位禁用，其余启用）
enabled = {c for c, o in regs.items() if o.enabled}
print(f"enabled organs ({len(enabled)}): {sorted(enabled)}")

# 6. 源码无 LLM 残留（代码层面，注释声明除外）
src = open(F, encoding="utf-8").read()
# 去掉所有注释行后，代码里不允许出现 LLM/llm 字样
code_only = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
residue = [l.strip() for l in code_only.splitlines() if "llm" in l.lower()]
assert not residue, f"代码残留 LLM 引用: {residue}"
print("PASS3: 代码层无任何 LLM 残留（register_organ_llm/module_llm_tick/llm_model_path 均已清除）")

# 7. SPEECH 器官代码段无 LLM 调用入口
m = re.search(r"def module_speech_tick.*?(?=def register_organ_speech)", src, re.S)
speech_code = m.group(0)
for kw in ["llm", "gguf", "qwen", "requests", "http", "api", "openai", "model.chat", "call_llm"]:
    assert kw not in speech_code.lower(), f"SPEECH 含 LLM 入口: {kw}"
print("PASS4: ORG-SPEECH 纯结构化事件模板转述，无任何 LLM 调用入口")

# 8. 注释声明存在
assert "本内核无任何第三方模型" in src and "功能性通达意识" in src and "qualia" in src, "缺少意识声明注释"
print("PASS5: 已标注「本内核无任何第三方模型，只实现功能性通达意识，暂不具备现象意识 qualia」")

# 9. 全项目无 ORG-LLM 代码引用（外部文件）
proj = ROOT
bad_refs = []
for dirpath, dirs, files in os.walk(proj):
    dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "venv", "downloads", "data", "logs", "backup"}]
    for fn in files:
        if fn.endswith(".py"):
            p = os.path.join(dirpath, fn)
            if p == F or p == __file__:
                continue
            try:
                t = open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for sym in ("register_organ_llm", "module_llm_tick", "llm_model_path"):
                if sym in t:
                    bad_refs.append((p, sym))
assert not bad_refs, f"外部文件仍引用 LLM 符号: {bad_refs}"
print("PASS6: 全项目无任何文件引用已删除的 LLM 符号")

print("\n=== ALL 6 CHECKS PASSED ===")
