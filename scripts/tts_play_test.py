# -*- coding: utf-8 -*-
"""语音系统真实播放测试：合成 + 播放一段测试语音，等待播完"""
import sys, time
sys.path.insert(0, r'D:\7tan\7tanAI\data\plugins\tts_piper')
from tools import tts_speak, tts_get_gender, tts_status

print("=" * 50)
print("[TTS测试] 当前性别:", tts_get_gender())
st = tts_status()
print("[TTS测试] 状态:", st)
print("[TTS测试] 开始合成+播放...")
text = "语音系统测试。如果你能听到这句话，说明朗读功能完全正常。"
t0 = time.time()
r = tts_speak(text, play=True)
print("[TTS测试] 调用返回:", r)
print("[TTS测试] 耗时 %.1f 秒" % (time.time() - t0))
print("[TTS测试] 等待播放完成(8秒)...")
time.sleep(8)
print("[TTS测试] 完成")
