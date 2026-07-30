"""逐模块追踪 src.ui.app 导入链"""
import sys, os, time
os.chdir('D:/7tan/7tanAI')
sys.path.insert(0, '.')

from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)
print("QApp OK", flush=True)

# app.py 的导入链
modules = [
    'src.ui.theme',
    'src.ui.login_dialog',
    'src.ui.chat_page',
    'src.ui.console_panel',
    'src.ui.pro_status_widget',
    'src.ui.welcome_wizard',
    'src.ui.widgets.message_input',
    'src.ui.widgets.message_bubble',
    'src.ui.widgets.session_sidebar',
    'src.ui.workers.chat_workers',
    'src.ui.video_editor.editor_window',
    'src.ui.video_editor.screen_recorder',
]

for m in modules:
    print(f"  importing {m}...", end=" ", flush=True)
    try:
        __import__(m)
        print("OK", flush=True)
    except Exception as e:
        print(f"ERROR: {e}", flush=True)

print("\nAll imports OK, trying app...", flush=True)
from src.ui.app import MainWindow
print("APP OK!", flush=True)
