# -*- coding: utf-8 -*-
"""端到端播放实测：真出声验证（Piper 女声直连播放）"""
import sys, os, time
sys.path.insert(0, r'D:\7tan\7tanAI')
os.chdir(r'D:\7tan\7tanAI')

from data.plugins.tts_piper import tools
print('gender =', tools._voice_gender)
# 直接走 Piper 播放（女声本地，不依赖网络）
r = tools._speak_piper('你好，这是端到端播放测试，如果你能听到这句话，说明声卡和播放链路正常。', play=True)
print('piper play result:', r.get('status'), r.get('engine'), r.get('size_kb'))
print('等待 3 秒让播放线程完成...')
time.sleep(3)
print('done. 播放线程存活检查:')
import threading
alive = [t.name for t in threading.enumerate() if 'tts-player' in t.name]
print('tts-player 线程:', alive)
