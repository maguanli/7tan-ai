# -*- coding: utf-8 -*-
"""用视觉大模型分析聊天截图，列出所有消息（含方向/时间），判断是否有新回复"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'desktop_bot'))
from desktop_do import _vision_config, _call_vision_api

img_path = sys.argv[1] if len(sys.argv) > 1 else r'D:\7tan\7tanAI\temp\wx_printwin_test.png'

cfg = _vision_config()
prompt = (
    '这是一张微信PC聊天窗口截图。请仔细阅读右侧聊天区（消息列表区域）的每一条消息，'
    '严格按时间从下往上（最新在前）列出，格式：\n'
    '【消息N】方向: 左(对方)/右(我) | 内容: xxx | 时间: xx:xx\n'
    '特别注意：1) 区分左右两侧气泡，右侧是自己发的，左侧是对方发的；'
    '2) 找出对方(左侧)最新一条消息是什么；'
    '3) 如果看到"你好"、"最近怎么样"之类的问候消息，指出它在哪一侧；'
    '4) 最后一行输出结论：对方是否有新回复？对方最后说的内容是什么？'
)
print('正在调用视觉大模型分析...')
resp = _call_vision_api(prompt, img_path, cfg)
print(resp)
print('DONE')
