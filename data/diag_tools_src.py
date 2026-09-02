import sys, os, json, re
sys.path.insert(0, r'D:\7tan\7tanAI')
import src.agent.world_model as wm
src_path = wm.__file__
print('world_model.py =', src_path)
src = open(src_path, encoding='utf-8').read()

# 找 get_all_tools / execute_tool 的来源
for m in re.finditer(r'^.*(get_all_tools|execute_tool|tool_executor|ToolRegistry).*$', src, re.M):
    line = m.group(0).strip()
    if line:
        print('>>>', line[:180])

# 尝试统计全量工具 JSON 大小
try:
    tools = wm._safe_tools_for_llm() if hasattr(wm, '_safe_tools_for_llm') else None
except Exception as e:
    print('safe_tools err:', e)
    tools = None
if tools is None:
    # 找模块级函数
    try:
        tools = [t for t in wm.get_all_tools()]
        print('found get_all_tools module-level, count =', len(tools))
    except Exception as e:
        print('module-level get_all_tools err:', e)
        tools = None
if tools:
    s = json.dumps(tools, ensure_ascii=False)
    print('tools count =', len(tools))
    print('tools JSON chars =', len(s))
    # 粗估 token（英文~4字符/token，中文~1.5字符/token 的混合估算用 3）
    print('approx tokens ~', len(s) // 3)
    # 打印前 2 个工具名与描述长度分布
    lens = [len(json.dumps(t, ensure_ascii=False)) for t in tools]
    print('min tool len', min(lens), 'max', max(lens), 'avg', sum(lens)//len(lens))
