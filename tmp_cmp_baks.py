# -*- coding: utf-8 -*-
import os, glob, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

fs = ['src/agent/world_model.py'] + sorted(glob.glob('src/agent/world_model.py.bak*'))
marks = [
    '_try_tool_answer',      # 模块G：意图->工具路由(用户要求加的)
    '_call_tool_safe',       # 模块G：安全执行工具
    '_wrap_tool_reply',      # 模块G：结果包装
    '_cloud_llm_answer',     # 云端LLM大脑(用户禁止,已回滚)
    'api_key',               # API密钥相关
    '_looks_like_tool_question',  # 工具型问题优先(模块G增强)
    '_feed_tan_model',       # 工具结果写回记忆
    'deepseek',              # 云端调用
    'requests.post',
    'chat.completions',
]
for f in fs:
    print('==== ' + f + '  (' + str(os.path.getsize(f)) + ' B)')
    try:
        txt = open(f, encoding='utf-8', errors='ignore').read()
    except Exception as e:
        print('  读取失败:', e); continue
    for m in marks:
        n = txt.count(m)
        if n:
            print('  含 %-28s x%d' % (m, n))
    # 找关键方法定义行
    for line in txt.splitlines():
        s = line.strip()
        if s.startswith('def ') and ('answer' in s or 'tool' in s or 'feed' in s or 'llm' in s or 'cloud' in s or 'memory' in s or 'recall' in s):
            print('   def>', s[:90])
print('--- 当前文件是备份中的哪个? 比较大小/标记 ---')
