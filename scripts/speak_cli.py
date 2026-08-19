# -*- coding: utf-8 -*-
"""
speak_cli.py — 朗读指定文本的命令行工具
用法:
    python speak_cli.py "要朗读的内容"
    python speak_cli.py --gender male "要朗读的内容"
    python speak_cli.py --file path/to/text.txt
"""
import sys
import os
import io
import argparse

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.plugins.tts_piper import tools as t


def main():
    parser = argparse.ArgumentParser(description='朗读指定文本')
    parser.add_argument('text', nargs='?', default=None, help='要朗读的文本')
    parser.add_argument('--gender', choices=['female', 'male'], default=None, help='声音性别')
    parser.add_argument('--file', default=None, help='从文件读取文本')
    parser.add_argument('--wait', action='store_true', help='等待播放完成（默认立即返回）')
    args = parser.parse_args()

    # 确定要朗读的文本
    if args.file:
        with open(args.file, encoding='utf-8', errors='replace') as f:
            text = f.read().strip()
    elif args.text:
        text = args.text
    else:
        print('❌ 未提供文本！用法: python speak_cli.py "要朗读的内容"')
        return 1

    if not text:
        print('❌ 文本为空！')
        return 1

    print(f'📢 朗读内容 ({len(text)} 字符): {text[:100]}{"..." if len(text) > 100 else ""}')

    # 切换声音（可选）
    if args.gender:
        r = t.tts_set_gender(args.gender)
        print(f'🔊 切换声音: {r}')

    # 朗读
    try:
        result = t.tts_speak(text, play=True)
        print(f'✅ 朗读调用返回: {str(result)[:200]}')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return 1

    # 等待播放完成
    if args.wait:
        import time
        for i in range(30):
            time.sleep(1)
            if not t.tts_is_busy():
                print('✅ 播放完成')
                return 0
        print('⚠️ 等待超时（30秒），但已触发播放')
    return 0


if __name__ == '__main__':
    sys.exit(main())
