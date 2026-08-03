# -*- coding: utf-8 -*-
"""验证男声(Edge) → 回退 Piper 链路 + 播放链路"""
import sys, os
sys.path.insert(0, r'D:\7tan\7tanAI')
os.chdir(r'D:\7tan\7tanAI')

from data.plugins.tts_piper import tools

print('=== 1. 切男声后 tts_speak(play=False) ===')
print('set_gender:', tools.tts_set_gender('male'))
r = tools.tts_speak('测试男声引擎回退链路', play=False)
print('result:', {k: str(v)[:70] for k, v in r.items() if k != 'wav_path'})
print('wav exists:', os.path.exists(r.get('wav_path', '')) if r.get('wav_path') else None)

print()
print('=== 2. 播放函数检查 ===')
import inspect
src = inspect.getsource(tools._play_wav_async) if hasattr(tools, '_play_wav_async') else 'NOT FOUND'
print(src[:2000])
