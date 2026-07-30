"""
精确模拟 main.py 的导入路径
运行: .venv\Scripts\python.exe _test_import2.py
"""
import sys, os

# 模拟 main.py 的环境设置
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print('step1: import QWebEngine...', flush=True)
import PyQt6.QtWebEngineWidgets
print('step1 OK', flush=True)

print('step2: QApplication...', flush=True)
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)
print('step2 OK', flush=True)

print('step3: import ui.app...', flush=True)
from src.ui.app import MainWindow, DARK_STYLESHEET
print('step3 OK!', flush=True)
