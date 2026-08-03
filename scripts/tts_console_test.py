# -*- coding: utf-8 -*-
"""实时控制台 Agent 内容朗读测试：真实合成 + 真实播放"""
import sys, time
sys.path.insert(0, r'D:\7tan\7tanAI\data\plugins\tts_piper')
from tools import tts_speak, tts_get_gender, tts_status

print("=" * 50)
print("[TTS测试] 当前声音:", tts_get_gender())
st = tts_status()
print("[TTS测试] 引擎状态:", st)
print("[TTS测试] 开始朗读 Agent 内容...")
text = "你好，这是实时控制台语音朗读测试。Agent 回复的内容现在可以正常朗读了。如果你能听到这句话，说明语音功能一切正常。"
t0 = time.time()
r = tts_speak(text, play=True)
print("[TTS测试] 调用返回:", r)
print("[TTS测试] 耗时 %.1f 秒" % (time.time() - t0))
print("[TTS测试] 等待播放完成(15秒)...")
time.sleep(15)
print("[TTS测试] 完成")
