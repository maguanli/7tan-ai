# -*- coding: utf-8 -*-
"""
入库：全部工具(252) + 全部插件(47) → 主模型记忆库 knowledge。
改进：严格验证（检查 save 返回值 + 立即读回断言）。
"""
import json, os, sys, time, importlib.util, shutil

ROOT = r"D:\7tan\7tanAI"
sys.path.insert(0, ROOT)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PLUGIN_DIR = os.path.join(ROOT, "data", "plugins")
MANIFEST = os.path.join(PLUGIN_DIR, "manifest.json")
INSTALLED = os.path.join(PLUGIN_DIR, "installed.json")
MEM_JSON = os.path.join(ROOT, "data", "tan_model_memory.json")

def load_json(p, default=None):
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

# 1) 收集工具
from src.tools.registry import TOOL_REGISTRY

def _load_plugin_module(plugin_id, pkg_dir):
    tools_path = os.path.join(pkg_dir, "tools.py")
    if not os.path.exists(tools_path):
        return False, "无 tools.py"
    try:
        spec = importlib.util.spec_from_file_location(f"plugin_{plugin_id}", tools_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return True, ""
    except Exception as e:
        return False, str(e)[:100]

installed = load_json(INSTALLED, {}).get("plugins", []) or []
manifest = load_json(MANIFEST, []) or []
loaded_plugins, load_errs = [], []
for pid in installed:
    pdir = os.path.join(PLUGIN_DIR, pid)
    if os.path.isdir(pdir):
        ok, err = _load_plugin_module(pid, pdir)
        (loaded_plugins.append(pid) if ok else load_errs.append((pid, err)))

tools = []
for name, t in TOOL_REGISTRY.items():
    params = getattr(t, 'parameters', {}) or {}
    if isinstance(params, dict):
        props = params.get('properties', params) or {}
        req = params.get('required', [])
        req = req if isinstance(req, list) else list(props.keys())
    else:
        props, req = {}, []
    tools.append({"name": name,
                  "description": (getattr(t, 'description', '') or '').replace("\n", " ").strip(),
                  "category": getattr(t, 'category', 'misc') or 'misc',
                  "dangerous": bool(getattr(t, 'dangerous', False)),
                  "properties": props, "required": req or []})
tools.sort(key=lambda x: x["name"])

# 2) 生成条目
def fmt_params(props, req):
    if not props:
        return "无参数"
    req = set(req or [])
    parts = []
    for k, v in props.items():
        if isinstance(v, dict):
            t = v.get("type", "")
            desc = (v.get("description") or "")[:24]
        else:
            t, desc = "", ""
        star = "*" if k in req else ""
        s = f"{k}{star}"
        if t:
            s += f":{t}"
        if desc:
            s += f"({desc})"
        parts.append(s)
    return ", ".join(parts[:8]) + ("…" if len(parts) > 8 else "")

now = time.time()
tool_entries = []
for t in tools:
    lines = [f"工具 {t['name']}",
             f"分类:{t['category']}" + (" 危险:是" if t["dangerous"] else "")]
    if t["description"]:
        lines.append("说明:" + t["description"][:150])
    lines.append("调用:execute_tool(\"%s\",{参数})" % t["name"])
    lines.append("参数:" + fmt_params(t["properties"], t["required"])[:120])
    tool_entries.append({"key": f"tool_usage_{t['name']}",
                         "content": "\n".join(lines)[:300],
                         "source": "tool_catalog", "confidence": 1.0, "ts": now})

plugin_entries = []
for p in manifest:
    pid = p.get("id", "")
    lines = [f"插件 {p.get('name', pid)} v{p.get('version','')}",
             f"id:{pid} 类型:{p.get('type','')} 分类:{p.get('category','')}"]
    desc = (p.get("description") or "").replace("\n", " ").strip()
    if desc:
        lines.append("说明:" + desc[:150])
    tl = p.get("tools", []) or []
    if tl:
        lines.append("提供工具:" + ", ".join(str(x) for x in tl[:12]))
    plugin_entries.append({"key": f"plugin_info_{pid}",
                           "content": "\n".join(lines)[:300],
                           "source": "plugin_catalog", "confidence": 1.0, "ts": now})

# 3) 合并现有记忆 + upsert
from src.database.db import load_tan_model_memory, save_tan_model_memory
mem = load_tan_model_memory() or {}
traces = mem.get("traces") or []
pe = mem.get("pe_history") or []
knowledge = mem.get("knowledge") or []
print("读回现有: traces=%d pe=%d knowledge=%d" % (len(traces), len(pe), len(knowledge)))

existing_keys = {k.get("key") for k in knowledge if isinstance(k, dict)}
def upsert(entries):
    n_new = n_upd = 0
    for e in entries:
        if e["key"] in existing_keys:
            for i, k in enumerate(knowledge):
                if k.get("key") == e["key"]:
                    knowledge[i] = e
                    break
            n_upd += 1
        else:
            knowledge.append(e)
            existing_keys.add(e["key"])
            n_new += 1
    return n_new, n_upd

tn, tu = upsert(tool_entries)
pn, pu = upsert(plugin_entries)
print("工具: 新增%d 更新%d | 插件: 新增%d 更新%d | 总 knowledge=%d" % (tn, tu, pn, pu, len(knowledge)))

# 4) 备份 → 保存 DB → 读回验证
bak = MEM_JSON + ".bak_tool_catalog2"
try:
    if os.path.exists(MEM_JSON):
        shutil.copy2(MEM_JSON, bak)
except Exception as e:
    print("备份失败:", e)

ok_db = save_tan_model_memory(traces, pe, knowledge)
print("save_tan_model_memory 返回:", ok_db)

back = load_tan_model_memory() or {}
bk = back.get("knowledge") or []
bt = len([x for x in bk if x.get("key","").startswith("tool_usage_")])
bp = len([x for x in bk if x.get("key","").startswith("plugin_info_")])
print("读回验证: knowledge=%d (工具=%d 插件=%d)" % (len(bk), bt, bp))

# JSON 镜像
with open(MEM_JSON, "w", encoding='utf-8') as f:
    json.dump({"traces": back.get("traces") or traces,
               "pe_history": back.get("pe_history") or pe,
               "knowledge": bk}, f, ensure_ascii=False, indent=2)
with open(MEM_JSON, encoding='utf-8') as f:
    jd = json.load(f)
jk = jd.get("knowledge") or []
print("JSON 镜像验证: knowledge=%d" % len(jk))

print("RESULT:", "PASS" if (ok_db and len(bk) >= len(tool_entries) + len(plugin_entries)) else "FAIL")
