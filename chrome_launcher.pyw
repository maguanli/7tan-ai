# -*- coding: utf-8 -*-
"""Chrome 启动器 - 每次启动前修复配置，确保恢复上次会话
用法：双击此脚本即可（桌面快捷方式指向它）
"""
import os, json, subprocess, time, glob, sys

USER = 'Administrator'
UD = os.path.join(r'C:\Users', USER, 'AppData', 'Local', 'Google', 'Chrome', 'User Data')
# 便携版 Chrome 位置（用户桌面快捷方式指向这里）
CHROME = r"D:\用户目录\下载\新建文件夹 123\chrome-win\chrome.exe"
if not os.path.exists(CHROME):
    CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def fix_preferences():
    """把 restore_on_startup 设为 1（继续上次浏览）"""
    for fname in ['Preferences']:
        path = os.path.join(UD, 'Default', fname)
        if not os.path.exists(path):
            print('配置文件不存在:', path)
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            changed = False
            s = data.setdefault('session', {})
            if s.get('restore_on_startup') != 1:
                s['restore_on_startup'] = 1
                s.pop('startup_urls', None)
                changed = True
            p = data.setdefault('profile', {})
            if p.get('exit_type') != 'Normal':
                p['exit_type'] = 'Normal'
                changed = True
            if p.get('exited_cleanly') is not True:
                p['exited_cleanly'] = True
                changed = True
            if changed:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False)
                print('已修复配置:', fname)
            # 删除锁文件
            for jf in glob.glob(path + '*'):
                if jf.endswith('.journal'):
                    try: os.remove(jf)
                    except: pass
        except Exception as e:
            print('修复失败:', e)

if __name__ == '__main__':
    fix_preferences()
    time.sleep(0.5)
    try:
        subprocess.Popen([CHROME], shell=False)
    except Exception as e:
        print('启动失败:', e)
