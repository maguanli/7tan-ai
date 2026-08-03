# -*- coding: utf-8 -*-
"""TTS 引擎运行时诊断"""
import sys, os
sys.path.insert(0, r'D:\7tan\7tanAI')
os.chdir(r'D:\7tan\7tanAI')

print('=== 1. 依赖检查 ===')
try:
    import edge_tts
    print('edge_tts: OK', getattr(edge_tts, '__version__', '?'))
except Exception as e:
    print('edge_tts: FAIL -', type(e).__name__, e)

from data.plugins.tts_piper import tools
print('gender =', tools._voice_gender)
print('status =', tools.tts_status())

print()
print('=== 2. 合成测试 (play=False, 不播放) ===')
r = tools.tts_speak('你好，测试语音引擎是否可用', play=False)
for k, v in r.items():
    if k == 'wav_path':
        print('  wav_path =', v, '| exists =', os.path.exists(v) if v else None)
    else:
        print('  %s = %s' % (k, str(v)[:80]))

print()
print('=== 3. Piper 独立测试 ===')
try:
    r2 = tools._speak_piper('测试Piper本地语音', play=False)
    print('piper result:', {k: str(v)[:60] for k, v in r2.items() if k != 'wav_path'})
    print('wav exists:', os.path.exists(r2.get('wav_path', '')) if r2.get('wav_path') else None)
except Exception as e:
    print('piper FAIL:', type(e).__name__, e)

print()
print('=== 4. Edge 独立测试 ===')
try:
    r3 = tools._speak_edge_tts('测试Edge在线语音', play=False)
    print('edge result:', {k: str(v)[:60] for k, v in r3.items() if k != 'wav_path'})
    print('wav exists:', os.path.exists(r3.get('wav_path', '')) if r3.get('wav_path') else None)
except Exception as e:
    print('edge FAIL:', type(e).__name__, e)
