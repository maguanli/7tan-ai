# -*- coding: utf-8 -*-
"""补写 draft_saver 的 manifest.json / installed.json（create_plugin 因 GBK 编码失败未写入）"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\7tan\7tanAI')
MP = ROOT / 'data' / 'plugins' / 'manifest.json'
IP = ROOT / 'data' / 'plugins' / 'installed.json'
PLUG = ROOT / 'data' / 'plugins' / 'draft_saver' / 'tools.py'

TOOLS = ['draft_env_check', 'draft_platforms', 'draft_set_platform', 'draft_record_url',
         'draft_open_editor', 'draft_prep_html', 'draft_verify_html', 'draft_set_clipboard',
         'draft_set_clipboard_image', 'draft_fill_title', 'draft_paste_body',
         'draft_readback', 'draft_save_draft', 'draft_save_all']

ENTRY = {
    "id": "draft_saver",
    "name": "发稿助手",
    "version": "1.0.0",
    "author": "AI Self-Evolution",
    "type": "custom",
    "category": "发布",
    "description": "多平台「存草稿」一键套件。内置 7 个平台档案（公众号/百家号/搜狐号/头条号/知乎/小红书/微博头条文章）的编辑器 URL、窗口关键字、点击坐标、粘贴通道、等待秒数与已知坑。统一流程：打开编辑器→窗口闸门→写剪贴板→填标题正文→等抓图→回读校验→存草稿（永不点发表）。",
    "tools": TOOLS,
    "icon": "📮",
}

print('tools.py 存在:', PLUG.exists(), PLUG.stat().st_size if PLUG.exists() else '-', '字节')

mf = json.loads(MP.read_text(encoding='utf-8'))
print('manifest 原有条目:', len(mf))
mf = [p for p in mf if p.get('id') != 'draft_saver']
mf.append(ENTRY)
MP.write_text(json.dumps(mf, ensure_ascii=False, indent=2), encoding='utf-8')

ins = json.loads(IP.read_text(encoding='utf-8'))
pl = ins.get('plugins', [])
if 'draft_saver' not in pl:
    pl.append('draft_saver')
ins['plugins'] = pl
IP.write_text(json.dumps(ins, ensure_ascii=False, indent=2), encoding='utf-8')

# 回读验证
mf2 = json.loads(MP.read_text(encoding='utf-8'))
ins2 = json.loads(IP.read_text(encoding='utf-8'))
hit = [p for p in mf2 if p.get('id') == 'draft_saver']
print('manifest 现有条目:', len(mf2), '| 末3个:', [p['id'] for p in mf2][-3:])
print('installed 现有:', len(ins2['plugins']), '| 末3个:', ins2['plugins'][-3:])
print('draft_saver 在 manifest:', bool(hit), '| 工具数:', len(hit[0]['tools']) if hit else 0)
print('draft_saver 在 installed:', 'draft_saver' in ins2['plugins'])
