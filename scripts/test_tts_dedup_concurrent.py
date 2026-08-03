# -*- coding: utf-8 -*-
"""验证: 三通道并发去重 + 失败回滚 + 成功保留"""
import sys, threading, time, hashlib
sys.path.insert(0, '.')

# 1) 语法检查
import ast
for f in ['data/plugins/tts_piper/tools.py', 'src/ui/console_panel.py', 'src/ui/chat_page.py']:
    ast.parse(open(f, encoding='utf-8').read())
    print('语法OK:', f)

# 2) tts_piper 新哈希
h = hashlib.sha256(open('data/plugins/tts_piper/tools.py', 'rb').read()).hexdigest()
print('tts_piper 新哈希:', h)

# 3) 并发去重测试
from data.plugins.tts_piper import tools

play_calls = []
plock = threading.Lock()

def fake_speak(text, play=True, strip_code=True):
    with plock:
        play_calls.append(text)
    time.sleep(0.3)  # 放大并发窗口
    return {"status": "ok", "engine": "mock", "size_kb": 1}

tools.tts_speak = fake_speak

TEXT = "这是一段测试文本，用于验证三通道并发时只朗读一次。"
results = []
def worker():
    results.append(tools.tts_speak_dedup(TEXT))

threads = [threading.Thread(target=worker) for _ in range(3)]
for t in threads: t.start()
for t in threads: t.join()

print('并发3通道 → 实际播放次数:', len(play_calls))
ok1 = len(play_calls) == 1
print('[PASS]' if ok1 else '[FAIL]', '3通道并发只播放1次')

# 4) 失败回滚
tools.tts_speak = lambda text, play=True, strip_code=True: {"status": "error", "message": "模拟失败"}
r = tools.tts_speak_dedup("另一段失败测试文本")
ok2 = tools.tts_is_spoken("另一段失败测试文本") is False
print('[PASS]' if ok2 else '[FAIL]', '失败后登记已回滚可重试, 返回:', r.get('status'))

# 5) 成功保留
tools.tts_speak = lambda text, play=True, strip_code=True: {"status": "ok", "engine": "mock"}
tools.tts_speak_dedup("成功测试文本内容")
ok3 = tools.tts_is_spoken("成功测试文本内容") is True
print('[PASS]' if ok3 else '[FAIL]', '成功后保留登记(5分钟防重)')

# 6) 控制台通道抢占语义验证(先mark后播,失败回滚)
from data.plugins.tts_piper.tools import tts_mark_spoken, tts_clear_spoken
tools.tts_speak = lambda text, play=True, strip_code=True: {"status": "ok", "engine": "mock"}
tts_mark_spoken("控制台抢占文本")
ok4 = tools.tts_is_spoken("控制台抢占文本") is True
print('[PASS]' if ok4 else '[FAIL]', '控制台先登记可抢占(其他通道将跳过)')
tts_clear_spoken("控制台抢占文本")
ok5 = tools.tts_is_spoken("控制台抢占文本") is False
print('[PASS]' if ok5 else '[FAIL]', '失败回滚后登记清除')

print('=== ALL PASS ===' if (ok1 and ok2 and ok3 and ok4 and ok5) else '=== HAS FAILURE ===')
