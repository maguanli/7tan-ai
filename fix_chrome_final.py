# -*- coding: utf-8 -*-
"""彻底修复便携版 Chrome 恢复上次会话"""
import os, json, glob, win32com.client, shutil

UD = r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data'
PORTABLE = r'D:\用户目录\下载\新建文件夹 123\chrome-win'
LNK = r'C:\Users\Administrator\Desktop\chrome.exe.lnk'

print('=== 步骤1: 删除 First Run 文件（防止每次当首次运行）===')
for p in [os.path.join(UD, 'First Run'), os.path.join(PORTABLE, 'First Run')]:
    if os.path.exists(p):
        os.remove(p)
        print(f'  已删除: {p}')
    else:
        print(f'  不存在: {p}')

print('\n=== 步骤2: 修复 chrome_launcher.pyw 路径 ===')
launcher = r'D:\7tan\7tanAI\chrome_launcher.pyw'
if os.path.exists(launcher):
    with open(launcher, 'r', encoding='utf-8') as f:
        content = f.read()
    old = r'D:\用户目录\资料\新建文件夹 123\chrome-win\chrome.exe'
    new = r'D:\用户目录\下载\新建文件夹 123\chrome-win\chrome.exe'
    if old in content:
        content = content.replace(old, new)
        with open(launcher, 'w', encoding='utf-8') as f:
            f.write(content)
        print('  已修正脚本路径: 资料 -> 下载')
    else:
        print('  脚本路径已正确或无需修改')

print('\n=== 步骤3: 桌面 chrome.exe.lnk 添加 --restore-last-session ===')
sh = win32com.client.Dispatch('WScript.Shell')
sc = sh.CreateShortcut(LNK)
print('  修改前 Args:', repr(sc.Arguments))
args = sc.Arguments
if 'restore-last-session' not in args:
    sc.Arguments = '--restore-last-session'
    sc.Save()
    print('  已添加 --restore-last-session')
else:
    print('  已有该参数')
sc2 = sh.CreateShortcut(LNK)
print('  修改后 Args:', repr(sc2.Arguments))

print('\n=== 步骤4: 验证 Preferences 状态 ===')
pref = os.path.join(UD, 'Default', 'Preferences')
with open(pref, 'r', encoding='utf-8') as f:
    d = json.load(f)
print('  restore_on_startup =', d.get('session', {}).get('restore_on_startup'))
print('  exit_type =', d.get('profile', {}).get('exit_type'))
print('  exited_cleanly =', d.get('profile', {}).get('exited_cleanly'))

print('\n=== 步骤5: 清理会话残留（让下次启动干净保存）===')
sess = os.path.join(UD, 'Default', 'Sessions')
if os.path.isdir(sess):
    for fn in os.listdir(sess):
        fp = os.path.join(sess, fn)
        try:
            os.remove(fp)
            print(f'  清理: {fn}')
        except Exception as e:
            print(f'  跳过: {fn} ({e})')
else:
    print('  Sessions 目录不存在，无需清理')

print('\n✅ 全部完成！')
