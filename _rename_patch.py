#!/usr/bin/env python3
"""批量替换：7坛AI小编 → 7Tan，7tanAI → 7Tan"""
import sys

FILES_AND_REPLACEMENTS = {
    # (文件路径, [(旧, 新), ...])
    r"D:\7tan\7tanAI\src\ui\app.py": [
        ('7坛AI小编 — 原生 PyQt6 桌面应用', '7Tan — 原生 PyQt6 桌面应用'),
        ('logo = QLabel("🎮 7坛AI小编")', 'logo = QLabel("🎮 7Tan")'),
        ('self.setWindowTitle("7tanAI — AI 自动更新系统")', 'self.setWindowTitle("7Tan — AI 自动更新系统")'),
        ('app.setApplicationName("7tanAI")', 'app.setApplicationName("7Tan")'),
    ],
    r"D:\7tan\7tanAI\rebuild.bat": [
        ('7tanAI 构建脚本 v17', '7Tan 构建脚本 v17'),
    ],
    r"D:\7tan\7tanAI\ARCHITECTURE.md": [
        ('7坛AI小编', '7Tan'),
        ('软件名称: 7坛AI小编', '软件名称: 7Tan'),
    ],
    r"D:\7tan\7tanAI\dist\7tan-editor\config\config.yaml": [
        ('7坛AI小编', '7Tan'),
        ('7tanAI', '7Tan'),
    ],
}

for filepath, replacements in FILES_AND_REPLACEMENTS.items():
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        for old, new in replacements:
            if old in content:
                content = content.replace(old, new)
                print(f"  ✓ 替换: {old[:40]}... → {new}")
            else:
                print(f"  ⚠ 未找到: {old[:40]}...")
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 已修改: {filepath}")
        else:
            print(f"⏭️ 无变更: {filepath}")
    except FileNotFoundError:
        print(f"⏭️ 文件不存在: {filepath}")
    except Exception as e:
        print(f"❌ 失败: {filepath} - {e}")

print("\n=== 全部完成! ===")
